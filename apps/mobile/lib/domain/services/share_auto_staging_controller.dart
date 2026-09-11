import 'dart:async';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import '../../data/storage/vault_storage_provider.dart';
import 'share_receiver_service.dart';

/// Callback invoked to display in-app notifications (e.g. SnackBar).
typedef ShareNotificationCallback = void Function(String message);

/// Callback invoked to finish/close the host activity.
typedef ShareCloseCallback = Future<void> Function();

/// Controls auto-staging of shared payloads (files or text) received via Android
/// Universal Share Sheet directly into `chrysalis/Inbox/`.
class ShareAutoStagingController {
  final ShareReceiverService shareReceiverService;
  final Directory inboxDirectory;
  final VaultStorageProvider? storageProvider;
  final ShareNotificationCallback? onNotification;
  final String Function()? timestampProvider;
  final ShareCloseCallback? closeCallback;

  StreamSubscription<SharedPayload>? _shareSubscription;
  bool _isInitialized = false;

  ShareAutoStagingController({
    required this.shareReceiverService,
    Directory? inboxDirectory,
    this.storageProvider,
    this.onNotification,
    this.timestampProvider,
    this.closeCallback,
  }) : inboxDirectory = inboxDirectory ?? resolveDefaultInboxDirectory();

  bool get isInitialized => _isInitialized;

  /// Resolves the default vault `chrysalis/Inbox` directory synchronously.
  static Directory resolveDefaultInboxDirectory() {
    final envVault = Platform.environment['CHRYSALIS_VAULT_PATH']
        ?.trim()
        .replaceAll('"', '')
        .replaceAll("'", '');
    if (envVault != null && envVault.trim().isNotEmpty) {
      final candidateInbox = Directory(p.join(envVault, 'chrysalis', 'Inbox'));
      if (candidateInbox.existsSync()) return candidateInbox;
      final fallbackInbox = Directory(p.join(envVault, 'Inbox'));
      if (fallbackInbox.existsSync()) return fallbackInbox;
      return candidateInbox;
    }

    for (final candidate in [
      'g:/My Drive/vault/chrysalis/Inbox',
      'G:/My Drive/vault/chrysalis/Inbox',
      'g:/My Drive/vault/Inbox',
      'G:/My Drive/vault/Inbox',
      'g:/My Drive/chrysalis/chrysalis/Inbox',
      'G:/My Drive/chrysalis/chrysalis/Inbox',
      'g:/My Drive/chrysalis/Inbox',
      'G:/My Drive/chrysalis/Inbox',
    ]) {
      final dir = Directory(candidate);
      if (dir.existsSync()) {
        return dir;
      }
    }

    if (Platform.isAndroid) {
      for (final candidate in [
        '/storage/emulated/0/Android/data/com.chrysalis.mobile.chrysalis_mobile/files',
        '/data/user/0/com.chrysalis.mobile.chrysalis_mobile/files',
        '/data/data/com.chrysalis.mobile.chrysalis_mobile/files',
      ]) {
        final dir = Directory(candidate);
        if (dir.existsSync()) {
          return Directory(p.join(candidate, 'chrysalis', 'Inbox'));
        }
      }
      return Directory(p.join(Directory.systemTemp.path, 'chrysalis', 'Inbox'));
    }

    return Directory(p.join(Directory.current.path, 'chrysalis', 'Inbox'));
  }

