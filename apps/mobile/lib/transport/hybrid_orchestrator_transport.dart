import 'dart:async';
import '../data/storage/vault_storage_provider.dart';
import 'ambient_gateway_client.dart';
import 'orchestrator_transport.dart';
import 'substrate_mailbox_client.dart';

/// Unified Hybrid Engine for Mobile Client Communication.
///
/// Implements Model 3:
/// - Online: Routes to Ambient Gateway WSS/REST for sub-second streaming.
/// - Offline: Seamlessly falls back to Substrate Mailbox, buffering intents
///   into `System/Inbox/events.json` on the vault filesystem.
class HybridOrchestratorTransport implements OrchestratorTransport {
  final AmbientGatewayClient gatewayClient;
  final SubstrateMailboxClient mailboxClient;
  final VaultStorageProvider storageProvider;

  final StreamController<TransportConnectionState> _stateController =
      StreamController<TransportConnectionState>.broadcast();
  final StreamController<OrchestratorEvent> _eventController =
      StreamController<OrchestratorEvent>.broadcast();

  TransportConnectionState _currentState = TransportConnectionState.disconnected;
  StreamSubscription? _gatewayEventSub;

  HybridOrchestratorTransport({
    required this.gatewayClient,
    required this.storageProvider,
    SubstrateMailboxClient? mailboxClient,
  }) : mailboxClient = mailboxClient ?? SubstrateMailboxClient(storageProvider: storageProvider);

  @override
  TransportConnectionState get currentState => _currentState;

  @override
  Stream<TransportConnectionState> get connectionState => _stateController.stream;

  @override
  Stream<OrchestratorEvent> get incomingEvents => _eventController.stream;

  @override
  Future<void> initialize() async {
    _setState(TransportConnectionState.connecting);

    // Forward gateway events to main event stream
    _gatewayEventSub = gatewayClient.events.listen((event) {
      if (!_eventController.isClosed) {
        _eventController.add(event);
      }
    });

    // Attempt Ambient Gateway connection
    final connected = await gatewayClient.connect();
    if (connected) {
      _setState(TransportConnectionState.connectedGateway);
    } else {
      // Smooth fallback to Substrate Mailbox
      _setState(TransportConnectionState.bufferingMailbox);
    }
  }

  void _setState(TransportConnectionState newState) {
    _currentState = newState;
    if (!_stateController.isClosed) {
      _stateController.add(newState);
    }
  }

  @override
  Future<void> sendCommand(String command, {Map<String, dynamic>? parameters}) async {
    if (_currentState == TransportConnectionState.connectedGateway) {
      try {
        await gatewayClient.sendCommand(command, parameters: parameters);
        return;
      } catch (_) {
        // If gateway fails in-flight, fall back to mailbox
        _setState(TransportConnectionState.bufferingMailbox);
      }
    }

    // Offline / Mailbox mode: buffer to System/Inbox/events.json
    final eventId = await mailboxClient.appendCommand(command, parameters: parameters);
    _eventController.add(
      OrchestratorEvent(
        type: OrchestratorEventType.statusUpdate,
        content: 'Intent buffered to System/Inbox/events.json ($eventId). '
            'Home orchestrator will execute upon next sync.',
        metadata: {'eventId': eventId, 'mode': 'mailbox'},
        timestamp: DateTime.now(),
      ),
    );
  }

  @override
  Future<void> sendMessage(String text) async {
    if (_currentState == TransportConnectionState.connectedGateway) {
      try {
        await gatewayClient.sendMessage(text);
        return;
      } catch (_) {
        _setState(TransportConnectionState.bufferingMailbox);
      }
    }

    // Offline / Mailbox mode: buffer to System/Inbox/events.json
    final eventId = await mailboxClient.appendMessage(text);
    _eventController.add(
      OrchestratorEvent(
        type: OrchestratorEventType.statusUpdate,
        content: 'Message buffered to System/Inbox/events.json ($eventId).',
        metadata: {'eventId': eventId, 'mode': 'mailbox'},
        timestamp: DateTime.now(),
      ),
    );
  }

  /// Manually force or simulate a connection state switch.
  void setMode(TransportConnectionState mode) {
    _setState(mode);
  }

  @override
  Future<void> dispose() async {
    _gatewayEventSub?.cancel();
    _gatewayEventSub = null;
    gatewayClient.dispose();
    if (!_stateController.isClosed) {
      _stateController.close();
    }
    if (!_eventController.isClosed) {
      _eventController.close();
    }
  }
}
