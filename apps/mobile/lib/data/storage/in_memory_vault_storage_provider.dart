import 'dart:async';
import '../../core/exceptions/app_exceptions.dart';
import 'vault_storage_provider.dart';

/// In-memory implementation of [VaultStorageProvider] for fast unit testing
/// and mock environments.
class InMemoryVaultStorageProvider implements VaultStorageProvider {
  final Map<String, String> _files = {};
  final StreamController<SyncStatus> _statusController = StreamController<SyncStatus>.broadcast();
  final StreamController<VaultChangeEvent> _changesController = StreamController<VaultChangeEvent>.broadcast();
  SyncStatus _currentStatus = SyncStatus.idle();
  SyncStatus get currentStatus => _currentStatus;

  @override
  String get providerId => 'in_memory';

  @override
  String get displayName => 'In-Memory Vault (Testing)';

  @override
  Future<void> initialize() async {
    _emitStatus(SyncStatus.idle(DateTime.now()));
  }

  void _emitStatus(SyncStatus s) {
    _currentStatus = s;
    if (!_statusController.isClosed) {
      _statusController.add(s);
    }
  }

  @override
  Stream<SyncStatus> get syncStatus => _statusController.stream;

  @override
  Stream<VaultChangeEvent> get watchChanges => _changesController.stream;

  @override
  Future<bool> fileExists(String relativePath) async {
    final cleanPath = _clean(relativePath);
    return _files.containsKey(cleanPath);
  }

  @override
  Future<String> readTextFile(String relativePath) async {
    final cleanPath = _clean(relativePath);
    final content = _files[cleanPath];
    if (content == null) {
      throw VaultStorageException('File not found in vault: "$cleanPath"');
    }
    return content;
  }

  @override
  Future<void> writeTextFile(String relativePath, String content, {String? eTag}) async {
    final cleanPath = _clean(relativePath);
    final isNew = !_files.containsKey(cleanPath);
    _files[cleanPath] = content;

    if (!_changesController.isClosed) {
      _changesController.add(
        VaultChangeEvent(
          relativePath: cleanPath,
          type: isNew ? VaultChangeType.created : VaultChangeType.modified,
          timestamp: DateTime.now(),
        ),
      );
    }
  }

  @override
  Future<void> deleteFile(String relativePath) async {
    final cleanPath = _clean(relativePath);
    if (_files.remove(cleanPath) != null) {
      if (!_changesController.isClosed) {
        _changesController.add(
          VaultChangeEvent(
            relativePath: cleanPath,
            type: VaultChangeType.deleted,
            timestamp: DateTime.now(),
          ),
        );
      }
    }
  }

  @override
  Future<List<VaultFileEntry>> listFiles({String directory = ''}) async {
    final cleanDir = _clean(directory);
    final results = <VaultFileEntry>[];
    for (final entry in _files.entries) {
      if (cleanDir.isEmpty || entry.key.startsWith('$cleanDir/')) {
        results.add(
          VaultFileEntry(
            relativePath: entry.key,
            sizeBytes: entry.value.length,
            modifiedAt: DateTime.now(),
            isDirectory: false,
          ),
        );
      }
    }
    return results;
  }

  @override
  Future<SyncResult> triggerSync({bool force = false}) async {
    _emitStatus(SyncStatus.syncing());
    await Future.delayed(const Duration(milliseconds: 10));
    _emitStatus(SyncStatus.success(DateTime.now()));
    return const SyncResult(success: true, filesChanged: 0);
  }

  @override
  Future<void> dispose() async {
    await _statusController.close();
    await _changesController.close();
  }

  String _clean(String path) {
    var p = path.replaceAll('\\', '/');
    if (p.startsWith('/')) p = p.substring(1);
    if (p.endsWith('/') && p.length > 1) p = p.substring(0, p.length - 1);
    return p;
  }
}
