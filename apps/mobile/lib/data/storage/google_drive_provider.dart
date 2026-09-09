import 'dart:async';
import 'dart:convert';
import 'package:googleapis/drive/v3.dart' as drive;
import '../../core/exceptions/app_exceptions.dart';
import 'vault_storage_provider.dart';

/// Google Drive v3 REST implementation of [VaultStorageProvider].
///
/// Features:
/// - Folder hierarchy search and automatic parent directory creation.
/// - Full UTF-8 text file CRUD operations with dynamic MIME-type detection.
/// - Delta synchronization via Google Drive Changes API (`changes.getStartPageToken` / `changes.list`).
/// - Real-time change stream notifications (`watchChanges`) filtered strictly to the vault hierarchy.
/// - Multi-level path and folder caching for sub-millisecond lookups.
/// - Exponential backoff and retry on transient rate limits (HTTP 429 / 503).
class GoogleDriveProvider implements VaultStorageProvider {
  final drive.DriveApi driveApi;
  final String vaultRootFolderName;

  final StreamController<SyncStatus> _statusController = StreamController<SyncStatus>.broadcast();
  final StreamController<VaultChangeEvent> _changesController = StreamController<VaultChangeEvent>.broadcast();

  SyncStatus _currentStatus = SyncStatus.idle();
  SyncStatus get currentStatus => _currentStatus;

  String? _vaultRootFolderId;
  String? _startPageToken;

  /// Cache mapping relative directory paths (e.g. "TaskNotes/Tasks") to Google Drive Folder IDs.
  final Map<String, String> _folderIdCache = {};

  /// Reverse cache mapping Google Drive Folder IDs to relative directory paths.
  final Map<String, String> _folderIdToPathCache = {};

  /// Set of Folder IDs verified to be outside the Chrysalis vault hierarchy.
  final Set<String> _nonVaultFolderIds = {};

  /// Cache mapping relative file paths (e.g. "TaskNotes/Tasks/note.md") to Google Drive File IDs.
  final Map<String, String> _fileIdCache = {};

  /// Reverse cache mapping file IDs to relative paths.
  final Map<String, String> _idToPathCache = {};

  /// In-flight directory creation futures to prevent race conditions during concurrent writes.
  final Map<String, Future<String>> _directoryCreationFutures = {};

  static const String _folderMimeType = 'application/vnd.google-apps.folder';

  GoogleDriveProvider({
    required this.driveApi,
    this.vaultRootFolderName = 'chrysalis',
    String? initialStartPageToken,
  }) : _startPageToken = initialStartPageToken;

  @override
  String get providerId => 'google_drive';

  @override
  String get displayName => 'Google Drive (API v3)';

  String? get vaultRootFolderId => _vaultRootFolderId;
  String? get startPageToken => _startPageToken;

  @override
  Stream<SyncStatus> get syncStatus => _statusController.stream;

  @override
  Stream<VaultChangeEvent> get watchChanges => _changesController.stream;

  void _emitStatus(SyncStatus s) {
    _currentStatus = s;
    if (!_statusController.isClosed) {
      _statusController.add(s);
    }
  }

  void _emitChange(VaultChangeEvent event) {
    if (!_changesController.isClosed) {
      _changesController.add(event);
    }
  }

  /// Retries transient rate limits (HTTP 429 / 503) with exponential backoff.
  Future<T> _retryOnRateLimit<T>(Future<T> Function() operation, {int maxRetries = 3}) async {
    var attempt = 0;
    var delay = const Duration(milliseconds: 200);
    while (true) {
      try {
        return await operation();
      } catch (e) {
        attempt++;
        final isRateLimitOrUnavailable =
            e is drive.DetailedApiRequestError && (e.status == 429 || e.status == 503);
        if (attempt >= maxRetries || !isRateLimitOrUnavailable) {
          rethrow;
        }
        await Future.delayed(delay);
        delay *= 2;
      }
    }
  }

  @override
  Future<void> initialize() async {
    try {
      _emitStatus(SyncStatus.syncing());
      _vaultRootFolderId = await _getOrCreateVaultRoot();
      _folderIdCache[''] = _vaultRootFolderId!;
      _folderIdToPathCache[_vaultRootFolderId!] = '';

      if (_startPageToken == null) {
        final startToken = await _retryOnRateLimit(() => driveApi.changes.getStartPageToken());
        _startPageToken = startToken.startPageToken;
      }

      _emitStatus(SyncStatus.idle(DateTime.now()));
    } catch (e) {
      _emitStatus(SyncStatus.error(e.toString()));
      throw VaultStorageException('Failed to initialize GoogleDriveProvider', e);
    }
  }