  /// Resolves the default vault `chrysalis/Inbox` directory asynchronously.
  ///
  /// Provides safe Android-native fallback using [getApplicationDocumentsDirectory]
  /// from `path_provider` when running on Android where drive letters do not exist
  /// and `Directory.current` is `/` (read-only).
  static Future<Directory> resolveDefaultInboxDirectoryAsync() async {
    final envVault = Platform.environment['CHRYSALIS_VAULT_PATH']
        ?.trim()
        .replaceAll('"', '')
        .replaceAll("'", '');
    if (envVault != null && envVault.trim().isNotEmpty) {
      final candidateInbox = Directory(p.join(envVault, 'chrysalis', 'Inbox'));
      if (await candidateInbox.exists()) return candidateInbox;
      final fallbackInbox = Directory(p.join(envVault, 'Inbox'));
      if (await fallbackInbox.exists()) return fallbackInbox;
      return candidateInbox;
    }

    for (final candidate in [
      'g:/My Drive/vault/chrysalis/Inbox',
      'G:/My Drive/vault/chrysalis/Inbox',
      'g:/My Drive/vault/Inbox',
      'G:/My Drive/vault/Inbox',
      'g:/My Drive/chrysalis/chrysalis/Inbox',
      'G:/My Drive/chrysalis/chrysalis/Inbox',
      'g:/My Drive/chrysalis/Inbox',
      'G:/My Drive/chrysalis/Inbox',
    ]) {
      final dir = Directory(candidate);
      if (await dir.exists()) {
        return dir;
      }
    }

    if (Platform.isAndroid) {
      try {
        final appDocDir = await getApplicationDocumentsDirectory();
        return Directory(p.join(appDocDir.path, 'chrysalis', 'Inbox'));
      } catch (_) {}
    }

    return resolveDefaultInboxDirectory();
  }

  /// Derives the root vault directory from an inbox directory.
  ///
  /// For example, `<vault>/chrysalis/Inbox` -> `<vault>`,
  /// and `<vault>/Inbox` -> `<vault>`.
  static Directory resolveVaultDirectoryFromInbox(Directory inboxDir) {
    final normalized = p.normalize(inboxDir.path).replaceAll('\\', '/');
    final lower = normalized.toLowerCase();
    if (lower.endsWith('/chrysalis/inbox')) {
      return inboxDir.parent.parent;
    } else if (lower.endsWith('/inbox')) {
      if (p.basename(inboxDir.parent.path).toLowerCase() == 'chrysalis') {
        return inboxDir.parent.parent;
      }
      return inboxDir.parent;
    }
    if (p.basename(inboxDir.parent.path).toLowerCase() == 'chrysalis') {
      return inboxDir.parent.parent;
    }
    return inboxDir.parent;
  }

  /// Resolves the root vault directory asynchronously.
  static Future<Directory> resolveDefaultVaultDirectoryAsync() async {
    final inboxDir = await resolveDefaultInboxDirectoryAsync();
    return resolveVaultDirectoryFromInbox(inboxDir);
  }

  /// Formats the current local timestamp for file naming: `YYYYMMDD_HHmmss`.
  String currentTimestamp() {
    if (timestampProvider != null) {
      return timestampProvider!();
    }
    final now = DateTime.now();
    final y = now.year.toString().padLeft(4, '0');
    final m = now.month.toString().padLeft(2, '0');
    final d = now.day.toString().padLeft(2, '0');
    final h = now.hour.toString().padLeft(2, '0');
    final min = now.minute.toString().padLeft(2, '0');
    final s = now.second.toString().padLeft(2, '0');
    return '$y$m${d}_$h$min$s';
  }

  /// Initializes the controller:
  /// 1. Processes any pending cold-start shared payload.
  /// 2. Listens to warm-resume incoming shares on [shareReceiverService.onShareReceived].
  Future<void> initialize() async {
    if (_isInitialized) return;
    _isInitialized = true;

    final isShareLaunch = await shareReceiverService.isShareLaunch();
    final pendingPayload = await shareReceiverService.getInitialSharedPayload(clear: true);

    if (pendingPayload != null && pendingPayload.isNotEmpty) {
      await handlePayload(pendingPayload, isStrictShareLaunch: isShareLaunch);
    }

    _shareSubscription = shareReceiverService.onShareReceived.listen((payload) async {
      if (payload.isNotEmpty) {
        await handlePayload(payload, isStrictShareLaunch: false);
      }
    });
  }

  static bool _isTextExtension(String filePath) {
    final ext = p.extension(filePath).toLowerCase();
    return const {
      '.txt',
      '.md',
      '.json',
      '.csv',
      '.yaml',
      '.yml',
      '.xml',
      '.html',
      '.ics',
      '.log',
    }.contains(ext);
  }

