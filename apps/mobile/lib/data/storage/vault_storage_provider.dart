import 'dart:async';

/// Status of vault synchronization.
enum SyncState {
  idle,
  syncing,
  success,
  error,
}

class SyncStatus {
  final SyncState state;
  final DateTime? lastSyncedAt;
  final String? errorMessage;

  const SyncStatus({
    required this.state,
    this.lastSyncedAt,
    this.errorMessage,
  });

  factory SyncStatus.idle([DateTime? lastSynced]) => SyncStatus(
        state: SyncState.idle,
        lastSyncedAt: lastSynced,
      );

  factory SyncStatus.syncing() => const SyncStatus(state: SyncState.syncing);

  factory SyncStatus.success(DateTime timestamp) => SyncStatus(
        state: SyncState.success,
        lastSyncedAt: timestamp,
      );

  factory SyncStatus.error(String message) => SyncStatus(
        state: SyncState.error,
        errorMessage: message,
      );
}

class SyncResult {
  final bool success;
  final int filesChanged;
  final String? error;

  const SyncResult({
    required this.success,
    this.filesChanged = 0,
    this.error,
  });
}

enum VaultChangeType {
  created,
  modified,
  deleted,
}

class VaultChangeEvent {
  final String relativePath;
  final VaultChangeType type;
  final DateTime timestamp;

  const VaultChangeEvent({
    required this.relativePath,
    required this.type,
    required this.timestamp,
  });
}

class VaultFileEntry {
  final String relativePath;
  final int sizeBytes;
  final DateTime modifiedAt;
  final bool isDirectory;

  const VaultFileEntry({
    required this.relativePath,
    required this.sizeBytes,
    required this.modifiedAt,
    this.isDirectory = false,
  });
}

/// Abstract contract for Chrysalis Vault Storage Substrates.
///
/// Implementations mediate between local cache and remote vaults:
/// - Google Drive API v3 (REST)
/// - Embedded Syncthing (libsyncthing.so)
/// - Local Filesystem / Testing In-Memory
abstract class VaultStorageProvider {
  /// Machine identifier (e.g. 'google_drive', 'syncthing_embedded', 'local_fs', 'in_memory')
  String get providerId;

  /// User-facing label
  String get displayName;

  /// Initializes authentication and directory bindings
  Future<void> initialize();

  /// Real-time stream of sync status
  Stream<SyncStatus> get syncStatus;

  /// Lists all files under [directory] relative to Chrysalis vault root
  Future<List<VaultFileEntry>> listFiles({String directory = ''});

  /// Reads UTF-8 text file content relative to vault root
  Future<String> readTextFile(String relativePath);

  /// Writes UTF-8 text file content relative to vault root
  Future<void> writeTextFile(String relativePath, String content, {String? eTag});

  /// Deletes file relative to vault root
  Future<void> deleteFile(String relativePath);

  /// Checks if file exists in vault
  Future<bool> fileExists(String relativePath);

  /// Emits real-time delta events when remote files are modified
  Stream<VaultChangeEvent> get watchChanges;

  /// Manually trigger a delta synchronization pass
  Future<SyncResult> triggerSync({bool force = false});

  /// Cleans up active listeners and connections
  Future<void> dispose();
}