  /// Locates or creates the root Chrysalis vault folder in Google Drive.
  Future<String> _getOrCreateVaultRoot() async {
    final query =
        "mimeType = '$_folderMimeType' and name = '$vaultRootFolderName' and 'root' in parents and trashed = false";
    final result = await _retryOnRateLimit(() => driveApi.files.list(
          q: query,
          spaces: 'drive',
          $fields: 'files(id, name)',
        ));

    if (result.files != null && result.files!.isNotEmpty) {
      return result.files!.first.id!;
    }

    // Create the vault root folder under 'root'
    final folderMeta = drive.File()
      ..name = vaultRootFolderName
      ..mimeType = _folderMimeType
      ..parents = ['root'];

    final created = await _retryOnRateLimit(() => driveApi.files.create(
          folderMeta,
          $fields: 'id, name',
        ));

    return created.id!;
  }

  /// Finds an existing directory in the vault without creating it if it does not exist.
  Future<String?> findDirectory(String directoryPath) async {
    if (_vaultRootFolderId == null) {
      await initialize();
    }

    final cleanDir = _cleanPath(directoryPath);
    if (cleanDir.isEmpty) {
      return _vaultRootFolderId;
    }

    if (_folderIdCache.containsKey(cleanDir)) {
      return _folderIdCache[cleanDir];
    }

    final segments = cleanDir.split('/');
    var currentParentId = _vaultRootFolderId!;
    var currentSubpath = '';

    for (final segment in segments) {
      if (segment.isEmpty) continue;
      currentSubpath = currentSubpath.isEmpty ? segment : '$currentSubpath/$segment';

      if (_folderIdCache.containsKey(currentSubpath)) {
        currentParentId = _folderIdCache[currentSubpath]!;
        continue;
      }

      final query =
          "mimeType = '$_folderMimeType' and name = '$segment' and '$currentParentId' in parents and trashed = false";
      final res = await _retryOnRateLimit(() => driveApi.files.list(
            q: query,
            spaces: 'drive',
            $fields: 'files(id, name)',
          ));

      if (res.files != null && res.files!.isNotEmpty) {
        final folderId = res.files!.first.id!;
        _folderIdCache[currentSubpath] = folderId;
        _folderIdToPathCache[folderId] = currentSubpath;
        currentParentId = folderId;
      } else {
        return null;
      }
    }

    return currentParentId;
  }

  /// Resolves or recursively creates folders corresponding to [directoryPath] relative to the vault root.
  Future<String> getOrCreateDirectory(String directoryPath) {
    final cleanDir = _cleanPath(directoryPath);
    if (cleanDir.isEmpty) {
      if (_vaultRootFolderId != null) return Future.value(_vaultRootFolderId!);
      return initialize().then((_) => _vaultRootFolderId!);
    }

    if (_folderIdCache.containsKey(cleanDir)) {
      return Future.value(_folderIdCache[cleanDir]!);
    }

    return _directoryCreationFutures.putIfAbsent(cleanDir, () async {
      try {
        return await _getOrCreateDirectoryInternal(cleanDir);
      } finally {
        _directoryCreationFutures.remove(cleanDir);
      }
    });
  }

  Future<String> _getOrCreateDirectoryInternal(String cleanDir) async {
    if (_vaultRootFolderId == null) {
      await initialize();
    }

    final segments = cleanDir.split('/');
    var currentParentId = _vaultRootFolderId!;
    var currentSubpath = '';

    for (final segment in segments) {
      if (segment.isEmpty) continue;
      currentSubpath = currentSubpath.isEmpty ? segment : '$currentSubpath/$segment';

      if (_folderIdCache.containsKey(currentSubpath)) {
        currentParentId = _folderIdCache[currentSubpath]!;
        continue;
      }

      final query =
          "mimeType = '$_folderMimeType' and name = '$segment' and '$currentParentId' in parents and trashed = false";
      final res = await _retryOnRateLimit(() => driveApi.files.list(
            q: query,
            spaces: 'drive',
            $fields: 'files(id, name)',
          ));

      String folderId;
      if (res.files != null && res.files!.isNotEmpty) {
        folderId = res.files!.first.id!;
      } else {
        final folderMeta = drive.File()
          ..name = segment
          ..mimeType = _folderMimeType
          ..parents = [currentParentId];
        final created = await _retryOnRateLimit(() => driveApi.files.create(
              folderMeta,
              $fields: 'id, name',
            ));
        folderId = created.id!;
      }

      _folderIdCache[currentSubpath] = folderId;
      _folderIdToPathCache[folderId] = currentSubpath;
      currentParentId = folderId;
    }

    return currentParentId;
  }

