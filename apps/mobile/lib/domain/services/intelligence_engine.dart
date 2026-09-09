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

/// Option B: Mobile-Native / Serverless Edge Intelligence Engine.
///
/// Executes on-device inference (e.g. Gemini Nano via AICore) or direct
/// cloud model APIs when operating without a dedicated home server.
class MobileNativeIntelligenceEngine implements IntelligenceEngine {
  final StreamController<OrchestratorEvent> _eventController =
      StreamController<OrchestratorEvent>.broadcast();
  final String modelName;

  MobileNativeIntelligenceEngine({
    this.modelName = 'gemini-nano',
  });

  /// Factory constructor for Option B Serverless Cloud endpoint defaulting to Gemini 3.8 Flash
  factory MobileNativeIntelligenceEngine.cloud({
    String modelName = 'gemini-3.8-flash',
  }) {
    return MobileNativeIntelligenceEngine(modelName: modelName);
  }

  @override
  EngineMode get mode => EngineMode.mobileNative;

  @override
  Stream<OrchestratorEvent> get eventStream => _eventController.stream;

  @override
  Future<bool> isAvailable() async {
    // Edge on-device model availability check stub
    return true;
  }

  @override
  Future<EngineStatus> getStatus() async {
    return EngineStatus(
      isAvailable: true,
      mode: EngineMode.mobileNative,
      engineName: 'MobileNative ($modelName)',
      version: '1.0.0',
      details: {
        'model': modelName,
        'accelerator': 'NNAPI / AICore',
        'edge_mode': true,
      },
      timestamp: DateTime.now(),
    );
  }

  @override
  Future<OrchestratorResponse> sendCommand(
    String command, {
    Map<String, dynamic>? parameters,
  }) async {
    final stopwatch = Stopwatch()..start();
    final cmd = command.split(' ').first.toLowerCase();

    // Emulate edge AI execution
    final output = _emulateEdgeResponse(cmd, parameters);
    stopwatch.stop();

    _eventController.add(OrchestratorEvent(
      type: OrchestratorEventType.response,
      content: output,
      timestamp: DateTime.now(),
    ));

    return OrchestratorResponse(
      success: true,
      command: command,
      output: output,
      executionTimeMs: stopwatch.elapsedMilliseconds,
      timestamp: TimezoneUtils.formatIsoWithOffset(DateTime.now()),
      emulated: true,
    );
  }

  @override
  Future<void> sendMessage(String text) async {
    _eventController.add(OrchestratorEvent(
      type: OrchestratorEventType.token,
      content: '🤖 [Edge Nano] Thinking...',
      timestamp: DateTime.now(),
    ));
  }

  @override
  Future<void> dispose() async {
    await _eventController.close();
  }

  String _emulateEdgeResponse(String cmd, Map<String, dynamic>? params) {
    switch (cmd) {
      case '/morning':
        final wake = params?['wake'] ?? '07:30';
        return '🌅 Edge morning calibration locked at $wake.';
      case '/evening':
        return '🌙 Edge evening review: 14-day roadmap milestones synced.';
      case '/doctor':
        return '🩺 Edge integrity check: 100% healthy.';
      case '/plan':
        return '📋 Edge focus plan calibrated: 75m ultradian sprints stacked.';
      default:
        return '🤖 Edge intelligence processed: "$cmd"';
    }
  }
}
