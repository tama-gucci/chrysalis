import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import '../core/constants/timezones.dart';
import '../domain/services/intelligence_engine.dart';
import 'orchestrator_transport.dart';

/// Client implementing Model 2: Ambient Chrysalis Gateway.
///
/// Connects to the home server daemon running on `surface-pro-x` (Golem) via
/// Cloudflare Tunnel or local LAN WebSocket on dedicated port 8765.
/// Implements [IntelligenceEngine] to decouple mobile presentation from the backend.
class AmbientGatewayClient implements IntelligenceEngine {
  final String? gatewayUrl;
  final String? authToken;
  WebSocketChannel? _channel;
  StreamSubscription? _channelSubscription;
  final StreamController<OrchestratorEvent> _eventController =
      StreamController<OrchestratorEvent>.broadcast();
  bool _isConnected = false;

  AmbientGatewayClient({
    this.gatewayUrl,
    this.authToken,
  });

  @override
  EngineMode get mode => EngineMode.homeGateway;

  bool get isConnected => _isConnected;

  /// Stream of real-time orchestrator events.
  Stream<OrchestratorEvent> get events => _eventController.stream;

  @override
  Stream<OrchestratorEvent> get eventStream => _eventController.stream;

  String? _getHttpBaseUrl() {
    if (gatewayUrl == null || gatewayUrl!.isEmpty) return null;
    var url = gatewayUrl!;
    if (url.startsWith('ws://')) {
      url = 'http://${url.substring(5)}';
    } else if (url.startsWith('wss://')) {
      url = 'https://${url.substring(6)}';
    }
    final wsIdx = url.indexOf('/api/orchestrator/ws');
    if (wsIdx != -1) {
      url = url.substring(0, wsIdx);
    }
    if (url.endsWith('/')) {
      url = url.substring(0, url.length - 1);
    }
    return url;
  }

  @override
  Future<bool> isAvailable() async {
    if (_isConnected) return true;
    final httpBase = _getHttpBaseUrl();
    if (httpBase == null) return false;
    try {
      final res = await http.get(Uri.parse('$httpBase/health')).timeout(const Duration(seconds: 2));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<EngineStatus> getStatus() async {
    final available = await isAvailable();
    return EngineStatus(
      isAvailable: available,
      mode: EngineMode.homeGateway,
      engineName: 'Ambient Gateway',
      version: '1.0.0',
      details: {
        'url': gatewayUrl ?? 'not configured',
        'connected': _isConnected,
        'port': 8765,
      },
      timestamp: DateTime.now(),
    );
  }

  /// Attempts connection to gateway WSS.
  Future<bool> connect() async {
    if (gatewayUrl == null || gatewayUrl!.isEmpty) {
      _isConnected = false;
      return false;
    }

    try {
      final base = Uri.parse(_getHttpBaseUrl()!);
      final uri = base.replace(
        scheme: base.scheme == 'https' ? 'wss' : 'ws',
        path: '${base.path}/api/orchestrator/ws',
        queryParameters: authToken == null ? null : {'token': authToken!},
      );
      _channel = WebSocketChannel.connect(uri);
      await _channel!.ready.timeout(const Duration(seconds: 3));

      _channelSubscription = _channel!.stream.listen(
        (data) {
          _handleIncoming(data);
        },
        onError: (err) {
          _isConnected = false;
        },
        onDone: () {
          _isConnected = false;
        },
      );

      _isConnected = true;
      return true;
    } catch (_) {
      _isConnected = false;
      return false;
    }
  }

  /// Commands use one request path. Never replay a timed-out mutation over a
  /// second transport: the backend may already have performed it.
  @override
  Future<OrchestratorResponse> sendCommand(String command, {Map<String, dynamic>? parameters}) async {
    final base = _getHttpBaseUrl();
    if (base == null) throw StateError('Gateway is not configured');
    final stopwatch = Stopwatch()..start();
    OrchestratorResponse result;
    try {
      final response = await http.post(Uri.parse('$base/api/orchestrator/command'),
        headers: {
          'Content-Type': 'application/json',
          if (authToken != null) 'Authorization': 'Bearer $authToken',
        },
        body: jsonEncode({'command': command, 'parameters': parameters ?? {}}),
      ).timeout(const Duration(seconds: 65));
      if (response.statusCode != 200) {
        throw StateError('Gateway returned HTTP ${response.statusCode}');
      }
      result = OrchestratorResponse.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    } catch (_) {
      result = OrchestratorResponse(success: false, command: command, output: '',
        error: 'Could not confirm command completion. Check the vault before retrying.',
        executionTimeMs: stopwatch.elapsedMilliseconds,
        timestamp: TimezoneUtils.formatIsoWithOffset(DateTime.now()));
    }
    _eventController.add(OrchestratorEvent(
      type: result.success ? OrchestratorEventType.response : OrchestratorEventType.error,
      content: result.success ? result.output : (result.error ?? 'Command failed'),
      metadata: result.toJson(), timestamp: DateTime.now(),
    ));
    return result;
  }

  @override
  Future<void> sendMessage(String text) async { await sendCommand(text); }

  void _handleIncoming(dynamic data) {
    try {
      final decoded = jsonDecode(data.toString());
      if (decoded is Map) {
        final typeStr = decoded['type']?.toString().toLowerCase() ?? 'response';

        // Extract text content from content, message, or data output
        String content = decoded['content']?.toString() ?? '';
        if (content.isEmpty) {
          if (decoded['message'] != null) {
            content = decoded['message'].toString();
          } else if (decoded['data'] is Map && (decoded['data'] as Map)['output'] != null) {
            content = (decoded['data'] as Map)['output'].toString();
          } else if (decoded['data'] != null && decoded['data'] is! Map) {
            content = decoded['data'].toString();
          }
        }

        final Map<String, dynamic>? metadata = decoded['metadata'] is Map
            ? Map<String, dynamic>.from(decoded['metadata'] as Map)
            : (decoded['data'] is Map ? Map<String, dynamic>.from(decoded['data'] as Map) : null);

        final OrchestratorEventType type;
        switch (typeStr) {
          case 'token':
          case 'chunk':
            type = OrchestratorEventType.token;
            break;
          case 'status':
            type = OrchestratorEventType.statusUpdate;
            break;
          case 'error':
            type = OrchestratorEventType.error;
            break;
          case 'complete':
          case 'response':
          default:
            type = OrchestratorEventType.response;
        }

        _eventController.add(
          OrchestratorEvent(
            type: type,
            content: content,
            metadata: metadata,
            timestamp: DateTime.now(),
          ),
        );
      }
    } catch (_) {
      _eventController.add(
        OrchestratorEvent(
          type: OrchestratorEventType.response,
          content: data.toString(),
          timestamp: DateTime.now(),
        ),
      );
    }
  }

  void disconnect() {
    _isConnected = false;
    _channelSubscription?.cancel();
    _channelSubscription = null;
    try {
      _channel?.sink.close();
    } catch (_) {}
    _channel = null;
  }

  @override
  Future<void> dispose() async {
    disconnect();
    if (!_eventController.isClosed) {
      _eventController.close();
    }
  }
}
