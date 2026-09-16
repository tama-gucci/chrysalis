import 'dart:async';

/// Connection mode of the hybrid orchestrator transport.
enum TransportConnectionState {
  disconnected,
  connecting,
  /// Active sub-second streaming connection to Ambient Gateway (WSS/REST)
  connectedGateway,
  /// Offline fallback buffering intents into the configured vault mailbox.
  bufferingMailbox,
}

enum OrchestratorEventType {
  token,
  response,
  statusUpdate,
  error,
}

class OrchestratorEvent {
  final OrchestratorEventType type;
  final String content;
  final Map<String, dynamic>? metadata;
  final DateTime timestamp;

  const OrchestratorEvent({
    required this.type,
    required this.content,
    this.metadata,
    required this.timestamp,
  });
}

/// Abstract contract for orchestrator client communication.
abstract class OrchestratorTransport {
  /// Stream emitting active connection state transitions.
  Stream<TransportConnectionState> get connectionState;

  /// Current connection state snapshot.
  TransportConnectionState get currentState;

  /// Stream of streamed responses and updates from the orchestrator.
  Stream<OrchestratorEvent> get incomingEvents;

  /// Initializes connectivity (attempts Gateway, falls back to Substrate Mailbox).
  Future<void> initialize();

  /// Sends a slash command (e.g. "/morning", "/plan", "/task", "/pause")
  Future<void> sendCommand(String command, {Map<String, dynamic>? parameters});

  /// Sends an interactive conversational message to Antigravity
  Future<void> sendMessage(String text);

  /// Disposes active sockets and subscriptions
  Future<void> dispose();
}
