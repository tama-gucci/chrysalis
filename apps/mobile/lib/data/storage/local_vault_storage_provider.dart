import 'dart:async';
import 'dart:io';
import 'package:path/path.dart' as p;
import '../../core/exceptions/app_exceptions.dart';
import 'vault_storage_provider.dart';

/// Local filesystem implementation of [VaultStorageProvider].
///
/// Can bind to an Android app-private storage folder, an external directory,
/// or a Syncthing-synced folder on disk.
class LocalVaultStorageProvider implements VaultStorageProvider {
  final Directory rootDirectory;
  final StreamController<SyncStatus> _statusController = StreamController<SyncStatus>.broadcast();
  final StreamController<VaultChangeEvent> _changesController = StreamController<VaultChangeEvent>.broadcast();
  StreamSubscription<FileSystemEvent>? _watcherSub;

  LocalVaultStorageProvider({required this.rootDirectory});

  @override
  String get providerId => 'local_fs';

  @override
  String get displayName => 'Local Filesystem Vault';

  @override
  Future<void> initialize() async {
    if (!await rootDirectory.exists()) {
      await rootDirectory.create(recursive: true);
    }
    _statusController.add(SyncStatus.idle(DateTime.now()));

    try {
      _watcherSub = rootDirectory.watch(recursive: true).listen((event) {
        final rel = p.relative(event.path, from: rootDirectory.path).replaceAll('\\', '/');
        final VaultChangeType type;
        switch (event.type) {
          case FileSystemEvent.create:
            type = VaultChangeType.created;
            break;
          case FileSystemEvent.modify:
            type = VaultChangeType.modified;
            break;
          case FileSystemEvent.delete:
            type = VaultChangeType.deleted;
            break;
          default:
            type = VaultChangeType.modified;
        }
        if (!_changesController.isClosed) {
          _changesController.add(
            VaultChangeEvent(
              relativePath: rel,
              type: type,
              timestamp: DateTime.now(),
            ),
          );
        }
      });
    } catch (_) {
      // File watching may not be supported on all filesystems
    }
  }

  @override
  Stream<SyncStatus> get syncStatus => _statusController.stream;

  @override
  Stream<VaultChangeEvent> get watchChanges => _changesController.stream;

  @override
  Future<bool> fileExists(String relativePath) async {
    final file = File(p.join(rootDirectory.path, relativePath));
    return file.exists();
  }

  @override
  Future<String> readTextFile(String relativePath) async {
    final file = File(p.join(rootDirectory.path, relativePath));
    if (!await file.exists()) {
      throw VaultStorageException('File not found: "$relativePath"');
    }
    try {
      return await file.readAsString();
    } catch (e) {
      throw VaultStorageException('Failed to read file "$relativePath"', e);
    }
  }

  @override
  Future<void> writeTextFile(String relativePath, String content, {String? eTag}) async {
    final file = File(p.join(rootDirectory.path, relativePath));
    try {
      await file.parent.create(recursive: true);
      await file.writeAsString(content);
    } catch (e) {
      throw VaultStorageException('Failed to write file "$relativePath"', e);
    }
  }

  @override
  Future<void> deleteFile(String relativePath) async {
    final file = File(p.join(rootDirectory.path, relativePath));
    if (await file.exists()) {
      try {
        await file.delete();
      } catch (e) {
        throw VaultStorageException('Failed to delete file "$relativePath"', e);
      }
    }
  }

  @override
  Future<List<VaultFileEntry>> listFiles({String directory = ''}) async {
    final targetDir = Directory(p.join(rootDirectory.path, directory));
    if (!await targetDir.exists()) return [];

    final list = <VaultFileEntry>[];
    try {
      await for (final entity in targetDir.list(recursive: true, followLinks: false)) {
        if (entity is File) {
          final rel = p.relative(entity.path, from: rootDirectory.path).replaceAll('\\', '/');
          final stat = await entity.stat();
          list.add(
            VaultFileEntry(
              relativePath: rel,
              sizeBytes: stat.size,
              modifiedAt: stat.modified,
              isDirectory: false,
            ),
          );
        }
      }
    } catch (e) {
      throw VaultStorageException('Failed to list files in "$directory"', e);
    }
    return list;
  }

  @override
  Future<SyncResult> triggerSync({bool force = false}) async {
    _statusController.add(SyncStatus.syncing());
    _statusController.add(SyncStatus.success(DateTime.now()));
    return const SyncResult(success: true);
  }

  @override
  Future<void> dispose() async {
    await _watcherSub?.cancel();
    await _statusController.close();
    await _changesController.close();
  }
}