  String _resolveUniqueFileName(String baseName, Set<String> usedInBatch) {
    var candidateName = baseName;
    var candidateFile = File(p.join(inboxDirectory.path, candidateName));

    if (candidateFile.existsSync() || usedInBatch.contains(candidateName)) {
      final ext = p.extension(baseName);
      final withoutExt = p.withoutExtension(baseName);
      var counter = 1;
      while (candidateFile.existsSync() || usedInBatch.contains(candidateName)) {
        candidateName = '${withoutExt}_$counter$ext';
        candidateFile = File(p.join(inboxDirectory.path, candidateName));
        counter++;
      }
    }
    usedInBatch.add(candidateName);
    return candidateName;
  }

  /// Writes the received [SharedPayload] to `chrysalis/Inbox/`.
  /// Returns a list of filenames saved in the Inbox.
  Future<List<String>> stagePayload(SharedPayload payload) async {
    if (payload.isEmpty) return const [];

    if (!await inboxDirectory.exists()) {
      await inboxDirectory.create(recursive: true);
    }

    final ts = currentTimestamp();
    final stagedNames = <String>[];
    final usedInBatch = <String>{};

    // 1. Stage shared files (e.g. PDF syllabus, audio recordings, images)
    if (payload.files.isNotEmpty) {
      for (final sharedFile in payload.files) {
        final sanitizedOriginalName = p.basename(sharedFile.name).replaceAll(RegExp(r'[\\/:*?"<>|]'), '_');
        final baseFileName = '${ts}_$sanitizedOriginalName';
        final targetFileName = _resolveUniqueFileName(baseFileName, usedInBatch);
        final destinationFile = File(p.join(inboxDirectory.path, targetFileName));

        final sourceFile = File(sharedFile.path);
        if (await sourceFile.exists()) {
          await sourceFile.copy(destinationFile.path);
        } else {
          // Fallback if file content was provided or staged in cache
          await destinationFile.writeAsString('Shared payload: ${sharedFile.name}');
        }

        if (storageProvider != null && _isTextExtension(destinationFile.path)) {
          try {
            final content = await destinationFile.readAsString();
            await storageProvider!.writeTextFile('chrysalis/Inbox/$targetFileName', content);
          } catch (_) {
            // Binary files or read errors are safely ignored; physical file already staged on disk
          }
        }

        stagedNames.add(targetFileName);
      }
    }

    // 2. Stage shared text (e.g. Pixel Recorder lecture transcripts)
    if (payload.text != null && payload.text!.trim().isNotEmpty) {
      // If no files were staged, write text to `<timestamp>_shared_text.txt`
      // If files were also staged, write text as companion transcript
      final baseFileName = stagedNames.isEmpty
          ? '${ts}_shared_text.txt'
          : '${ts}_shared_notes.txt';
      final targetFileName = _resolveUniqueFileName(baseFileName, usedInBatch);

      final destinationFile = File(p.join(inboxDirectory.path, targetFileName));
      final textContent = payload.text!.trim();
      await destinationFile.writeAsString(textContent);

      if (storageProvider != null) {
        await storageProvider!.writeTextFile('chrysalis/Inbox/$targetFileName', textContent);
      }

      stagedNames.add(targetFileName);
    }

    return stagedNames;
  }

  /// Processes an incoming [payload]:
  /// Stages to disk, displays confirmation notification (Toast / SnackBar),
  /// and terminates activity if launched strictly as a share target.
  Future<bool> handlePayload(
    SharedPayload payload, {
    required bool isStrictShareLaunch,
  }) async {
    if (payload.isEmpty) return false;

    final stagedFiles = await stagePayload(payload);
    if (stagedFiles.isEmpty) return false;

    for (final filename in stagedFiles) {
      final confirmation = 'Saved to Chrysalis Inbox: $filename';
      await shareReceiverService.showNativeToast(confirmation);
      onNotification?.call(confirmation);
    }

    await shareReceiverService.clearSharedPayload();

    if (isStrictShareLaunch) {
      if (closeCallback != null) {
        await closeCallback!();
      } else {
        await shareReceiverService.finishNativeActivity();
        await SystemNavigator.pop();
      }
    }

    return true;
  }

  void dispose() {
    _shareSubscription?.cancel();
    _isInitialized = false;
  }
}
