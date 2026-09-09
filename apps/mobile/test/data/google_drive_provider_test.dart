import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:googleapis/drive/v3.dart' as drive;
import 'package:http/http.dart' as http;
import 'package:chrysalis_mobile/core/exceptions/app_exceptions.dart';
import 'package:chrysalis_mobile/data/storage/google_drive_provider.dart';
import 'package:chrysalis_mobile/data/storage/vault_storage_provider.dart';

/// In-memory HTTP client simulating Google Drive v3 REST API endpoints.
class MockDriveHttpClient extends http.BaseClient {
  int _idCounter = 1;
  int _tokenCounter = 100;

  final Map<String, _MockDriveEntry> _driveFiles = {};
  final List<_MockDriveChange> _driveChanges = [];

  /// Number of 429 errors to simulate before succeeding
  int rateLimitSimulationsRemaining = 0;

  /// Whether to simulate multiple pages for changes.list
  bool simulateMultiPageChanges = false;

  MockDriveHttpClient() {
    // Pre-create standard Drive 'root' folder
    _driveFiles['root'] = _MockDriveEntry(
      id: 'root',
      name: 'My Drive',
      mimeType: 'application/vnd.google-apps.folder',
      parents: [],
    );
  }

  /// Injects a remote file entry into Drive (simulating another client).
  String injectRemoteFile({
    required String name,
    required String mimeType,
    required List<String> parents,
    String content = '',
  }) {
    final id = 'remote_file_${_idCounter++}';
    final entry = _MockDriveEntry(
      id: id,
      name: name,
      mimeType: mimeType,
      parents: parents,
      contentBytes: utf8.encode(content),
      modifiedTime: DateTime.now(),
    );
    _driveFiles[id] = entry;
    _driveChanges.add(_MockDriveChange(fileId: id, removed: false, timestamp: DateTime.now()));
    return id;
  }

