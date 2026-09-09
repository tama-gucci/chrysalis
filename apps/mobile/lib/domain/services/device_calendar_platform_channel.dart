import 'package:flutter/services.dart';
import 'device_calendar_service.dart';

/// Concrete [DeviceCalendarDataSource] implementation using Flutter's [MethodChannel]
/// to interact with native Android (CalendarContract) and iOS (EventKit) APIs.
class DeviceCalendarPlatformChannelDataSource implements DeviceCalendarDataSource {
  final MethodChannel _channel;

  DeviceCalendarPlatformChannelDataSource({MethodChannel? channel})
      : _channel = channel ?? const MethodChannel('org.chrysalis.mobile/calendar');

  @override
  String get providerName => 'Native OS Calendar Provider';

  @override
  Future<bool> isAvailable() async {
    try {
      final available = await _channel.invokeMethod<bool>('isAvailable');
      return available ?? false;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> hasPermissions() async {
    try {
      final granted = await _channel.invokeMethod<bool>('hasPermissions');
      return granted ?? false;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> requestPermissions() async {
    try {
      final granted = await _channel.invokeMethod<bool>('requestPermissions');
      return granted ?? false;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<List<DeviceCalendarInfo>> getCalendars() async {
    try {
      final response = await _channel.invokeListMethod<Map<dynamic, dynamic>>('getCalendars');
      if (response == null) return [];

      return response.map((map) {
        return DeviceCalendarInfo(
          id: map['id']?.toString() ?? '',
          name: map['name']?.toString() ?? 'Calendar',
          accountName: map['accountName']?.toString() ?? '',
          isPrimary: map['isPrimary'] == true,
          isReadOnly: map['isReadOnly'] == true,
          color: map['color'] is int ? map['color'] as int : null,
        );
      }).toList();
    } catch (_) {
      return [];
    }
  }

  @override
  Future<String?> createOrUpdateEvent({
    required String calendarId,
    required DeviceCalendarEvent event,
  }) async {
    try {
      final eventId = await _channel.invokeMethod<String>('createOrUpdateEvent', {
        'calendarId': calendarId,
        'eventId': event.id,
        'title': event.title,
        'startEpochMs': event.start.millisecondsSinceEpoch,
        'endEpochMs': event.end.millisecondsSinceEpoch,
        'description': event.description,
        'location': event.location,
        'allDay': event.allDay,
      });
      return eventId;
    } catch (_) {
      return null;
    }
  }

  @override
  Future<bool> deleteEvent({
    required String calendarId,
    required String eventId,
  }) async {
    try {
      final success = await _channel.invokeMethod<bool>('deleteEvent', {
        'calendarId': calendarId,
        'eventId': eventId,
      });
      return success ?? false;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<List<DeviceCalendarEvent>> getEventsInRange({
    required String calendarId,
    required DateTime start,
    required DateTime end,
  }) async {
    try {
      final response = await _channel.invokeListMethod<Map<dynamic, dynamic>>('getEventsInRange', {
        'calendarId': calendarId,
        'startEpochMs': start.millisecondsSinceEpoch,
        'endEpochMs': end.millisecondsSinceEpoch,
      });
      if (response == null) return [];

      return response.map((map) {
        return DeviceCalendarEvent(
          id: map['id']?.toString(),
          calendarId: calendarId,
          title: map['title']?.toString() ?? 'Untitled',
          start: DateTime.fromMillisecondsSinceEpoch(map['startEpochMs'] as int),
          end: DateTime.fromMillisecondsSinceEpoch(map['endEpochMs'] as int),
          description: map['description']?.toString(),
          location: map['location']?.toString(),
          allDay: map['allDay'] == true,
        );
      }).toList();
    } catch (_) {
      return [];
    }
  }
}