  /// Finds a file by its relative path inside the vault.
  Future<drive.File?> _findFile(String relativePath) async {
    if (_vaultRootFolderId == null) {
      await initialize();
    }

    final clean = _cleanPath(relativePath);
    if (clean.isEmpty) return null;

    final cachedId = _fileIdCache[clean];
    if (cachedId != null) {
      try {
        final existing = await _retryOnRateLimit(() => driveApi.files.get(
              cachedId,
              $fields: 'id, name, mimeType, modifiedTime, size, parents, trashed',
            )) as drive.File;
        if (existing.trashed != true) {
          return existing;
        } else {
          _fileIdCache.remove(clean);
          _idToPathCache.remove(cachedId);
        }
      } catch (_) {
        _fileIdCache.remove(clean);
        _idToPathCache.remove(cachedId);
      }
    }

    final lastSlash = clean.lastIndexOf('/');
    final dirPart = lastSlash == -1 ? '' : clean.substring(0, lastSlash);
    final fileName = lastSlash == -1 ? clean : clean.substring(lastSlash + 1);

    final parentFolderId = dirPart.isEmpty ? _vaultRootFolderId! : await findDirectory(dirPart);
    if (parentFolderId == null) {
      return null;
    }

    final query =
        "name = '$fileName' and '$parentFolderId' in parents and trashed = false and mimeType != '$_folderMimeType'";

    final res = await _retryOnRateLimit(() => driveApi.files.list(
          q: query,
          spaces: 'drive',
          $fields: 'files(id, name, mimeType, modifiedTime, size, parents, trashed)',
        ));

    if (res.files != null && res.files!.isNotEmpty) {
      final file = res.files!.first;
      _fileIdCache[clean] = file.id!;
      _idToPathCache[file.id!] = clean;
      return file;
    }

    return null;
  }

  @override
  Future<bool> fileExists(String relativePath) async {
    final file = await _findFile(relativePath);
    return file != null;
  }

  @override
  Future<String> readTextFile(String relativePath) async {
    final file = await _findFile(relativePath);
    if (file == null || file.id == null) {
      throw VaultStorageException('File not found in Google Drive vault: "$relativePath"');
    }

    try {
      final media = await _retryOnRateLimit(() => driveApi.files.get(
            file.id!,
            downloadOptions: drive.DownloadOptions.fullMedia,
          )) as drive.Media;

      final chunks = await media.stream.toList();
      final bytes = chunks.expand((chunk) => chunk).toList();
      return utf8.decode(bytes);
    } catch (e) {
      if (e is VaultStorageException) rethrow;
      throw VaultStorageException('Failed to read file from Google Drive: "$relativePath"', e);
    }
  }

  String _determineMimeType(String path) {
    final lower = path.toLowerCase();
    if (lower.endsWith('.json')) return 'application/json';
    if (lower.endsWith('.yaml') || lower.endsWith('.yml')) return 'text/yaml';
    if (lower.endsWith('.txt')) return 'text/plain';
    return 'text/markdown';
  }

  @override
  Future<void> writeTextFile(String relativePath, String content, {String? eTag}) async {
    if (_vaultRootFolderId == null) {
      await initialize();
    }

    final clean = _cleanPath(relativePath);
    final lastSlash = clean.lastIndexOf('/');
    final dirPart = lastSlash == -1 ? '' : clean.substring(0, lastSlash);
    final fileName = lastSlash == -1 ? clean : clean.substring(lastSlash + 1);

    final parentFolderId = await getOrCreateDirectory(dirPart);
    final existingFile = await _findFile(clean);

    final mimeType = _determineMimeType(clean);
    final bytes = utf8.encode(content);
    final media = drive.Media(
      Stream.value(bytes),
      bytes.length,
      contentType: '$mimeType; charset=utf-8',
    );

    try {
      if (existingFile != null && existingFile.id != null) {
        final updateMeta = drive.File();
        final updated = await _retryOnRateLimit(() => driveApi.files.update(
              updateMeta,
              existingFile.id!,
              uploadMedia: media,
              $fields: 'id, name, modifiedTime, size',
            ));

        _fileIdCache[clean] = updated.id!;
        _idToPathCache[updated.id!] = clean;

        _emitChange(VaultChangeEvent(
          relativePath: clean,
          type: VaultChangeType.modified,
          timestamp: DateTime.now(),
        ));
      } else {
        final newMeta = drive.File()
          ..name = fileName
          ..parents = [parentFolderId]
          ..mimeType = mimeType;

        final created = await _retryOnRateLimit(() => driveApi.files.create(
              newMeta,
              uploadMedia: media,
              $fields: 'id, name, modifiedTime, size',
            ));

        _fileIdCache[clean] = created.id!;
        _idToPathCache[created.id!] = clean;

        _emitChange(VaultChangeEvent(
          relativePath: clean,
          type: VaultChangeType.created,
          timestamp: DateTime.now(),
        ));
      }
    } catch (e) {
      throw VaultStorageException('Failed to write file to Google Drive: "$clean"', e);
    }
  }

