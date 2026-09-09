import 'dart:async';

/// Represents a calendar account available on the host device (e.g., Google Calendar, Samsung Calendar).
class DeviceCalendarInfo {
  final String id;
  final String name;
  final String accountName;
  final bool isPrimary;
  final bool isReadOnly;
  final int? color;

  const DeviceCalendarInfo({
    required this.id,
    required this.name,
    required this.accountName,
    this.isPrimary = false,
    this.isReadOnly = false,
    this.color,
  });

  @override
  String toString() => 'DeviceCalendarInfo(id: $id, name: $name, account: $accountName, primary: $isPrimary)';
}

/// Represents an event entry stored in the device's native calendar database.
class DeviceCalendarEvent {
  final String? id;
  final String calendarId;
  final String title;
  final DateTime start;
  final DateTime end;
  final String? description;
  final String? location;
  final bool allDay;

  const DeviceCalendarEvent({
    this.id,
    required this.calendarId,
    required this.title,
    required this.start,
    required this.end,
    this.description,
    this.location,
    this.allDay = false,
  });

  DeviceCalendarEvent copyWith({
    String? id,
    String? calendarId,
    String? title,
    DateTime? start,
    DateTime? end,
    String? description,
    String? location,
    bool? allDay,
  }) {
    return DeviceCalendarEvent(
      id: id ?? this.id,
      calendarId: calendarId ?? this.calendarId,
      title: title ?? this.title,
      start: start ?? this.start,
      end: end ?? this.end,
      description: description ?? this.description,
      location: location ?? this.location,
      allDay: allDay ?? this.allDay,
    );
  }

  @override
  String toString() => 'DeviceCalendarEvent(id: $id, title: $title, start: $start, end: $end)';
}

/// Contract for native mobile and wearable calendar synchronization.
///
/// Implementations connect directly to the host operating system's calendar provider
/// (Android CalendarContract or iOS EventKit), allowing the device OS to handle
/// background cloud synchronization and Wear OS watch mirroring with zero API keys.
abstract class DeviceCalendarDataSource {
  String get providerName;

  /// Checks whether calendar provider services are supported on this device.
  Future<bool> isAvailable();

  /// Checks whether the user has granted read/write calendar permissions.
  Future<bool> hasPermissions();

  /// Prompts the native OS calendar permission dialog.
  Future<bool> requestPermissions();

  /// Retrieves all calendars synchronized on this device.
  Future<List<DeviceCalendarInfo>> getCalendars();

  /// Creates a new calendar event or updates an existing one if [event.id] is set.
  /// Returns the assigned or existing native event ID.
  Future<String?> createOrUpdateEvent({
    required String calendarId,
    required DeviceCalendarEvent event,
  });

  /// Deletes an event from the specified device calendar.
  Future<bool> deleteEvent({
    required String calendarId,
    required String eventId,
  });

  /// Retrieves events within the specified time range for collision checks.
  Future<List<DeviceCalendarEvent>> getEventsInRange({
    required String calendarId,
    required DateTime start,
    required DateTime end,
  });
}

/// In-memory simulated calendar data source for headless testing, CI/CD, and desktop environments.
class MockDeviceCalendarDataSource implements DeviceCalendarDataSource {
  bool permissionGranted;
  bool shouldGrantOnRequest;
  final Map<String, DeviceCalendarInfo> _calendars = {};
  final Map<String, Map<String, DeviceCalendarEvent>> _eventsByCalendar = {};
  int _nextId = 1000;

  MockDeviceCalendarDataSource({
    this.permissionGranted = true,
    this.shouldGrantOnRequest = true,
    List<DeviceCalendarInfo>? initialCalendars,
  }) {
    if (initialCalendars != null && initialCalendars.isNotEmpty) {
      for (final cal in initialCalendars) {
        _calendars[cal.id] = cal;
        _eventsByCalendar[cal.id] = {};
      }
    } else {
      // Default primary Google Calendar
      const defaultCal = DeviceCalendarInfo(
        id: 'primary-google-cal',
        name: 'Personal Focus',
        accountName: 'user@example.com',
        isPrimary: true,
        isReadOnly: false,
      );
      _calendars[defaultCal.id] = defaultCal;
      _eventsByCalendar[defaultCal.id] = {};
    }
  }

  @override
  String get providerName => 'Mock Device Calendar (Simulated)';

  @override
  Future<bool> isAvailable() async => true;

  @override
  Future<bool> hasPermissions() async => permissionGranted;

  @override
  Future<bool> requestPermissions() async {
    if (shouldGrantOnRequest) {
      permissionGranted = true;
      return true;
    }
    permissionGranted = false;
    return false;
  }

  @override
  Future<List<DeviceCalendarInfo>> getCalendars() async {
    if (!permissionGranted) return [];
    return _calendars.values.toList();
  }

  @override
  Future<String?> createOrUpdateEvent({
    required String calendarId,
    required DeviceCalendarEvent event,
  }) async {
    if (!permissionGranted) return null;
    final calEvents = _eventsByCalendar.putIfAbsent(calendarId, () => {});

    final eventId = event.id ?? 'evt_${_nextId++}';
    final storedEvent = event.copyWith(id: eventId, calendarId: calendarId);
    calEvents[eventId] = storedEvent;
    return eventId;
  }

  @override
  Future<bool> deleteEvent({
    required String calendarId,
    required String eventId,
  }) async {
    if (!permissionGranted) return false;
    final calEvents = _eventsByCalendar[calendarId];
    if (calEvents == null) return false;
    return calEvents.remove(eventId) != null;
  }

  @override
  Future<List<DeviceCalendarEvent>> getEventsInRange({
    required String calendarId,
    required DateTime start,
    required DateTime end,
  }) async {
    if (!permissionGranted) return [];
    final calEvents = _eventsByCalendar[calendarId];
    if (calEvents == null) return [];

    return calEvents.values.where((e) {
      return (e.start.isBefore(end) && e.end.isAfter(start));
    }).toList();
  }

  /// Helper to directly inspect stored events during testing.
  Map<String, DeviceCalendarEvent> getEventsForCalendar(String calendarId) {
    return Map.unmodifiable(_eventsByCalendar[calendarId] ?? {});
  }
}
