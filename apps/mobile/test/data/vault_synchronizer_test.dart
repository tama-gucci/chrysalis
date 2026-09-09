import 'package:flutter_test/flutter_test.dart';
import 'package:drift/drift.dart' as drift;
import 'package:chrysalis_mobile/data/database/app_database.dart';
import 'package:chrysalis_mobile/data/database/connection.dart';
import 'package:chrysalis_mobile/data/storage/in_memory_vault_storage_provider.dart';
import 'package:chrysalis_mobile/data/sync/vault_synchronizer.dart';
import 'package:chrysalis_mobile/domain/models/cognitive_modality.dart';
import 'package:chrysalis_mobile/domain/models/task_note.dart';
import 'package:chrysalis_mobile/domain/models/task_status.dart';

void main() {
  group('VaultSynchronizer (Offline-First SQLite Cache & Mutation Journal)', () {
    late AppDatabase db;
    late InMemoryVaultStorageProvider storage;
    late VaultSynchronizer synchronizer;

    setUp(() async {
      db = DatabaseFactory.createInMemory();
      storage = InMemoryVaultStorageProvider();
      await storage.initialize();

      synchronizer = VaultSynchronizer(
        database: db,
        storageProvider: storage,
      );
      await synchronizer.initialize();
    });

    tearDown(() async {
      await synchronizer.dispose();
      await storage.dispose();
      await db.close();
    });

    test('saveTask writes immediately to SQLite cache and drains mutation journal', () async {
      final task = TaskNote(
        title: 'Offline First Synchronizer Task',
        status: TaskStatus.todo,
        modality: CognitiveModality.analytical,
        path: 'TaskNotes/Tasks/sample-sync-task.md',
      );

      await synchronizer.saveTask(task);

      // 1. Verify note is in SQLite cache immediately
      final cached = await db.getCachedNoteByPath(task.path!);
      expect(cached, isNotNull);
      expect(cached!.title, equals('Offline First Synchronizer Task'));

      // 2. Verify drained to remote storage provider
      await synchronizer.drainMutationJournal();

      expect(await storage.fileExists(task.path!), isTrue);
      final rawFile = await storage.readTextFile(task.path!);
      expect(rawFile, contains('title: "Offline First Synchronizer Task"'));

      // 3. Verify clean in SQLite cache
      final updatedCache = await db.getCachedNoteByPath(task.path!);
      expect(updatedCache!.isDirty, isFalse);
    });

    test('deleteTask removes note from cache and drains delete to storage provider', () async {
      final task = TaskNote(
        title: 'Task To Delete',
        path: 'TaskNotes/Tasks/to-delete.md',
      );
      await synchronizer.saveTask(task);
      await synchronizer.drainMutationJournal();
      expect(await storage.fileExists(task.path!), isTrue);

      // Delete task
      await synchronizer.deleteTask(task.path!);

      // Deleted from local cache immediately
      expect(await db.getCachedNoteByPath(task.path!), isNull);

      // Drain delete
      await synchronizer.drainMutationJournal();
      expect(await storage.fileExists(task.path!), isFalse);
    });

    test('ingestAllRemoteTasks populates SQLite cache from storage provider', () async {
      const taskMd = '''---
title: "Remote Task from Home Orchestrator"
status: todo
dateCreated: "2026-09-04T12:00:00-05:00"
created: "2026-09-04T12:00:00-05:00"
priority: high
urgency_tier: 3
modality: analytical
timeEstimate: 45
energy: medium
friction: medium
micro_chunked: false
tags:
  - task
---
# Remote Task
''';

      await storage.writeTextFile('TaskNotes/Tasks/remote-task.md', taskMd);

      final count = await synchronizer.ingestAllRemoteTasks();
      expect(count, equals(1));

      final cached = await db.getCachedNoteByPath('TaskNotes/Tasks/remote-task.md');
      expect(cached, isNotNull);
      expect(cached!.title, equals('Remote Task from Home Orchestrator'));
      expect(cached.isDirty, isFalse);
    });

    test('burst concurrent saveTask calls drain all pending mutations without loss', () async {
      final t1 = TaskNote(title: 'Burst Task 1', path: 'TaskNotes/Tasks/burst-1.md');
      final t2 = TaskNote(title: 'Burst Task 2', path: 'TaskNotes/Tasks/burst-2.md');
      final t3 = TaskNote(title: 'Burst Task 3', path: 'TaskNotes/Tasks/burst-3.md');

      // Launch all saves concurrently without awaiting between them
      await Future.wait([
        synchronizer.saveTask(t1),
        synchronizer.saveTask(t2),
        synchronizer.saveTask(t3),
      ]);

      // All files must be drained to remote storage provider
      expect(await storage.fileExists(t1.path!), isTrue);
      expect(await storage.fileExists(t2.path!), isTrue);
      expect(await storage.fileExists(t3.path!), isTrue);

      // Pending mutations queue must be completely empty
      final pending = await db.getPendingMutations();
      expect(pending.isEmpty, isTrue);
    });

    test('recovers abandoned in-flight mutations upon initialization', () async {
      // Simulate an in-flight mutation left behind from an interrupted session
      await db.insertMutation(
        MutationJournalCompanion(
          path: const drift.Value('TaskNotes/Tasks/interrupted.md'),
          mutationType: const drift.Value('upsert'),
          payload: const drift.Value('---\ntitle: "Interrupted Task"\nstatus: todo\ndateCreated: "2026-09-04T12:00:00-05:00"\ncreated: "2026-09-04T12:00:00-05:00"\npriority: normal\nurgency_tier: 2\nmodality: analytical\ntimeEstimate: 45\nenergy: medium\nfriction: medium\nmicro_chunked: false\ntags:\n  - task\n---\n'),
          payloadSha256: const drift.Value('fake-hash'),
          createdAt: drift.Value(DateTime.now()),
          syncState: const drift.Value('in_flight'),
        ),
      );

      // Create a fresh synchronizer on the same DB
      final freshSynchronizer = VaultSynchronizer(
        database: db,
        storageProvider: storage,
      );
      await freshSynchronizer.initialize();

      // The interrupted mutation should be recovered to pending and drained
      expect(await storage.fileExists('TaskNotes/Tasks/interrupted.md'), isTrue);
      final pending = await db.getPendingMutations();
      expect(pending.isEmpty, isTrue);

      await freshSynchronizer.dispose();
    });
  });
}
