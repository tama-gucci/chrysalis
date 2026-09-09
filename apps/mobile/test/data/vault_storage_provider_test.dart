import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/core/exceptions/app_exceptions.dart';
import 'package:chrysalis_mobile/data/storage/in_memory_vault_storage_provider.dart';
import 'package:chrysalis_mobile/data/storage/vault_storage_provider.dart';

void main() {
  group('InMemoryVaultStorageProvider', () {
    late InMemoryVaultStorageProvider provider;

    setUp(() async {
      provider = InMemoryVaultStorageProvider();
      await provider.initialize();
    });

    tearDown(() async {
      await provider.dispose();
    });

    test('writes and reads file successfully', () async {
      const path = 'TaskNotes/Tasks/test-task.md';
      const content = '# Test Task\nBody content';

      await provider.writeTextFile(path, content);

      expect(await provider.fileExists(path), isTrue);
      final read = await provider.readTextFile(path);
      expect(read, equals(content));
    });

    test('throws VaultStorageException on reading non-existent file', () async {
      expect(
        () => provider.readTextFile('NonExistent/file.md'),
        throwsA(isA<VaultStorageException>()),
      );
    });

    test('deletes file and confirms non-existence', () async {
      const path = 'TaskNotes/Tasks/to-delete.md';
      await provider.writeTextFile(path, 'content');
      expect(await provider.fileExists(path), isTrue);

      await provider.deleteFile(path);
      expect(await provider.fileExists(path), isFalse);
    });

    test('lists files filtered by directory prefix', () async {
      await provider.writeTextFile('TaskNotes/Tasks/t1.md', 'c1');
      await provider.writeTextFile('TaskNotes/Tasks/t2.md', 'c2');
      await provider.writeTextFile('System/Scheduling-Memory.md', 'c3');

      final tasks = await provider.listFiles(directory: 'TaskNotes/Tasks');
      expect(tasks.length, equals(2));
      expect(tasks.map((e) => e.relativePath), containsAll(['TaskNotes/Tasks/t1.md', 'TaskNotes/Tasks/t2.md']));

      final all = await provider.listFiles();
      expect(all.length, equals(3));
    });

    test('emits VaultChangeEvent when file is created or modified', () async {
      final events = <VaultChangeEvent>[];
      final sub = provider.watchChanges.listen(events.add);

      await provider.writeTextFile('test.md', 'v1');
      await provider.writeTextFile('test.md', 'v2');
      await provider.deleteFile('test.md');

      await Future.delayed(const Duration(milliseconds: 10));
      expect(events.length, equals(3));
      expect(events[0].type, equals(VaultChangeType.created));
      expect(events[1].type, equals(VaultChangeType.modified));
      expect(events[2].type, equals(VaultChangeType.deleted));

      await sub.cancel();
    });
  });
}
