import 'dart:async';
import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:drift/drift.dart' as drift;
import '../../core/constants/timezones.dart';
import '../../domain/models/task_note.dart';
import '../../domain/parser/task_note_parser.dart';
import '../database/app_database.dart';
import '../storage/vault_storage_provider.dart';

/// Offline-First Synchronization Engine.
///
/// Ensures all mutations (task additions, completions, edits) write to local
/// SQLite cache and the Mutation Journal first (<10ms UI update), then drains
/// to the active [VaultStorageProvider].
class VaultSynchronizer {
  final AppDatabase database;
  final VaultStorageProvider storageProvider;
  StreamSubscription<VaultChangeEvent>? _changeSubscription;

  final String tasksDirectory;

  VaultSynchronizer({
    required this.database,
    required this.storageProvider,
    this.tasksDirectory = 'chrysalis/Tasks',
  });

  /// Initializes synchronizer and hooks up remote vault watcher.
  Future<void> initialize() async {
    await storageProvider.initialize();

    _changeSubscription = storageProvider.watchChanges.listen((event) async {
      if (event.relativePath.startsWith('$tasksDirectory/') ||
          event.relativePath.startsWith('TaskNotes/Tasks/')) {
        await _handleRemoteChange(event);
      }
    });

    // Recover any abandoned in-flight mutations from interrupted sessions
    await database.resetInFlightMutations();

    // Initial drain in case mutations remained pending from last session
    await drainMutationJournal();
  }

  /// Saves a task note offline-first: updates SQLite immediately,
  /// journals mutation, and triggers remote drain.
  Future<void> saveTask(TaskNote task) async {
    final path = task.path ?? _generateTaskPath(task.title);
    final serialized = TaskNoteParser.serialize(task.copyWith(path: path));
    final hash = sha256.convert(utf8.encode(serialized)).toString();
    final now = DateTime.now();

    // 1. Write to local cache (Dirty = true until drained)
    await database.upsertCachedNote(
      CachedNotesCompanion(
        path: drift.Value(path),
        title: drift.Value(task.title),
        status: drift.Value(task.status.yamlValue),
        content: drift.Value(serialized),
        frontmatterYaml: drift.Value(''),
        lastCachedLocally: drift.Value(now),
        isDirty: const drift.Value(true),
      ),
    );

    // 2. Append to Mutation Journal
    await database.insertMutation(
      MutationJournalCompanion(
        path: drift.Value(path),
        mutationType: const drift.Value('upsert'),
        payload: drift.Value(serialized),
        payloadSha256: drift.Value(hash),
        createdAt: drift.Value(now),
        syncState: const drift.Value('pending'),
      ),
    );

    // 3. Drain mutation journal
    await drainMutationJournal();
  }

  /// Deletes a task note offline-first.
  Future<void> deleteTask(String path) async {
    final now = DateTime.now();

    // 1. Delete from local SQLite cache
    await database.deleteCachedNote(path);

    // 2. Append delete mutation to journal
    await database.insertMutation(
      MutationJournalCompanion(
        path: drift.Value(path),
        mutationType: const drift.Value('delete'),
        payload: const drift.Value(''),
        payloadSha256: const drift.Value(''),
        createdAt: drift.Value(now),
        syncState: const drift.Value('pending'),
      ),
    );

    // 3. Drain mutation journal
    await drainMutationJournal();
  }

  Future<int>? _activeDrain;
  bool _needsAnotherDrain = false;

  /// Drains pending journal mutations to the active [VaultStorageProvider].
  Future<int> drainMutationJournal() {
    if (_activeDrain != null) {
      _needsAnotherDrain = true;
      return _activeDrain!;
    }
    final future = _runDrainLoop();
    _activeDrain = future;
    return future.whenComplete(() {
      _activeDrain = null;
    });
  }

  Future<int> _runDrainLoop() async {
    int totalDrained = 0;
    do {
      _needsAnotherDrain = false;
      final drained = await _performDrain();
      totalDrained += drained;
    } while (_needsAnotherDrain);
    return totalDrained;
  }