  /// Injects a remote directory entry into Drive.
  String injectRemoteDirectory({
    required String name,
    required List<String> parents,
  }) {
    final id = 'remote_folder_${_idCounter++}';
    final entry = _MockDriveEntry(
      id: id,
      name: name,
      mimeType: 'application/vnd.google-apps.folder',
      parents: parents,
      modifiedTime: DateTime.now(),
    );
    _driveFiles[id] = entry;
    _driveChanges.add(_MockDriveChange(fileId: id, removed: false, timestamp: DateTime.now()));
    return id;
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (rateLimitSimulationsRemaining > 0) {
      rateLimitSimulationsRemaining--;
      final body = jsonEncode({
        'error': {
          'code': 429,
          'message': 'Rate limit exceeded. User rate limit exceeded.',
        }
      });
      return _jsonResponse(429, body);
    }

    final uri = request.url;
    final path = uri.path;
    final method = request.method;

    // 1. changes.getStartPageToken
    if (method == 'GET' && path.endsWith('/changes/startPageToken')) {
      final body = jsonEncode({
        'kind': 'drive#startPageToken',
        'startPageToken': 'token_${_tokenCounter++}',
      });
      return _jsonResponse(200, body);
    }

    // 2. changes.list
    if (method == 'GET' && path.endsWith('/changes')) {
      final pageToken = uri.queryParameters['pageToken'];

      if (simulateMultiPageChanges && pageToken != 'page_2') {
        // Return page 1 with nextPageToken
        final firstHalf = _driveChanges.take(1).map((c) => _changeToJson(c)).toList();
        final body = jsonEncode({
          'kind': 'drive#changeList',
          'nextPageToken': 'page_2',
          'changes': firstHalf,
        });
        return _jsonResponse(200, body);
      }

      final matchingChanges = _driveChanges.map((c) => _changeToJson(c)).toList();
      final body = jsonEncode({
        'kind': 'drive#changeList',
        'newStartPageToken': 'token_${_tokenCounter++}',
        'changes': matchingChanges,
      });
      return _jsonResponse(200, body);
    }

    // 3. files.get (Metadata or Download)
    if (method == 'GET' && path.contains('/files/')) {
      final fileId = path.split('/files/').last.split('?').first;
      final entry = _driveFiles[fileId];
      if (entry == null || entry.trashed) {
        return _jsonResponse(404, jsonEncode({'error': {'message': 'File not found: $fileId'}}));
      }

      if (uri.queryParameters['alt'] == 'media') {
        final bytes = entry.contentBytes;
        return http.StreamedResponse(
          Stream.value(bytes),
          200,
          headers: {'content-type': '${entry.mimeType}; charset=utf-8', 'content-length': '${bytes.length}'},
        );
      } else {
        return _jsonResponse(200, jsonEncode(_fileToJson(entry)));
      }
    }

    // 4. files.list
    if (method == 'GET' && path.endsWith('/files')) {
      final q = uri.queryParameters['q'] ?? '';
      final matching = <Map<String, dynamic>>[];

      for (final entry in _driveFiles.values) {
        if (entry.trashed) continue;
        if (_matchesQuery(entry, q)) {
          matching.add(_fileToJson(entry));
        }
      }

      final body = jsonEncode({
        'kind': 'drive#fileList',
        'files': matching,
      });
      return _jsonResponse(200, body);
    }

    // 5. files.create (Metadata or Multipart Upload)
    if (method == 'POST' && path.contains('/files')) {
      final List<int> bodyBytes = request is http.Request
          ? request.bodyBytes
          : await request.finalize().fold<List<int>>([], (a, b) => a..addAll(b));

      final newId = 'file_${_idCounter++}';
      String name = 'untitled';
      String mimeType = 'text/markdown';
      List<String> parents = [];
      List<int> content = [];

      final contentType = request.headers['content-type'] ?? '';
      if (contentType.contains('multipart/related')) {
        final raw = utf8.decode(bodyBytes, allowMalformed: true);
        final boundaryMatch = RegExp(r'boundary="?([^"\s;]+)"?').firstMatch(contentType);
        final boundary = boundaryMatch?.group(1) ?? '';
        final delimiter = boundary.isNotEmpty ? '--$boundary' : '--';
        final parts = raw
            .split(delimiter)
            .map((p) => p.trim())
            .where((p) => p.isNotEmpty && p != '--')
            .toList();

        if (parts.isNotEmpty) {
          // Part 0 is metadata
          final metaPart = parts[0];
          final startIdx = metaPart.indexOf('{');
          final endIdx = metaPart.lastIndexOf('}');
          if (startIdx != -1 && endIdx != -1) {
            final jsonStr = metaPart.substring(startIdx, endIdx + 1);
            final meta = jsonDecode(jsonStr) as Map<String, dynamic>;
            name = meta['name'] ?? name;
            mimeType = meta['mimeType'] ?? mimeType;
            if (meta['parents'] != null) {
              parents = List<String>.from(meta['parents'] as List);
            }
          }
        }

        if (parts.length > 1) {
          // Part 1 is content payload
          final contentPart = parts[1];
          final doubleNewline = contentPart.contains('\r\n\r\n')
              ? contentPart.indexOf('\r\n\r\n')
              : contentPart.indexOf('\n\n');
          if (doubleNewline != -1) {
            final sepLen = contentPart.contains('\r\n\r\n') ? 4 : 2;
            final payload = contentPart.substring(doubleNewline + sepLen).trim();
            if (contentPart.contains('base64')) {
              content = base64.decode(payload);
            } else {
              content = utf8.encode(payload);
            }
          }
        }
      } else {
        final raw = utf8.decode(bodyBytes, allowMalformed: true);
        if (raw.trim().startsWith('{')) {
          final meta = jsonDecode(raw) as Map<String, dynamic>;
          name = meta['name'] ?? name;
          mimeType = meta['mimeType'] ?? mimeType;
          if (meta['parents'] != null) {
            parents = List<String>.from(meta['parents'] as List);
          }
        }
      }

      final entry = _MockDriveEntry(
        id: newId,
        name: name,
        mimeType: mimeType,
        parents: parents,
        contentBytes: content,
        modifiedTime: DateTime.now(),
      );

      _driveFiles[newId] = entry;
      _driveChanges.add(_MockDriveChange(fileId: newId, removed: false, timestamp: DateTime.now()));

      return _jsonResponse(200, jsonEncode(_fileToJson(entry)));
    }

    // 6. files.update
    if ((method == 'PATCH' || method == 'PUT') && path.contains('/files/')) {
      final fileId = path.split('/files/').last.split('?').first;
      final entry = _driveFiles[fileId];
      if (entry == null) {
        return _jsonResponse(404, jsonEncode({'error': {'message': 'File not found'}}));
      }

      final List<int> bodyBytes = request is http.Request
          ? request.bodyBytes
          : await request.finalize().fold<List<int>>([], (a, b) => a..addAll(b));

      final contentType = request.headers['content-type'] ?? '';
      if (contentType.contains('multipart/related')) {
        final raw = utf8.decode(bodyBytes, allowMalformed: true);
        final boundaryMatch = RegExp(r'boundary="?([^"\s;]+)"?').firstMatch(contentType);
        final boundary = boundaryMatch?.group(1) ?? '';
        final delimiter = boundary.isNotEmpty ? '--$boundary' : '--';
        final parts = raw
            .split(delimiter)
            .map((p) => p.trim())
            .where((p) => p.isNotEmpty && p != '--')
            .toList();

        // Content is in the last part
        if (parts.isNotEmpty) {
          final contentPart = parts.last;
          final doubleNewline = contentPart.contains('\r\n\r\n')
              ? contentPart.indexOf('\r\n\r\n')
              : contentPart.indexOf('\n\n');
          if (doubleNewline != -1) {
            final sepLen = contentPart.contains('\r\n\r\n') ? 4 : 2;
            final payload = contentPart.substring(doubleNewline + sepLen).trim();
            if (contentPart.contains('base64')) {
              entry.contentBytes = base64.decode(payload);
            } else {
              entry.contentBytes = utf8.encode(payload);
            }
          }
        }
      }

      entry.modifiedTime = DateTime.now();
      _driveChanges.add(_MockDriveChange(fileId: fileId, removed: false, timestamp: DateTime.now()));

      return _jsonResponse(200, jsonEncode(_fileToJson(entry)));
    }

    // 7. files.delete
    if (method == 'DELETE' && path.contains('/files/')) {
      final fileId = path.split('/files/').last.split('?').first;
      final entry = _driveFiles[fileId];
      if (entry != null) {
        entry.trashed = true;
        _driveChanges.add(_MockDriveChange(fileId: fileId, removed: true, timestamp: DateTime.now()));
      }
      return _jsonResponse(204, '');
    }

    return _jsonResponse(404, jsonEncode({'error': {'message': 'Unhandled URL: $uri'}}));
  }

