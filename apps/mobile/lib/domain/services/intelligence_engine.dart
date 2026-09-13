import 'dart:async';
import '../../core/constants/timezones.dart';
import '../../transport/orchestrator_transport.dart';

/// Operational mode of the Intelligence Engine.
enum EngineMode {
  /// Option A: Dedicated Home Hub Gateway (Surface Pro X / Golem on port 8765)
  homeGateway,

  /// Option B: Mobile-Native / Serverless Edge Mode (Gemini Nano / direct cloud API)
  mobileNative,
}

/// Status snapshot of the active Intelligence Engine.
class EngineStatus {
  final bool isAvailable;
  final EngineMode mode;
  final String engineName;
  final String version;
  final Map<String, dynamic> details;
  final DateTime timestamp;

  const EngineStatus({
    required this.isAvailable,
    required this.mode,
    required this.engineName,
    this.version = '1.0.0',
    this.details = const {},
    required this.timestamp,
  });

  @override
  String toString() =>
      'EngineStatus(engine: $engineName, mode: ${mode.name}, available: $isAvailable)';
}

/// Structured response from orchestrator command execution.
class OrchestratorResponse {
  final bool success;
  final String command;
  final String output;
  final String? error;
  final String? conversationId;
  final int executionTimeMs;
  final String timestamp;
  final bool emulated;

  const OrchestratorResponse({
    required this.success,
    required this.command,
    required this.output,
    this.error,
    this.conversationId,
    required this.executionTimeMs,
    required this.timestamp,
    this.emulated = false,
  });

  factory OrchestratorResponse.fromJson(Map<String, dynamic> json) {
    return OrchestratorResponse(
      success: json['success'] as bool? ?? false,
      command: json['command'] as String? ?? '',
      output: json['output'] as String? ?? '',
      error: json['error'] as String?,
      conversationId: json['conversation_id'] as String?,
      executionTimeMs: (json['execution_time_ms'] as num?)?.toInt() ?? 0,
      timestamp: json['timestamp'] as String? ??
          TimezoneUtils.formatIsoWithOffset(DateTime.now()),
      emulated: json['emulated'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'success': success,
        'command': command,
        'output': output,
        if (error != null) 'error': error,
        if (conversationId != null) 'conversation_id': conversationId,
        'execution_time_ms': executionTimeMs,
        'timestamp': timestamp,
        'emulated': emulated,
      };
}

/// Master contract for the Chrysalis Modular Intelligence Engine.
///
/// Decouples mobile presentation from backend agent orchestration,
/// supporting both Option A (Home Gateway) and Option B (Mobile-Native).
abstract class IntelligenceEngine {
  /// Active operational mode of the intelligence engine.
  EngineMode get mode;

  /// Stream emitting real-time tokens, status updates, and responses.
  Stream<OrchestratorEvent> get eventStream;

  /// Verifies whether the engine backend is currently available.
  Future<bool> isAvailable();

  /// Returns telemetry and operational status snapshot.
  Future<EngineStatus> getStatus();

  /// Dispatches a Chrysalis slash command (/morning, /evening, /plan, /task, /doctor, /pause).
  Future<OrchestratorResponse> sendCommand(
    String command, {
    Map<String, dynamic>? parameters,
  });

  /// Sends a conversational natural language turn.
  Future<void> sendMessage(String text);

  /// Releases resources, sockets, or listeners.
  Future<void> dispose();
}

/// Reserved direct inference adapter. No cloud or on-device execution is
/// implemented; callers receive an explicit unavailable result.
class MobileNativeIntelligenceEngine implements IntelligenceEngine {
  final _eventController = StreamController<OrchestratorEvent>.broadcast();
  final String modelName;

  MobileNativeIntelligenceEngine({this.modelName = 'unconfigured'});

  factory MobileNativeIntelligenceEngine.cloud({String modelName = 'unconfigured'}) =>
      MobileNativeIntelligenceEngine(modelName: modelName);

  @override
  EngineMode get mode => EngineMode.mobileNative;
  @override
  Stream<OrchestratorEvent> get eventStream => _eventController.stream;
  @override
  Future<bool> isAvailable() async => false;
  @override
  Future<EngineStatus> getStatus() async => EngineStatus(
    isAvailable: false, mode: mode, engineName: 'Direct AI (not configured)',
    details: {'implemented': false}, timestamp: DateTime.now(),
  );
  @override
  Future<OrchestratorResponse> sendCommand(String command, {Map<String, dynamic>? parameters}) async {
    const error = 'Direct AI execution is not implemented. No action was performed.';
    _eventController.add(OrchestratorEvent(
      type: OrchestratorEventType.error, content: error, timestamp: DateTime.now(),
    ));
    return OrchestratorResponse(success: false, command: command, output: '',
      error: error, executionTimeMs: 0,
      timestamp: TimezoneUtils.formatIsoWithOffset(DateTime.now()));
  }
  @override
  Future<void> sendMessage(String text) async { await sendCommand(text); }
  @override
  Future<void> dispose() async { await _eventController.close(); }
}
