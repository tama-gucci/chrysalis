import 'dart:async';
import 'dart:convert';
import 'package:uuid/uuid.dart';
import '../../core/constants/timezones.dart';
import '../data/storage/vault_storage_provider.dart';

/// Client implementing Model 1: Substrate-Mediated Decoupled Mailbox.
///
/// When mobile is offline or unable to connect to the Ambient Gateway,
/// user intents and slash commands are safely serialized to
/// `System/Inbox/events.json` in the Chrysalis vault substrate.
/// The at-home Antigravity orchestrator processes these upon next sync.
class SubstrateMailboxClient {
  static const String defaultMailboxPath = 'chrysalis/System/Inbox/events.json';
  static const String legacyMailboxPath = 'System/Inbox/events.json';
  final String mailboxPath;
  final VaultStorageProvider storageProvider;
  final Uuid _uuid = const Uuid();
  Future<void>? _writeLock;

  SubstrateMailboxClient({
    required this.storageProvider,
    this.mailboxPath = defaultMailboxPath,
  });

  /// Appends a command intent to `System/Inbox/events.json`.
  Future<String> appendCommand(String command, {Map<String, dynamic>? parameters}) async {
    final eventId = 'cmd-${DateTime.now().millisecondsSinceEpoch}-${_uuid.v4().substring(0, 8)}';
    final payload = {
      'id': eventId,
      'timestamp': TimezoneUtils.formatIsoWithOffset(DateTime.now()),
      'type': 'command',
      'command': command,
      'parameters': parameters ?? {},
      'status': 'pending',
    };
    await _writeEvent(payload);
    return eventId;
  }

  /// Appends a chat message intent to `System/Inbox/events.json`.
  Future<String> appendMessage(String text) async {
    final eventId = 'msg-${DateTime.now().millisecondsSinceEpoch}-${_uuid.v4().substring(0, 8)}';
    final payload = {
      'id': eventId,
      'timestamp': TimezoneUtils.formatIsoWithOffset(DateTime.now()),
      'type': 'message',
      'text': text,
      'status': 'pending',
    };
    await _writeEvent(payload);
    return eventId;
  }

  /// Reads current mailbox events.
  Future<List<Map<String, dynamic>>> readEvents() async {
    String targetPath = mailboxPath;
    if (!await storageProvider.fileExists(targetPath)) {
      if (await storageProvider.fileExists(legacyMailboxPath)) {
        targetPath = legacyMailboxPath;
      } else {
        return [];
      }
    }
    try {
      final raw = await storageProvider.readTextFile(targetPath);
      final decoded = jsonDecode(raw);
      if (decoded is Map && decoded['events'] is List) {
        return List<Map<String, dynamic>>.from(decoded['events']);
      }
    } catch (_) {}
    return [];
  }

  Future<void> _writeEvent(Map<String, dynamic> newEvent) {
    final prev = _writeLock ?? Future.value();
    final completer = Completer<void>();
    _writeLock = completer.future;

    return prev.then((_) async {
      try {
        final events = await readEvents();
        events.add(newEvent);

        final payload = {
          'version': '1.0.0',
          'last_updated': TimezoneUtils.formatIsoWithOffset(DateTime.now()),
          'events': events,
        };

        final jsonStr = const JsonEncoder.withIndent('  ').convert(payload);
        await storageProvider.writeTextFile(mailboxPath, jsonStr);
      } finally {
        completer.complete();
        if (_writeLock == completer.future) {
          _writeLock = null;
        }
      }
    });
  }
}