  bool _matchesQuery(_MockDriveEntry entry, String q) {
    if (q.isEmpty) return true;
    if (q.contains("trashed = false") && entry.trashed) return false;

    // Match parent
    final parentMatch = RegExp(r"'([^']+)' in parents").firstMatch(q);
    if (parentMatch != null) {
      final requiredParent = parentMatch.group(1);
      if (!entry.parents.contains(requiredParent)) return false;
    }

    // Match name
    final nameMatch = RegExp(r"name = '([^']+)'").firstMatch(q);
    if (nameMatch != null) {
      final requiredName = nameMatch.group(1);
      if (entry.name != requiredName) return false;
    }

    // Match mimeType
    final mimeMatch = RegExp(r"mimeType = '([^']+)'").firstMatch(q);
    if (mimeMatch != null) {
      final requiredMime = mimeMatch.group(1);
      if (entry.mimeType != requiredMime) return false;
    }

    // Match negative mimeType
    final notMimeMatch = RegExp(r"mimeType != '([^']+)'").firstMatch(q);
    if (notMimeMatch != null) {
      final excludedMime = notMimeMatch.group(1);
      if (entry.mimeType == excludedMime) return false;
    }

    return true;
  }

  Map<String, dynamic> _fileToJson(_MockDriveEntry entry) {
    return {
      'kind': 'drive#file',
      'id': entry.id,
      'name': entry.name,
      'mimeType': entry.mimeType,
      'parents': entry.parents,
      'size': '${entry.contentBytes.length}',
      'modifiedTime': entry.modifiedTime.toIso8601String(),
      'trashed': entry.trashed,
    };
  }

