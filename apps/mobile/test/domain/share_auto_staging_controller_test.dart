import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/core/exceptions/app_exceptions.dart';
import 'package:chrysalis_mobile/data/storage/in_memory_vault_storage_provider.dart';
import 'package:chrysalis_mobile/data/storage/local_vault_storage_provider.dart';
import 'package:chrysalis_mobile/domain/services/share_receiver_service.dart';
import 'package:chrysalis_mobile/domain/services/share_auto_staging_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ShareAutoStagingController Tests', () {
    const channelName = 'org.chrysalis.mobile/share_receiver';
    const channel = MethodChannel(channelName);
    late ShareReceiverService service;
    late Directory tempInboxDir;
    late Directory tempStagingDir;
    late List<String> toastMessages;
    bool finishActivityCalled = false;

    setUp(() async {
      toastMessages = [];
      finishActivityCalled = false;
      tempInboxDir = await Directory.systemTemp.createTemp('chrysalis_test_inbox_');
      tempStagingDir = await Directory.systemTemp.createTemp('chrysalis_test_staging_');

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'showToast') {
          final msg = methodCall.arguments['message']?.toString() ?? '';
          toastMessages.add(msg);
          return true;
        }
        if (methodCall.method == 'finishActivity') {
          finishActivityCalled = true;
          return null;
        }
        if (methodCall.method == 'clearSharedPayload') {
          return null;
        }
        if (methodCall.method == 'isShareLaunch') {
          return false;
        }
        if (methodCall.method == 'getInitialSharedPayload') {
          return null;
        }
        return null;
      });

      service = ShareReceiverService(channel: channel);
    });

    tearDown(() async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null);
      service.dispose();
      if (await tempInboxDir.exists()) {
        await tempInboxDir.delete(recursive: true);
      }
      if (await tempStagingDir.exists()) {
        await tempStagingDir.delete(recursive: true);
      }
    });

    test('stagePayload correctly stages text payload to <timestamp>_shared_text.txt', () async {
      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260914_180000',
      );

      const payload = SharedPayload(
        action: 'android.intent.action.SEND',
        type: 'text/plain',
        text: 'Lecture 1: Technical Drafting & AIA Layering Rules',
      );

      final stagedFiles = await controller.stagePayload(payload);
      expect(stagedFiles.length, equals(1));
      expect(stagedFiles.first, equals('20260914_180000_shared_text.txt'));

      final savedFile = File('${tempInboxDir.path}/20260914_180000_shared_text.txt');
      expect(await savedFile.exists(), isTrue);
      expect(await savedFile.readAsString(), equals('Lecture 1: Technical Drafting & AIA Layering Rules'));
    });

    test('stagePayload correctly stages file payload (e.g. PDF syllabus) to <timestamp>_<filename>', () async {
      // Create a dummy staged file to simulate Android cache copy
      final sourceFile = File('${tempStagingDir.path}/ACC_CAD_Syllabus_Fall2026.pdf');
      await sourceFile.writeAsString('PDF-1.7 mock content for syllabus');

      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260914_180000',
      );

      final payload = SharedPayload(
        action: 'android.intent.action.SEND',
        type: 'application/pdf',
        files: [
          SharedFile(
            name: 'ACC_CAD_Syllabus_Fall2026.pdf',
            path: sourceFile.path,
            size: await sourceFile.length(),
          ),
        ],
      );

      final stagedFiles = await controller.stagePayload(payload);
      expect(stagedFiles.length, equals(1));
      expect(stagedFiles.first, equals('20260914_180000_ACC_CAD_Syllabus_Fall2026.pdf'));

      final destinationFile = File('${tempInboxDir.path}/20260914_180000_ACC_CAD_Syllabus_Fall2026.pdf');
      expect(await destinationFile.exists(), isTrue);
      expect(await destinationFile.readAsString(), equals('PDF-1.7 mock content for syllabus'));
    });

    test('stagePayload synchronizes staged text file to storageProvider if provided', () async {
      final storage = InMemoryVaultStorageProvider();
      await storage.initialize();

      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        storageProvider: storage,
        timestampProvider: () => '20260914_180000',
      );

      const payload = SharedPayload(
        action: 'android.intent.action.SEND',
        type: 'text/plain',
        text: 'Pixel Recorder live transcript chunk',
      );

      await controller.stagePayload(payload);

      final inMemoryContent = await storage.readTextFile('chrysalis/Inbox/20260914_180000_shared_text.txt');
      expect(inMemoryContent, equals('Pixel Recorder live transcript chunk'));
    });

    test('handlePayload displays native Toast and triggers closeCallback when launched strictly as share target', () async {
      bool closeCalled = false;
      String? snackBarMessage;

      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260914_180000',
        onNotification: (msg) => snackBarMessage = msg,
        closeCallback: () async {
          closeCalled = true;
        },
      );

      const payload = SharedPayload(
        action: 'android.intent.action.SEND',
        type: 'text/plain',
        text: 'AutoCAD dimensioning tip',
      );

      final handled = await controller.handlePayload(payload, isStrictShareLaunch: true);
      expect(handled, isTrue);

      expect(toastMessages.length, equals(1));
      expect(toastMessages.first, equals('Saved to Chrysalis Inbox: 20260914_180000_shared_text.txt'));
      expect(snackBarMessage, equals('Saved to Chrysalis Inbox: 20260914_180000_shared_text.txt'));
      expect(closeCalled, isTrue);
    });

    test('handlePayload does not close activity when not launched as strict share target', () async {
      bool closeCalled = false;

      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260914_180000',
        closeCallback: () async {
          closeCalled = true;
        },
      );

      const payload = SharedPayload(
        action: 'android.intent.action.SEND',
        type: 'text/plain',
        text: 'Revit family tip',
      );

      final handled = await controller.handlePayload(payload, isStrictShareLaunch: false);
      expect(handled, isTrue);
      expect(closeCalled, isFalse);
      expect(toastMessages.length, equals(1));
    });

    test('initialize processes pending cold-start share and responds to warm-resume stream', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'isShareLaunch') {
          return true;
        }
        if (methodCall.method == 'getInitialSharedPayload') {
          return <String, dynamic>{
            'action': 'android.intent.action.SEND',
            'type': 'text/plain',
            'text': 'Cold start initial share text',
          };
        }
        if (methodCall.method == 'showToast') {
          toastMessages.add(methodCall.arguments['message']?.toString() ?? '');
          return true;
        }
        if (methodCall.method == 'clearSharedPayload') {
          return null;
        }
        return null;
      });

      bool closeCalled = false;
      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260914_180000',
        closeCallback: () async {
          closeCalled = true;
        },
      );

      await controller.initialize();
      expect(controller.isInitialized, isTrue);
      expect(closeCalled, isTrue);
      expect(toastMessages.contains('Saved to Chrysalis Inbox: 20260914_180000_shared_text.txt'), isTrue);

      controller.dispose();
      expect(controller.isInitialized, isFalse);
    });

    test('handlePayload invokes native finishActivity when no closeCallback provided', () async {
      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260914_180000',
      );

      const payload = SharedPayload(
        action: 'android.intent.action.SEND',
        type: 'text/plain',
        text: 'Default close test',
      );

      await controller.handlePayload(payload, isStrictShareLaunch: true);
      expect(finishActivityCalled, isTrue);
    });

    test('stagePayload disambiguates filenames on collision to prevent overwriting', () async {
      final file1 = File('${tempStagingDir.path}/drawing.pdf');
      await file1.writeAsString('Drawing 1');
      final file2 = File('${tempStagingDir.path}/drawing_alt.pdf');
      await file2.writeAsString('Drawing 2');

      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260914_180000',
      );

      // Pre-create an existing file in inbox
      final existing = File('${tempInboxDir.path}/20260914_180000_drawing.pdf');
      await existing.writeAsString('Pre-existing drawing');

      final payload = SharedPayload(
        action: 'android.intent.action.SEND_MULTIPLE',
        type: 'application/pdf',
        files: [
          SharedFile(name: 'drawing.pdf', path: file1.path, size: 9),
          SharedFile(name: 'drawing.pdf', path: file2.path, size: 9),
        ],
      );

      final staged = await controller.stagePayload(payload);
      expect(staged.length, equals(2));
      expect(staged[0], equals('20260914_180000_drawing_1.pdf'));
      expect(staged[1], equals('20260914_180000_drawing_2.pdf'));

      // Verify original file is untouched
      expect(await existing.readAsString(), equals('Pre-existing drawing'));
      expect(await File('${tempInboxDir.path}/20260914_180000_drawing_1.pdf').readAsString(), equals('Drawing 1'));
      expect(await File('${tempInboxDir.path}/20260914_180000_drawing_2.pdf').readAsString(), equals('Drawing 2'));
    });

    test('stagePayload safely stages binary files without crashing or corrupting text storage', () async {
      final storage = InMemoryVaultStorageProvider();
      await storage.initialize();

      final binaryFile = File('${tempStagingDir.path}/binary_data.pdf');
      // Write bytes that are invalid UTF-8
      await binaryFile.writeAsBytes([0xFF, 0xFE, 0xFD, 0x00, 0x12]);

      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        storageProvider: storage,
        timestampProvider: () => '20260914_180000',
      );

      final payload = SharedPayload(
        action: 'android.intent.action.SEND',
        type: 'application/pdf',
        files: [
          SharedFile(name: 'binary_data.pdf', path: binaryFile.path, size: 5),
        ],
      );

      final staged = await controller.stagePayload(payload);
      expect(staged.length, equals(1));
      expect(staged.first, equals('20260914_180000_binary_data.pdf'));

      final destination = File('${tempInboxDir.path}/20260914_180000_binary_data.pdf');
      expect(await destination.exists(), isTrue);
      expect(await destination.readAsBytes(), equals([0xFF, 0xFE, 0xFD, 0x00, 0x12]));

      // Binary file should not be stored in text storageProvider
      expect(await storage.fileExists('chrysalis/Inbox/20260914_180000_binary_data.pdf'), isFalse);
    });

    test('stagePayload correctly stages screenshot image payload (PNG, JPEG, WebP) with byte preservation and Toast confirmation', () async {
      final pngBytes = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x01];
      final jpgBytes = [0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46];
      final webpBytes = [0x52, 0x49, 0x46, 0x46, 0x1A, 0x00, 0x00, 0x00, 0x57, 0x45, 0x42, 0x50];

      final pngFile = File('${tempStagingDir.path}/Screenshot_20260910_CAD.png');
      await pngFile.writeAsBytes(pngBytes);
      final jpgFile = File('${tempStagingDir.path}/Site_Inspection_Photo.jpg');
      await jpgFile.writeAsBytes(jpgBytes);
      final webpFile = File('${tempStagingDir.path}/Floorplan_Render.webp');
      await webpFile.writeAsBytes(webpBytes);

      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260910_223000',
      );

      final payload = SharedPayload(
        action: 'android.intent.action.SEND_MULTIPLE',
        type: 'image/*',
        files: [
          SharedFile(
            name: 'Screenshot_20260910_CAD.png',
            path: pngFile.path,
            mimeType: 'image/png',
            size: pngBytes.length,
          ),
          SharedFile(
            name: 'Site_Inspection_Photo.jpg',
            path: jpgFile.path,
            mimeType: 'image/jpeg',
            size: jpgBytes.length,
          ),
          SharedFile(
            name: 'Floorplan_Render.webp',
            path: webpFile.path,
            mimeType: 'image/webp',
            size: webpBytes.length,
          ),
        ],
      );

      final stagedFiles = await controller.stagePayload(payload);
      expect(stagedFiles.length, equals(3));
      expect(stagedFiles[0], equals('20260910_223000_Screenshot_20260910_CAD.png'));
      expect(stagedFiles[1], equals('20260910_223000_Site_Inspection_Photo.jpg'));
      expect(stagedFiles[2], equals('20260910_223000_Floorplan_Render.webp'));

      // Verify binary byte preservation
      final stagedPng = File('${tempInboxDir.path}/${stagedFiles[0]}');
      expect(await stagedPng.exists(), isTrue);
      expect(await stagedPng.readAsBytes(), equals(pngBytes));

      final stagedJpg = File('${tempInboxDir.path}/${stagedFiles[1]}');
      expect(await stagedJpg.exists(), isTrue);
      expect(await stagedJpg.readAsBytes(), equals(jpgBytes));

      final stagedWebp = File('${tempInboxDir.path}/${stagedFiles[2]}');
      expect(await stagedWebp.exists(), isTrue);
      expect(await stagedWebp.readAsBytes(), equals(webpBytes));
    });

    test('stagePayload correctly stages audio stream (.m4a, .mp3, .wav, .opus, .flac) with companion lecture transcript', () async {
      final audioBytes = [0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70, 0x4D, 0x34, 0x41];
      final audioFile = File('${tempStagingDir.path}/AIA_Standards_Lecture.m4a');
      await audioFile.writeAsBytes(audioBytes);

      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260910_230000',
      );

      final payload = SharedPayload(
        action: 'android.intent.action.SEND',
        type: 'audio/mp4',
        text: 'Transcription: AIA Cad layer guidelines require all dimension layers to follow A-ANNO-DIMS.',
        files: [
          SharedFile(
            name: 'AIA_Standards_Lecture.m4a',
            path: audioFile.path,
            mimeType: 'audio/mp4',
            size: audioBytes.length,
          ),
        ],
      );

      final stagedFiles = await controller.stagePayload(payload);
      expect(stagedFiles.length, equals(2));
      expect(stagedFiles[0], equals('20260910_230000_AIA_Standards_Lecture.m4a'));
      expect(stagedFiles[1], equals('20260910_230000_shared_notes.txt'));

      // Verify audio binary file
      final stagedAudio = File('${tempInboxDir.path}/${stagedFiles[0]}');
      expect(await stagedAudio.exists(), isTrue);
      expect(await stagedAudio.readAsBytes(), equals(audioBytes));

      // Verify companion transcript text file
      final stagedTranscript = File('${tempInboxDir.path}/${stagedFiles[1]}');
      expect(await stagedTranscript.exists(), isTrue);
      expect(await stagedTranscript.readAsString(), contains('A-ANNO-DIMS'));
    });

    test('handlePayload triggers Toast confirmations and closes activity for screenshot share target launch', () async {
      bool closeCalled = false;
      final imageFile = File('${tempStagingDir.path}/Screenshot_Quick_Capture.png');
      await imageFile.writeAsBytes([0x89, 0x50, 0x4E, 0x47]);

      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260910_231500',
        closeCallback: () async {
          closeCalled = true;
        },
      );

      final payload = SharedPayload(
        action: 'android.intent.action.SEND',
        type: 'image/png',
        files: [
          SharedFile(
            name: 'Screenshot_Quick_Capture.png',
            path: imageFile.path,
            mimeType: 'image/png',
            size: 4,
          ),
        ],
      );

      final handled = await controller.handlePayload(payload, isStrictShareLaunch: true);
      expect(handled, isTrue);
      expect(closeCalled, isTrue);
      expect(toastMessages.contains('Saved to Chrysalis Inbox: 20260910_231500_Screenshot_Quick_Capture.png'), isTrue);
    });

    test('stagePayload handles multiple screenshots with identical basenames via collision disambiguation', () async {
      final img1 = File('${tempStagingDir.path}/screenshot_batch_1.png');
      await img1.writeAsString('Screenshot Content 1');
      final img2 = File('${tempStagingDir.path}/screenshot_batch_2.png');
      await img2.writeAsString('Screenshot Content 2');
      final img3 = File('${tempStagingDir.path}/screenshot_batch_3.png');
      await img3.writeAsString('Screenshot Content 3');

      final controller = ShareAutoStagingController(
        shareReceiverService: service,
        inboxDirectory: tempInboxDir,
        timestampProvider: () => '20260910_233000',
      );

      final payload = SharedPayload(
        action: 'android.intent.action.SEND_MULTIPLE',
        type: 'image/png',
        files: [
          SharedFile(name: 'Screenshot.png', path: img1.path, size: 20),
          SharedFile(name: 'Screenshot.png', path: img2.path, size: 20),
          SharedFile(name: 'Screenshot.png', path: img3.path, size: 20),
        ],
      );

      final staged = await controller.stagePayload(payload);
      expect(staged.length, equals(3));
      expect(staged[0], equals('20260910_233000_Screenshot.png'));
      expect(staged[1], equals('20260910_233000_Screenshot_1.png'));
      expect(staged[2], equals('20260910_233000_Screenshot_2.png'));

      expect(await File('${tempInboxDir.path}/${staged[0]}').readAsString(), equals('Screenshot Content 1'));
      expect(await File('${tempInboxDir.path}/${staged[1]}').readAsString(), equals('Screenshot Content 2'));
      expect(await File('${tempInboxDir.path}/${staged[2]}').readAsString(), equals('Screenshot Content 3'));
    });

    test('resolveVaultDirectoryFromInbox correctly derives vault root from /chrysalis/Inbox', () {
      final inboxDir = Directory('D:/synthetic_vault/chrysalis/Inbox');
      final vaultDir = ShareAutoStagingController.resolveVaultDirectoryFromInbox(inboxDir);
      expect(vaultDir.path.replaceAll('\\', '/'), equals('D:/synthetic_vault'));
    });

    test('resolveVaultDirectoryFromInbox correctly derives vault root from /Inbox', () {
      final inboxDir = Directory('D:/synthetic_vault/Inbox');
      final vaultDir = ShareAutoStagingController.resolveVaultDirectoryFromInbox(inboxDir);
      expect(vaultDir.path.replaceAll('\\', '/'), equals('D:/synthetic_vault'));
    });

    test('resolveVaultDirectoryFromInbox handles case variations (Titlecase, uppercase, lowercase)', () {
      for (final path in [
        'D:/synthetic_vault/Chrysalis/Inbox',
        'D:/synthetic_vault/CHRYSALIS/INBOX',
        'D:/synthetic_vault/chrysalis/inbox',
        'D:/synthetic_vault/Chrysalis/inbox',
        'D:/synthetic_vault/CHRYSALIS/Inbox',
      ]) {
        final inboxDir = Directory(path);
        final vaultDir = ShareAutoStagingController.resolveVaultDirectoryFromInbox(inboxDir);
        expect(vaultDir.path.replaceAll('\\', '/'), equals('D:/synthetic_vault'),
            reason: 'Failed for path: $path');
      }

      for (final path in [
        'D:/synthetic_vault/Inbox',
        'D:/synthetic_vault/inbox',
        'D:/synthetic_vault/INBOX',
      ]) {
        final inboxDir = Directory(path);
        final vaultDir = ShareAutoStagingController.resolveVaultDirectoryFromInbox(inboxDir);
        expect(vaultDir.path.replaceAll('\\', '/'), equals('D:/synthetic_vault'),
            reason: 'Failed for path: $path');
      }
    });

    test('resolveDefaultInboxDirectory synchronously resolves valid directory', () {
      final dir = ShareAutoStagingController.resolveDefaultInboxDirectory();
      expect(dir.path, isNotEmpty);
    });

    test('resolveDefaultInboxDirectoryAsync asynchronously resolves valid directory', () async {
      final dir = await ShareAutoStagingController.resolveDefaultInboxDirectoryAsync();
      expect(dir.path, isNotEmpty);
    });

    test('resolveDefaultVaultDirectoryAsync asynchronously resolves valid vault root', () async {
      final vault = await ShareAutoStagingController.resolveDefaultVaultDirectoryAsync();
      expect(vault.path, isNotEmpty);
    });

    test('LocalVaultStorageProvider enforces directory traversal defenses', () async {
      final tempVault = await Directory.systemTemp.createTemp('vault_traversal_test_');
      try {
        final provider = LocalVaultStorageProvider(rootDirectory: tempVault);
        await provider.initialize();

        expect(
          () => provider.writeTextFile('../../outside_probe.txt', 'danger'),
          throwsA(isA<VaultStorageException>()),
        );

        expect(
          () => provider.readTextFile('../../outside_probe.txt'),
          throwsA(isA<VaultStorageException>()),
        );

        expect(
          () => provider.deleteFile('../../outside_probe.txt'),
          throwsA(isA<VaultStorageException>()),
        );

        expect(
          () => provider.fileExists('../../outside_probe.txt'),
          throwsA(isA<VaultStorageException>()),
        );

        expect(
          () => provider.listFiles(directory: '../../'),
          throwsA(isA<VaultStorageException>()),
        );

        await provider.dispose();
      } finally {
        if (await tempVault.exists()) {
          await tempVault.delete(recursive: true);
        }
      }
    });
  });
}
