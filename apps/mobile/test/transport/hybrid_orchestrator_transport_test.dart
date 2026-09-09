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

    test('sendCommand buffers to System/Inbox/events.json in vault when in mailbox mode', () async {
      final events = <OrchestratorEvent>[];
      final sub = transport.incomingEvents.listen(events.add);

      await transport.sendCommand('/morning', parameters: {'wake': '07:30', 'energy': 4});

      await Future.delayed(const Duration(milliseconds: 10));

      // 1. Verify notification event was emitted to client
      expect(events.isNotEmpty, isTrue);
      expect(events.first.content, contains('Intent buffered to System/Inbox/events.json'));

      // 2. Verify file exists in vault
      expect(await storage.fileExists('System/Inbox/events.json'), isTrue);

      final content = await storage.readTextFile('System/Inbox/events.json');
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

    test('sendMessage buffers conversational text to System/Inbox/events.json', () async {
      await transport.sendMessage('Hello Antigravity, schedule focus sprints for today.');

      final content = await storage.readTextFile('System/Inbox/events.json');
      final decoded = jsonDecode(content);

      final eventList = decoded['events'] as List;
      final msgEvent = eventList.first as Map<String, dynamic>;

      expect(msgEvent['type'], equals('message'));
      expect(msgEvent['text'], equals('Hello Antigravity, schedule focus sprints for today.'));
      expect(msgEvent['status'], equals('pending'));
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