  Map<String, dynamic> _changeToJson(_MockDriveChange change) {
    return {
      'kind': 'drive#change',
      'type': 'file',
      'changeType': 'file',
      'fileId': change.fileId,
      'removed': change.removed,
      'time': change.timestamp.toIso8601String(),
      if (!change.removed && _driveFiles.containsKey(change.fileId))
        'file': _fileToJson(_driveFiles[change.fileId]!),
    };
  }

  http.StreamedResponse _jsonResponse(int status, String body) {
    final bytes = utf8.encode(body);
    return http.StreamedResponse(
      Stream.value(bytes),
      status,
      headers: {'content-type': 'application/json; charset=utf-8', 'content-length': '${bytes.length}'},
    );
  }
}

class _MockDriveEntry {
  final String id;
  String name;
  String mimeType;
  List<String> parents;
  List<int> contentBytes;
  DateTime modifiedTime;
  bool trashed;

  _MockDriveEntry({
    required this.id,
    required this.name,
    required this.mimeType,
    required this.parents,
    List<int>? contentBytes,
    DateTime? modifiedTime,
  })  : contentBytes = contentBytes ?? [],
        modifiedTime = modifiedTime ?? DateTime.now(),
        trashed = false;
}

class _MockDriveChange {
  final String fileId;
  final bool removed;
  final DateTime timestamp;

  _MockDriveChange({
    required this.fileId,
    required this.removed,
    required this.timestamp,
  });
}