  @override
  Future<void> deleteFile(String relativePath) async {
    final clean = _cleanPath(relativePath);
    final file = await _findFile(clean);
    if (file != null && file.id != null) {
      try {
        await _retryOnRateLimit(() => driveApi.files.delete(file.id!));
        _fileIdCache.remove(clean);
        _idToPathCache.remove(file.id!);

        _emitChange(VaultChangeEvent(
          relativePath: clean,
          type: VaultChangeType.deleted,
          timestamp: DateTime.now(),
        ));
      } catch (e) {
        throw VaultStorageException('Failed to delete file from Google Drive: "$clean"', e);
      }
    }
  }

  @override
  Future<List<VaultFileEntry>> listFiles({String directory = ''}) async {
    if (_vaultRootFolderId == null) {
      await initialize();
    }

    final cleanDir = _cleanPath(directory);
    final startFolderId = cleanDir.isEmpty ? _vaultRootFolderId! : await findDirectory(cleanDir);
    if (startFolderId == null) {
      return []; // Directory does not exist yet; return empty list without creating it
    }

    final results = <VaultFileEntry>[];
    final queue = <_DirectoryTraversal>[_DirectoryTraversal(startFolderId, cleanDir)];

    while (queue.isNotEmpty) {
      final current = queue.removeAt(0);
      String? pageToken;

      do {
        final query = "'${current.folderId}' in parents and trashed = false";
        final listRes = await _retryOnRateLimit(() => driveApi.files.list(
              q: query,
              spaces: 'drive',
              pageToken: pageToken,
              $fields: 'nextPageToken, files(id, name, mimeType, modifiedTime, size, trashed)',
            ));

        for (final item in listRes.files ?? []) {
          if (item.trashed == true || item.name == null) continue;

          final itemRelPath =
              current.relativePath.isEmpty ? item.name! : '${current.relativePath}/${item.name}';

          if (item.mimeType == _folderMimeType) {
            _folderIdCache[itemRelPath] = item.id!;
            _folderIdToPathCache[item.id!] = itemRelPath;
            queue.add(_DirectoryTraversal(item.id!, itemRelPath));
          } else {
            _fileIdCache[itemRelPath] = item.id!;
            _idToPathCache[item.id!] = itemRelPath;

            results.add(VaultFileEntry(
              relativePath: itemRelPath,
              sizeBytes: int.tryParse(item.size ?? '0') ?? 0,
              modifiedAt: item.modifiedTime ?? DateTime.now(),
              isDirectory: false,
            ));
          }
        }

        pageToken = listRes.nextPageToken;
      } while (pageToken != null);
    }

    return results;
  }

  /// Resolves the relative directory path within the Chrysalis vault for [folderId].
  /// Returns null if [folderId] does not belong to the Chrysalis vault hierarchy.
  Future<String?> _resolveFolderPath(String folderId) async {
    if (folderId == _vaultRootFolderId) return '';
    if (folderId == 'root' || folderId.isEmpty) return null;
    if (_folderIdToPathCache.containsKey(folderId)) return _folderIdToPathCache[folderId];
    if (_nonVaultFolderIds.contains(folderId)) return null;

    try {
      final folder = await _retryOnRateLimit(() => driveApi.files.get(
            folderId,
            $fields: 'id, name, mimeType, parents, trashed',
          )) as drive.File;

      if (folder.trashed == true || folder.parents == null || folder.parents!.isEmpty) {
        _nonVaultFolderIds.add(folderId);
        return null;
      }

      for (final parent in folder.parents!) {
        if (parent == _vaultRootFolderId) {
          final relPath = folder.name!;
          _folderIdCache[relPath] = folderId;
          _folderIdToPathCache[folderId] = relPath;
          return relPath;
        }

        final parentRelPath = await _resolveFolderPath(parent);
        if (parentRelPath != null) {
          final relPath = parentRelPath.isEmpty ? folder.name! : '$parentRelPath/${folder.name!}';
          _folderIdCache[relPath] = folderId;
          _folderIdToPathCache[folderId] = relPath;
          return relPath;
        }
      }
    } catch (_) {
      // Ignored or 404
    }

    _nonVaultFolderIds.add(folderId);
    return null;
  }