  Future<int> _performDrain() async {
    int drainedCount = 0;
    final pending = await database.getPendingMutations();
    for (final mutation in pending) {
      await database.markMutationInFlight(mutation.id);
      try {
        if (mutation.mutationType == 'upsert') {
          await storageProvider.writeTextFile(mutation.path, mutation.payload);
          // Mark cached note clean
          final cached = await database.getCachedNoteByPath(mutation.path);
          if (cached != null) {
            await database.upsertCachedNote(
              CachedNotesCompanion(
                path: drift.Value(cached.path),
                title: drift.Value(cached.title),
                status: drift.Value(cached.status),
                content: drift.Value(cached.content),
                frontmatterYaml: drift.Value(cached.frontmatterYaml),
                lastCachedLocally: drift.Value(DateTime.now()),
                isDirty: const drift.Value(false),
              ),
            );
          }
        } else if (mutation.mutationType == 'delete') {
          await storageProvider.deleteFile(mutation.path);
        }

        await database.markMutationSynced(mutation.id, DateTime.now());
        drainedCount++;
      } catch (e) {
        await database.markMutationFailed(mutation.id, e.toString());
      }
    }
    return drainedCount;
  }

  /// Ingests all task notes from vault into local SQLite cache.
  Future<int> ingestAllRemoteTasks() async {
    var files = await storageProvider.listFiles(directory: tasksDirectory);
    if (files.isEmpty && tasksDirectory != 'TaskNotes/Tasks') {
      final legacyFiles = await storageProvider.listFiles(directory: 'TaskNotes/Tasks');
      if (legacyFiles.isNotEmpty) {
        files = legacyFiles;
      }
    }
    int ingested = 0;

    for (final file in files) {
      if (!file.relativePath.endsWith('.md')) continue;

      // Check if local version is dirty
      final local = await database.getCachedNoteByPath(file.relativePath);
      if (local != null && local.isDirty) {
        // Do not overwrite dirty local note before it has drained
        continue;
      }

      try {
        final content = await storageProvider.readTextFile(file.relativePath);
        final task = TaskNoteParser.parse(content, path: file.relativePath, strictTimezone: false);

        await database.upsertCachedNote(
          CachedNotesCompanion(
            path: drift.Value(file.relativePath),
            title: drift.Value(task.title),
            status: drift.Value(task.status.yamlValue),
            content: drift.Value(content),
            frontmatterYaml: const drift.Value(''),
            lastModifiedRemote: drift.Value(file.modifiedAt),
            lastCachedLocally: drift.Value(DateTime.now()),
            isDirty: const drift.Value(false),
          ),
        );
        ingested++;
      } catch (_) {
        // Continue on corrupt individual files
      }
    }
    return ingested;
  }

  Future<void> _handleRemoteChange(VaultChangeEvent event) async {
    if (event.type == VaultChangeType.deleted) {
      await database.deleteCachedNote(event.relativePath);
      return;
    }

    final local = await database.getCachedNoteByPath(event.relativePath);
    if (local != null && local.isDirty) return;

    try {
      final content = await storageProvider.readTextFile(event.relativePath);
      final task = TaskNoteParser.parse(content, path: event.relativePath, strictTimezone: false);
      await database.upsertCachedNote(
        CachedNotesCompanion(
          path: drift.Value(event.relativePath),
          title: drift.Value(task.title),
          status: drift.Value(task.status.yamlValue),
          content: drift.Value(content),
          frontmatterYaml: const drift.Value(''),
          lastModifiedRemote: drift.Value(event.timestamp),
          lastCachedLocally: drift.Value(DateTime.now()),
          isDirty: const drift.Value(false),
        ),
      );
    } catch (_) {}
  }

  String _generateTaskPath(String title) {
    final date = TimezoneUtils.todayDateString();
    final slug = title
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
        .replaceAll(RegExp(r'^-+|-+$'), '');
    return '$tasksDirectory/$date-$slug.md';
  }

  Future<void> dispose() async {
    await _changeSubscription?.cancel();
  }
}