void main() {
  group('GoogleDriveProvider Integration & Unit Tests', () {
    late MockDriveHttpClient mockClient;
    late drive.DriveApi driveApi;
    late GoogleDriveProvider provider;

    setUp(() async {
      mockClient = MockDriveHttpClient();
      driveApi = drive.DriveApi(mockClient);
      provider = GoogleDriveProvider(
        driveApi: driveApi,
        vaultRootFolderName: 'chrysalis-test-vault',
      );
      await provider.initialize();
    });

    tearDown(() async {
      await provider.dispose();
    });

    test('metadata conforms to specification', () {
      expect(provider.providerId, equals('google_drive'));
      expect(provider.displayName, contains('Google Drive'));
      expect(provider.vaultRootFolderId, isNotNull);
      expect(provider.startPageToken, isNotNull);
    });

    test('getOrCreateDirectory recursively creates nested directory structures', () async {
      final tasksDirId = await provider.getOrCreateDirectory('TaskNotes/Tasks');
      expect(tasksDirId, isNotEmpty);

      // Subsequent call should hit folderId cache
      final cachedDirId = await provider.getOrCreateDirectory('TaskNotes/Tasks');
      expect(cachedDirId, equals(tasksDirId));
    });

    test('listFiles returns empty list on non-existent directory without creating it', () async {
      final list = await provider.listFiles(directory: 'NonExistent/Directory');
      expect(list, isEmpty);

      // Verify it was NOT created in Drive
      final found = await provider.findDirectory('NonExistent/Directory');
      expect(found, isNull);
    });

    test('file CRUD: write, exists, read, list, and delete with MIME-type handling', () async {
      final changeEvents = <VaultChangeEvent>[];
      final sub = provider.watchChanges.listen(changeEvents.add);

      const filePath = 'TaskNotes/Tasks/sample-review-task.md';
      const initialContent = '---\ntitle: Review Project\nstatus: todo\n---\nBody here';

      // 1. Initial file existence check
      expect(await provider.fileExists(filePath), isFalse);

      // 2. Write new markdown file
      await provider.writeTextFile(filePath, initialContent);
      expect(await provider.fileExists(filePath), isTrue);

      // 3. Write a JSON file (e.g. mailbox events.json)
      const jsonPath = 'System/Inbox/events.json';
      const jsonContent = '{"events": []}';
      await provider.writeTextFile(jsonPath, jsonContent);
      expect(await provider.fileExists(jsonPath), isTrue);
      expect(await provider.readTextFile(jsonPath), equals(jsonContent));

      // 4. Read back text file
      final readBack = await provider.readTextFile(filePath);
      expect(readBack, equals(initialContent));

      // 5. Update file with new content
      const updatedContent = '---\ntitle: Review Project\nstatus: in-progress\n---\nUpdated body';
      await provider.writeTextFile(filePath, updatedContent);
      final readUpdated = await provider.readTextFile(filePath);
      expect(readUpdated, equals(updatedContent));

      // 6. List files in directory
      final files = await provider.listFiles(directory: 'TaskNotes/Tasks');
      expect(files.length, equals(1));
      expect(files.first.relativePath, equals('TaskNotes/Tasks/sample-review-task.md'));
      expect(files.first.sizeBytes, equals(utf8.encode(updatedContent).length));

      // 7. Delete file
      await provider.deleteFile(filePath);
      expect(await provider.fileExists(filePath), isFalse);

      await Future.delayed(const Duration(milliseconds: 20));
      expect(changeEvents.length, greaterThanOrEqualTo(4));
      expect(changeEvents.any((e) => e.type == VaultChangeType.created && e.relativePath == filePath), isTrue);
      expect(changeEvents.any((e) => e.type == VaultChangeType.created && e.relativePath == jsonPath), isTrue);
      expect(changeEvents.any((e) => e.type == VaultChangeType.modified && e.relativePath == filePath), isTrue);
      expect(changeEvents.any((e) => e.type == VaultChangeType.deleted && e.relativePath == filePath), isTrue);

      await sub.cancel();
    });

    test('readTextFile throws VaultStorageException when file does not exist', () async {
      expect(
        () => provider.readTextFile('NonExistent/file.md'),
        throwsA(isA<VaultStorageException>()),
      );
    });

    test('triggerSync correctly resolves remote subfolder files and ignores non-vault files', () async {
      final changeEvents = <VaultChangeEvent>[];
      final sub = provider.watchChanges.listen(changeEvents.add);

      // Pre-create TaskNotes/Tasks in vault
      final tasksDirId = await provider.getOrCreateDirectory('TaskNotes/Tasks');

      // 1. Simulate another device creating a file in TaskNotes/Tasks
      mockClient.injectRemoteFile(
        name: 'sample-remote-task.md',
        mimeType: 'text/markdown',
        parents: [tasksDirId],
        content: '# Remote Task',
      );

      // 2. Simulate another device creating a file outside the Chrysalis vault in root
      mockClient.injectRemoteFile(
        name: 'random-outside-doc.pdf',
        mimeType: 'application/pdf',
        parents: ['root'],
        content: 'PDF outside vault',
      );

      // 3. Simulate another device creating a new folder
      final newRemoteDirId = mockClient.injectRemoteDirectory(
        name: 'Templates',
        parents: [provider.vaultRootFolderId!],
      );
      expect(newRemoteDirId, isNotEmpty);

      // Trigger sync
      final syncResult = await provider.triggerSync();
      expect(syncResult.success, isTrue);

      // Verify that:
      // - The subfolder task was detected with its full relative path
      // - The non-vault document was filtered out
      // - The folder change did NOT emit a file change event
      await Future.delayed(const Duration(milliseconds: 20));

      expect(changeEvents.any((e) => e.relativePath == 'TaskNotes/Tasks/sample-remote-task.md'), isTrue);
      expect(changeEvents.any((e) => e.relativePath.contains('random-outside-doc')), isFalse);
      expect(changeEvents.any((e) => e.relativePath == 'Templates'), isFalse);

      await sub.cancel();
    });

    test('triggerSync handles multi-page changes pagination seamlessly', () async {
      mockClient.simulateMultiPageChanges = true;

      // Write 2 files to generate multiple changes
      await provider.writeTextFile('Note1.md', 'Content 1');
      await provider.writeTextFile('Note2.md', 'Content 2');

      final syncResult = await provider.triggerSync();
      expect(syncResult.success, isTrue);
      expect(syncResult.filesChanged, greaterThanOrEqualTo(1));
    });

    test('recovers from transient HTTP 429 rate limits via exponential backoff', () async {
      // Configure client to fail with 429 once, then succeed
      mockClient.rateLimitSimulationsRemaining = 1;

      const path = 'RateLimitTest.md';
      await provider.writeTextFile(path, 'Testing retry logic');

      expect(await provider.fileExists(path), isTrue);
      expect(await provider.readTextFile(path), equals('Testing retry logic'));
    });
  });
}
