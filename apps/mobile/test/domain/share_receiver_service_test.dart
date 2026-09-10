import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/domain/services/share_receiver_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ShareReceiverService Tests', () {
    const channelName = 'org.chrysalis.mobile/share_receiver';
    const channel = MethodChannel(channelName);
    late ShareReceiverService service;

    setUp(() {
      service = ShareReceiverService(channel: channel);
    });

    tearDown(() {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null);
      service.dispose();
    });

    test('getInitialSharedPayload returns null when native has no pending share', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'getInitialSharedPayload') {
          return null;
        }
        return null;
      });

      final payload = await service.getInitialSharedPayload();
      expect(payload, isNull);
    });

    test('getInitialSharedPayload correctly parses ACTION_SEND text payload', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'getInitialSharedPayload') {
          expect(methodCall.arguments, equals({'clear': true}));
          return <String, dynamic>{
            'action': 'android.intent.action.SEND',
            'type': 'text/plain',
            'text': 'Task: Finalize architecture diagram #chrysalis/dev',
            'subject': 'Architecture Note',
          };
        }
        return null;
      });

      final payload = await service.getInitialSharedPayload(clear: true);
      expect(payload, isNotNull);
      expect(payload!.action, equals('android.intent.action.SEND'));
      expect(payload.type, equals('text/plain'));
      expect(payload.text, equals('Task: Finalize architecture diagram #chrysalis/dev'));
      expect(payload.subject, equals('Architecture Note'));
      expect(payload.files, isEmpty);
      expect(payload.paths, isEmpty);
      expect(payload.isNotEmpty, isTrue);
    });

    test('getInitialSharedPayload correctly parses ACTION_SEND file payload with staging path', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'getInitialSharedPayload') {
          return <String, dynamic>{
            'action': 'android.intent.action.SEND',
            'type': 'application/pdf',
            'files': [
              {
                'name': 'research_paper.pdf',
                'path': '/data/user/0/com.chrysalis.mobile/cache/shared_staging/research_paper.pdf',
                'uri': 'content://com.android.providers.media.documents/document/1234',
                'mimeType': 'application/pdf',
                'size': 2048576,
              }
            ],
            'paths': [
              '/data/user/0/com.chrysalis.mobile/cache/shared_staging/research_paper.pdf',
            ],
            'path': '/data/user/0/com.chrysalis.mobile/cache/shared_staging/research_paper.pdf',
            'fileName': 'research_paper.pdf',
          };
        }
        return null;
      });

      final payload = await service.getInitialSharedPayload();
      expect(payload, isNotNull);
      expect(payload!.action, equals('android.intent.action.SEND'));
      expect(payload.type, equals('application/pdf'));
      expect(payload.files.length, equals(1));
      expect(payload.files.first.name, equals('research_paper.pdf'));
      expect(payload.files.first.path, contains('shared_staging/research_paper.pdf'));
      expect(payload.files.first.size, equals(2048576));
      expect(payload.paths.first, contains('shared_staging/research_paper.pdf'));
      expect(payload.path, contains('shared_staging/research_paper.pdf'));
      expect(payload.fileName, equals('research_paper.pdf'));
    });

    test('getInitialSharedPayload correctly parses ACTION_SEND_MULTIPLE multiple files', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'getInitialSharedPayload') {
          return <String, dynamic>{
            'action': 'android.intent.action.SEND_MULTIPLE',
            'type': '*/*',
            'files': [
              {
                'name': 'doc1.pdf',
                'path': '/cache/shared_staging/doc1.pdf',
                'mimeType': 'application/pdf',
                'size': 1024,
              },
              {
                'name': 'doc2.png',
                'path': '/cache/shared_staging/doc2.png',
                'mimeType': 'image/png',
                'size': 2048,
              },
            ],
            'paths': [
              '/cache/shared_staging/doc1.pdf',
              '/cache/shared_staging/doc2.png',
            ],
            'path': '/cache/shared_staging/doc1.pdf',
            'fileName': 'doc1.pdf',
          };
        }
        return null;
      });

      final payload = await service.getInitialSharedPayload();
      expect(payload, isNotNull);
      expect(payload!.action, equals('android.intent.action.SEND_MULTIPLE'));
      expect(payload.files.length, equals(2));
      expect(payload.files[0].name, equals('doc1.pdf'));
      expect(payload.files[1].name, equals('doc2.png'));
      expect(payload.paths.length, equals(2));
    });

    test('clearSharedPayload and clearStagingDirectory invoke native methods', () async {
      bool clearCalled = false;
      bool clearStagingCalled = false;

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'clearSharedPayload') {
          clearCalled = true;
          return null;
        }
        if (methodCall.method == 'clearStagingDirectory') {
          clearStagingCalled = true;
          return true;
        }
        return null;
      });

      await service.clearSharedPayload();
      expect(clearCalled, isTrue);

      final stagingCleared = await service.clearStagingDirectory();
      expect(stagingCleared, isTrue);
      expect(clearStagingCalled, isTrue);
    });

    test('onShareReceived stream emits payload when native invokes onShareReceived', () async {
      final receivedFuture = service.onShareReceived.first;

      // Simulate native calling onShareReceived over binary messenger
      final messenger = TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
      const codec = StandardMethodCodec();
      final ByteData message = codec.encodeMethodCall(
        const MethodCall('onShareReceived', <String, dynamic>{
          'action': 'android.intent.action.SEND',
          'type': 'text/plain',
          'text': 'Warm resume incoming shared note',
        }),
      );

      await messenger.handlePlatformMessage(
        channelName,
        message,
        (ByteData? reply) {},
      );

      final payload = await receivedFuture;
      expect(payload.text, equals('Warm resume incoming shared note'));
      expect(payload.action, equals('android.intent.action.SEND'));
    });

    test('SharedPayload isEmpty and isNotEmpty evaluate correctly', () {
      const emptyPayload = SharedPayload();
      expect(emptyPayload.isEmpty, isTrue);
      expect(emptyPayload.isNotEmpty, isFalse);

      const whitespacePayload = SharedPayload(text: '   ', subject: '  ');
      expect(whitespacePayload.isEmpty, isTrue);

      const textPayload = SharedPayload(text: 'Hello Chrysalis');
      expect(textPayload.isEmpty, isFalse);
      expect(textPayload.isNotEmpty, isTrue);

      const subjectPayload = SharedPayload(subject: 'Research Note');
      expect(subjectPayload.isEmpty, isFalse);

      const filePayload = SharedPayload(
        files: [
          SharedFile(name: 'a.pdf', path: '/path/a.pdf', size: 100),
        ],
      );
      expect(filePayload.isEmpty, isFalse);
    });

    test('SharedFile and SharedPayload toMap and fromMap are symmetrical', () {
      const originalFile = SharedFile(
        name: 'test.pdf',
        path: '/staging/test.pdf',
        uri: 'content://docs/1',
        mimeType: 'application/pdf',
        size: 4096,
      );
      final fileMap = originalFile.toMap();
      final parsedFile = SharedFile.fromMap(fileMap);

      expect(parsedFile.name, equals(originalFile.name));
      expect(parsedFile.path, equals(originalFile.path));
      expect(parsedFile.uri, equals(originalFile.uri));
      expect(parsedFile.mimeType, equals(originalFile.mimeType));
      expect(parsedFile.size, equals(originalFile.size));

      final originalPayload = SharedPayload(
        action: 'android.intent.action.SEND',
        type: 'application/pdf',
        text: 'Document note',
        subject: 'PDF Share',
        files: [originalFile],
        paths: ['/staging/test.pdf'],
        path: '/staging/test.pdf',
        fileName: 'test.pdf',
      );
      final payloadMap = originalPayload.toMap();
      final parsedPayload = SharedPayload.fromMap(payloadMap);

      expect(parsedPayload.action, equals(originalPayload.action));
      expect(parsedPayload.type, equals(originalPayload.type));
      expect(parsedPayload.text, equals(originalPayload.text));
      expect(parsedPayload.subject, equals(originalPayload.subject));
      expect(parsedPayload.files.length, equals(1));
      expect(parsedPayload.files.first.name, equals('test.pdf'));
      expect(parsedPayload.paths, equals(['/staging/test.pdf']));
      expect(parsedPayload.path, equals('/staging/test.pdf'));
      expect(parsedPayload.fileName, equals('test.pdf'));
    });

    test('getInitialSharedPayload handles channel platform exceptions by returning null', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        throw PlatformException(code: 'ERROR', message: 'Failed');
      });

      final payload = await service.getInitialSharedPayload();
      expect(payload, isNull);
    });

    test('clearStagingDirectory returns false on platform exception', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        throw PlatformException(code: 'ERROR', message: 'Failed to clear');
      });

      final success = await service.clearStagingDirectory();
      expect(success, isFalse);
    });

    test('shareContent passes text and title to native channel and returns success', () async {
      String? calledMethod;
      dynamic passedArguments;

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        calledMethod = methodCall.method;
        passedArguments = methodCall.arguments;
        return true;
      });

      final result = await service.shareContent(
        'Testing outbound text share',
        title: 'Share Title',
      );

      expect(result, isTrue);
      expect(calledMethod, equals('shareContent'));
      expect(passedArguments, equals({
        'text': 'Testing outbound text share',
        'title': 'Share Title',
      }));
    });

    test('shareContent returns false on PlatformException', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        throw PlatformException(code: 'ERROR', message: 'Failed');
      });

      final result = await service.shareContent('Test');
      expect(result, isFalse);
    });

    test('shareFile passes filePath and mimeType to native channel and returns success', () async {
      String? calledMethod;
      dynamic passedArguments;

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        calledMethod = methodCall.method;
        passedArguments = methodCall.arguments;
        return true;
      });

      final result = await service.shareFile(
        '/data/user/0/com.chrysalis.mobile/cache/syllabus.pdf',
        mimeType: 'application/pdf',
      );

      expect(result, isTrue);
      expect(calledMethod, equals('shareFile'));
      expect(passedArguments, equals({
        'filePath': '/data/user/0/com.chrysalis.mobile/cache/syllabus.pdf',
        'mimeType': 'application/pdf',
      }));
    });

    test('shareFile returns false on PlatformException', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        throw PlatformException(code: 'ERROR', message: 'Failed');
      });

      final result = await service.shareFile('/path/file.pdf');
      expect(result, isFalse);
    });

    test('showNativeToast passes message to native channel', () async {
      String? calledMethod;
      dynamic passedArguments;

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        calledMethod = methodCall.method;
        passedArguments = methodCall.arguments;
        return true;
      });

      final result = await service.showNativeToast('Saved to Chrysalis Inbox: test.txt');
      expect(result, isTrue);
      expect(calledMethod, equals('showToast'));
      expect(passedArguments, equals({'message': 'Saved to Chrysalis Inbox: test.txt'}));
    });

    test('finishNativeActivity invokes finishActivity on native channel', () async {
      bool finishCalled = false;

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'finishActivity') {
          finishCalled = true;
        }
        return null;
      });

      await service.finishNativeActivity();
      expect(finishCalled, isTrue);
    });

    test('isShareLaunch queries native channel and returns true/false', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'isShareLaunch') {
          return true;
        }
        return false;
      });

      final isShare = await service.isShareLaunch();
      expect(isShare, isTrue);
    });

    test('dispose safely closes stream and unregisters method call handler without error', () {
      expect(() => service.dispose(), returnsNormally);
      expect(() => service.dispose(), returnsNormally);
    });
  });
}
