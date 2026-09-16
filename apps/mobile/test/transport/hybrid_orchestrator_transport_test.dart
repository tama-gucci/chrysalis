import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/data/storage/in_memory_vault_storage_provider.dart';
import 'package:chrysalis_mobile/transport/ambient_gateway_client.dart';
import 'package:chrysalis_mobile/transport/hybrid_orchestrator_transport.dart';
import 'package:chrysalis_mobile/transport/orchestrator_transport.dart';
import 'package:chrysalis_mobile/transport/substrate_mailbox_client.dart';

void main() {
  group('Hybrid Orchestrator Transport', () {
    late InMemoryVaultStorageProvider storage;
    late AmbientGatewayClient gatewayClient;
    late HybridOrchestratorTransport transport;

    setUp(() async {
      storage = InMemoryVaultStorageProvider();
      await storage.initialize();

      // Gateway client without URL defaults to offline
      gatewayClient = AmbientGatewayClient();

      transport = HybridOrchestratorTransport(
        gatewayClient: gatewayClient,
        storageProvider: storage,
      );
      await transport.initialize();
    });

    tearDown(() async {
      await transport.dispose();
      await storage.dispose();
    });

    test('initializes and defaults to bufferingMailbox when gateway is unavailable', () {
      expect(transport.currentState, equals(TransportConnectionState.bufferingMailbox));
    });

    test('sendCommand buffers to chrysalis/System/Inbox/events.json in vault when in mailbox mode', () async {
      final events = <OrchestratorEvent>[];
      final sub = transport.incomingEvents.listen(events.add);

      await transport.sendCommand('/morning', parameters: {'wake': '07:30', 'energy': 4});

      await Future.delayed(const Duration(milliseconds: 10));

      // 1. Verify notification event was emitted to client
      expect(events.isNotEmpty, isTrue);
      expect(events.first.content, contains('Intent buffered to chrysalis/System/Inbox/events.json'));

      // 2. Verify file exists in vault
      expect(await storage.fileExists('chrysalis/System/Inbox/events.json'), isTrue);

      final content = await storage.readTextFile('chrysalis/System/Inbox/events.json');
      final decoded = jsonDecode(content);

      expect(decoded['version'], equals('1.0.0'));
      expect(decoded['events'], isA<List>());
      final eventList = decoded['events'] as List;
      expect(eventList.length, equals(1));

      final firstEvent = eventList.first as Map<String, dynamic>;
      expect(firstEvent['command'], equals('/morning'));
      expect(firstEvent['type'], equals('command'));
      expect(firstEvent['status'], equals('pending'));
      expect(firstEvent['parameters']['energy'], equals(4));
      expect(firstEvent['timestamp'], contains('-05:00'));

      await sub.cancel();
    });

    test('sendMessage buffers conversational text to chrysalis/System/Inbox/events.json', () async {
      await transport.sendMessage('Hello Antigravity, schedule focus sprints for today.');

      final content = await storage.readTextFile('chrysalis/System/Inbox/events.json');
      final decoded = jsonDecode(content);

      final eventList = decoded['events'] as List;
      final msgEvent = eventList.first as Map<String, dynamic>;

      expect(msgEvent['type'], equals('message'));
      expect(msgEvent['text'], equals('Hello Antigravity, schedule focus sprints for today.'));
      expect(msgEvent['status'], equals('pending'));
    });

    for (final path in [
      SubstrateMailboxClient.defaultMailboxPath,
      'Custom/Inbox/events.json',
      SubstrateMailboxClient.legacyMailboxPath,
    ]) {
      test('command and message status identify configured destination $path', () async {
        await transport.dispose();
        transport = HybridOrchestratorTransport(
          gatewayClient: AmbientGatewayClient(),
          storageProvider: storage,
          mailboxClient: SubstrateMailboxClient(
            storageProvider: storage,
            mailboxPath: path,
          ),
        );
        await transport.initialize();
        final commandNotice = transport.incomingEvents.first;
        await transport.sendCommand('/doctor');
        final command = await commandNotice;
        expect(command.content, contains('Intent buffered to $path'));
        expect(command.content, contains('not an executed action'));
        final messageNotice = transport.incomingEvents.first;
        await transport.sendMessage('Synthetic offline message');
        final message = await messageNotice;
        expect(message.content, contains('Message buffered to $path'));
        expect(message.content, contains('not an executed action'));
        final saved = jsonDecode(await storage.readTextFile(path))['events'] as List;
        expect(saved.map((e) => e['id']), [command.metadata!['eventId'], message.metadata!['eventId']]);
        expect(saved.map((e) => e['status']), ['pending', 'pending']);
        for (final other in [SubstrateMailboxClient.defaultMailboxPath,
                            SubstrateMailboxClient.legacyMailboxPath]) {
          if (other != path) expect(await storage.fileExists(other), isFalse);
        }
      });
    }

    test('legacy events survive migration and subsequent default appends', () async {
      const legacy = '{"version":"1.0.0","events":[{"id":"legacy-intent","type":"command","command":"/plan","status":"pending","parameters":{"stage":true}}]}';
      await storage.writeTextFile(SubstrateMailboxClient.legacyMailboxPath, legacy);
      final mailbox = SubstrateMailboxClient(storageProvider: storage);
      expect((await mailbox.readEvents()).single['id'], 'legacy-intent');
      final commandId = await mailbox.appendCommand('/doctor');
      final messageId = await mailbox.appendMessage('Synthetic follow-up');
      final saved = jsonDecode(await storage.readTextFile(SubstrateMailboxClient.defaultMailboxPath))['events'] as List;
      expect(saved.map((e) => e['id']), ['legacy-intent', commandId, messageId]);
      expect(saved.first, (jsonDecode(legacy)['events'] as List).single);
      expect(await storage.readTextFile(SubstrateMailboxClient.legacyMailboxPath), legacy);
    });

    test('existing configured mailbox takes precedence over legacy contents', () async {
      await storage.writeTextFile(SubstrateMailboxClient.legacyMailboxPath,
          '{"events":[{"id":"legacy-only"}]}');
      final mailbox = SubstrateMailboxClient(storageProvider: storage);
      await storage.writeTextFile(mailbox.mailboxPath, '{"events":[{"id":"current-only"}]}');
      final id = await mailbox.appendCommand('/doctor');
      expect((await mailbox.readEvents()).map((e) => e['id']), ['current-only', id]);
    });

    test('SubstrateMailboxClient appends multiple events sequentially', () async {
      final mailbox = SubstrateMailboxClient(storageProvider: storage);

      await mailbox.appendCommand('/plan', parameters: {'stage': true});
      await mailbox.appendCommand('/doctor');

      final events = await mailbox.readEvents();
      expect(events.length, equals(2));
      expect(events[0]['command'], equals('/plan'));
      expect(events[1]['command'], equals('/doctor'));
    });

    test('SubstrateMailboxClient handles concurrent burst writes safely without race overwrites', () async {
      final mailbox = SubstrateMailboxClient(storageProvider: storage);

      // Launch multiple appends concurrently without awaiting between them
      await Future.wait([
        mailbox.appendCommand('/doctor'),
        mailbox.appendMessage('Concurrent message 1'),
        mailbox.appendCommand('/pause', parameters: {'mode': 'rest'}),
        mailbox.appendMessage('Concurrent message 2'),
      ]);

      final events = await mailbox.readEvents();
      expect(events.length, equals(4));
      final types = events.map((e) => e['type']).toList();
      expect(types.where((t) => t == 'command').length, equals(2));
      expect(types.where((t) => t == 'message').length, equals(2));
    });
  });
}
