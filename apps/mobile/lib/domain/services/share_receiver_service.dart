import 'dart:async';
import 'package:flutter/services.dart';

/// Represents a staged file received through Android Universal Share Sheet.
class SharedFile {
  final String name;
  final String path;
  final String? uri;
  final String? mimeType;
  final int size;

  const SharedFile({
    required this.name,
    required this.path,
    this.uri,
    this.mimeType,
    required this.size,
  });

  factory SharedFile.fromMap(Map<dynamic, dynamic> map) {
    return SharedFile(
      name: map['name']?.toString() ?? '',
      path: map['path']?.toString() ?? '',
      uri: map['uri']?.toString(),
      mimeType: map['mimeType']?.toString(),
      size: (map['size'] as num?)?.toInt() ?? 0,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'name': name,
      'path': path,
      if (uri != null) 'uri': uri,
      if (mimeType != null) 'mimeType': mimeType,
      'size': size,
    };
  }

  @override
  String toString() => 'SharedFile(name: $name, path: $path, size: $size bytes)';
}

/// Represents the payload received via Android Universal Share Sheet (`ACTION_SEND` or `ACTION_SEND_MULTIPLE`).
class SharedPayload {
  final String? action;
  final String? type;
  final String? text;
  final String? subject;
  final List<SharedFile> files;
  final List<String> paths;
  final String? path;
  final String? fileName;

  const SharedPayload({
    this.action,
    this.type,
    this.text,
    this.subject,
    this.files = const [],
    this.paths = const [],
    this.path,
    this.fileName,
  });

  bool get isEmpty =>
      (text == null || text!.trim().isEmpty) &&
      files.isEmpty &&
      paths.isEmpty &&
      (subject == null || subject!.trim().isEmpty);

  bool get isNotEmpty => !isEmpty;

  factory SharedPayload.fromMap(Map<dynamic, dynamic> map) {
    final rawFiles = map['files'] as List<dynamic>? ?? [];
    final files = rawFiles
        .whereType<Map>()
        .map((m) => SharedFile.fromMap(Map<dynamic, dynamic>.from(m)))
        .toList();

    final rawPaths = map['paths'] as List<dynamic>? ?? [];
    final paths = rawPaths.map((p) => p.toString()).toList();

    return SharedPayload(
      action: map['action']?.toString(),
      type: map['type']?.toString(),
      text: map['text']?.toString(),
      subject: map['subject']?.toString(),
      files: files,
      paths: paths.isNotEmpty ? paths : files.map((f) => f.path).toList(),
      path: map['path']?.toString() ?? (files.isNotEmpty ? files.first.path : null),
      fileName: map['fileName']?.toString() ?? (files.isNotEmpty ? files.first.name : null),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      if (action != null) 'action': action,
      if (type != null) 'type': type,
      if (text != null) 'text': text,
      if (subject != null) 'subject': subject,
      'files': files.map((f) => f.toMap()).toList(),
      'paths': paths,
      if (path != null) 'path': path,
      if (fileName != null) 'fileName': fileName,
    };
  }

  @override
  String toString() =>
      'SharedPayload(action: $action, type: $type, text: $text, files: ${files.length})';
}

/// Service that interacts with native Android Universal Share Sheet intent receiver
/// via the MethodChannel `org.chrysalis.mobile/share_receiver`.
class ShareReceiverService {
  final MethodChannel _channel;
  final StreamController<SharedPayload> _shareStreamController =
      StreamController<SharedPayload>.broadcast();

  ShareReceiverService({MethodChannel? channel})
      : _channel = channel ?? const MethodChannel('org.chrysalis.mobile/share_receiver') {
    _channel.setMethodCallHandler(_handleNativeMethodCall);
  }

  /// Stream of shared payloads received while the application is running (warm resume / foreground).
  Stream<SharedPayload> get onShareReceived => _shareStreamController.stream;

  Future<dynamic> _handleNativeMethodCall(MethodCall call) async {
    if (call.method == 'onShareReceived') {
      final arguments = call.arguments;
      if (arguments is Map && !_shareStreamController.isClosed) {
        final payload = SharedPayload.fromMap(Map<dynamic, dynamic>.from(arguments));
        _shareStreamController.add(payload);
      }
    }
  }

  /// Retrieves the pending shared payload from cold start or prior background share.
  /// When [clear] is true (default), native pending state is reset to prevent replay.
  Future<SharedPayload?> getInitialSharedPayload({bool clear = true}) async {
    try {
      final response = await _channel.invokeMapMethod<dynamic, dynamic>(
        'getInitialSharedPayload',
        {'clear': clear},
      );
      if (response == null || response.isEmpty) {
        return null;
      }
      return SharedPayload.fromMap(response);
    } catch (_) {
      return null;
    }
  }

  /// Clears the native pending shared payload.
  Future<void> clearSharedPayload() async {
    try {
      await _channel.invokeMethod<void>('clearSharedPayload');
    } catch (_) {}
  }

  /// Deletes all files in the internal cache `shared_staging` directory.
  Future<bool> clearStagingDirectory() async {
    try {
      final success = await _channel.invokeMethod<bool>('clearStagingDirectory');
      return success ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Shares plaintext or markdown text out to external applications
  /// via Android native Sharesheet (`Intent.createChooser` with `ACTION_SEND`).
  Future<bool> shareContent(String text, {String? title}) async {
    try {
      final args = <String, dynamic>{'text': text};
      if (title != null) {
        args['title'] = title;
      }
      final success = await _channel.invokeMethod<bool>('shareContent', args);
      return success ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Shares a file out to external applications via Android native Sharesheet
  /// using `FileProvider` URI and `Intent.createChooser`.
  Future<bool> shareFile(String filePath, {String? mimeType}) async {
    try {
      final args = <String, dynamic>{'filePath': filePath};
      if (mimeType != null) {
        args['mimeType'] = mimeType;
      }
      final success = await _channel.invokeMethod<bool>('shareFile', args);
      return success ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Displays a native Android Toast notification.
  Future<bool> showNativeToast(String message) async {
    try {
      final success = await _channel.invokeMethod<bool>('showToast', {
        'message': message,
      });
      return success ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Finishes the host native Android Activity.
  Future<void> finishNativeActivity() async {
    try {
      await _channel.invokeMethod<void>('finishActivity');
    } catch (_) {}
  }

  /// Returns true if the host Android Activity was launched strictly as a share target (`ACTION_SEND`).
  Future<bool> isShareLaunch() async {
    try {
      final isShare = await _channel.invokeMethod<bool>('isShareLaunch');
      return isShare ?? false;
    } catch (_) {
      return false;
    }
  }

  void dispose() {
    _channel.setMethodCallHandler(null);
    if (!_shareStreamController.isClosed) {
      _shareStreamController.close();
    }
  }
}