  /// Resolves the relative path of a changed file within the Chrysalis vault.
  /// Returns null if the file does not belong to the Chrysalis vault hierarchy.
  Future<String?> _resolveFilePath(drive.Change change) async {
    final fileId = change.fileId;
    if (fileId == null) return null;

    if (_idToPathCache.containsKey(fileId)) {
      return _idToPathCache[fileId];
    }

    final file = change.file;
    if (file == null || file.name == null) return null;
    if (file.mimeType == _folderMimeType) return null;
    if (file.parents == null || file.parents!.isEmpty) return null;

    for (final parent in file.parents!) {
      final parentPath = await _resolveFolderPath(parent);
      if (parentPath != null) {
        final relPath = parentPath.isEmpty ? file.name! : '$parentPath/${file.name!}';
        _fileIdCache[relPath] = fileId;
        _idToPathCache[fileId] = relPath;
        return relPath;
      }
    }

    return null;
  }

  @override
  Future<SyncResult> triggerSync({bool force = false}) async {
    _emitStatus(SyncStatus.syncing());

    try {
      if (_vaultRootFolderId == null) {
        await initialize();
      }

      if (_startPageToken == null) {
        final token = await _retryOnRateLimit(() => driveApi.changes.getStartPageToken());
        _startPageToken = token.startPageToken;
      }

      var pageToken = _startPageToken;
      var filesChanged = 0;
      String? newStartToken;

      while (pageToken != null) {
        final changeList = await _retryOnRateLimit(() => driveApi.changes.list(
              pageToken!,
              spaces: 'drive',
              $fields:
                  'nextPageToken, newStartPageToken, changes(fileId, removed, file(id, name, mimeType, modifiedTime, trashed, parents))',
            ));

        for (final change in changeList.changes ?? []) {
          final fileId = change.fileId;
          if (fileId == null) continue;

          // If change is a folder, update cache or cleanup
          if (change.file?.mimeType == _folderMimeType) {
            if (change.removed == true || change.file?.trashed == true) {
              final path = _folderIdToPathCache.remove(fileId);
              if (path != null) _folderIdCache.remove(path);
            }
            continue;
          }

          final isRemoved = change.removed == true || change.file?.trashed == true;
          final path = await _resolveFilePath(change);

          if (path != null) {
            filesChanged++;
            if (isRemoved) {
              _fileIdCache.remove(path);
              _idToPathCache.remove(fileId);
              _emitChange(VaultChangeEvent(
                relativePath: path,
                type: VaultChangeType.deleted,
                timestamp: DateTime.now(),
              ));
            } else {
              _fileIdCache[path] = fileId;
              _idToPathCache[fileId] = path;
              _emitChange(VaultChangeEvent(
                relativePath: path,
                type: VaultChangeType.modified,
                timestamp: change.file?.modifiedTime ?? DateTime.now(),
              ));
            }
          }
        }

        if (changeList.newStartPageToken != null) {
          newStartToken = changeList.newStartPageToken;
          pageToken = null;
        } else {
          pageToken = changeList.nextPageToken;
        }
      }

      if (newStartToken != null) {
        _startPageToken = newStartToken;
      } else {
        final freshToken = await _retryOnRateLimit(() => driveApi.changes.getStartPageToken());
        _startPageToken = freshToken.startPageToken;
      }

      final now = DateTime.now();
      _emitStatus(SyncStatus.success(now));
      return SyncResult(success: true, filesChanged: filesChanged);
    } catch (e) {
      final errorMsg = e.toString();
      _emitStatus(SyncStatus.error(errorMsg));
      return SyncResult(success: false, filesChanged: 0, error: errorMsg);
    }
  }

  @override
  Future<void> dispose() async {
    await _statusController.close();
    await _changesController.close();
  }

  String _cleanPath(String path) {
    var p = path.replaceAll('\\', '/').trim();
    p = p.replaceAll(RegExp(r'/+'), '/');
    while (p.startsWith('/')) {
      p = p.substring(1);
    }
    while (p.endsWith('/') && p.isNotEmpty) {
      p = p.substring(0, p.length - 1);
    }
    return p;
  }
}

class _DirectoryTraversal {
  final String folderId;
  final String relativePath;

  _DirectoryTraversal(this.folderId, this.relativePath);
}
