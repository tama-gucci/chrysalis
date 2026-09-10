import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/data/storage/in_memory_vault_storage_provider.dart';
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
  });
}
