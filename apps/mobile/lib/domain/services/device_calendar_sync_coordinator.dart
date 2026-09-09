import '../models/task_note.dart';
import '../models/task_status.dart';
import 'device_calendar_service.dart';

/// Result report from a calendar synchronization pass.
class DeviceCalendarSyncResult {
  final int createdCount;
  final int updatedCount;
  final int deletedCount;
  final List<TaskNote> modifiedTasks;
  final String? error;

  const DeviceCalendarSyncResult({
    this.createdCount = 0,
    this.updatedCount = 0,
    this.deletedCount = 0,
    this.modifiedTasks = const [],
    this.error,
  });

  bool get isSuccess => error == null;

  @override
  String toString() =>
      'DeviceCalendarSyncResult(created: $createdCount, updated: $updatedCount, deleted: $deletedCount, modified: ${modifiedTasks.length}, error: $error)';
}

/// Orchestrates synchronization between Chrysalis [TaskNote] entities and the native host calendar.
///
/// Designed for zero-setup operation:
/// - Pushes scheduled focus sprints into the native device calendar database.
/// - Android OS automatically mirrors events to Google Calendar and Wear OS complications.
/// - Automatically removes or cleans up events when tasks are marked done or unscheduled.
/// - Stamps `googleCalendarEventId` onto the task note to maintain bi-directional identity.
class DeviceCalendarSyncCoordinator {
  final DeviceCalendarDataSource dataSource;
  final String? targetCalendarId;

  DeviceCalendarSyncCoordinator({
    required this.dataSource,
    this.targetCalendarId,
  });

  /// Resolves which device calendar to sync with, prioritizing primary and writable calendars.
  Future<DeviceCalendarInfo?> resolveTargetCalendar() async {
    final calendars = await dataSource.getCalendars();
    if (calendars.isEmpty) return null;

    if (targetCalendarId != null) {
      return calendars.firstWhere(
        (c) => c.id == targetCalendarId,
        orElse: () => calendars.first,
      );
    }

    // Try finding primary non-read-only calendar
    for (final cal in calendars) {
      if (cal.isPrimary && !cal.isReadOnly) return cal;
    }

    // Fallback to first non-read-only calendar
    for (final cal in calendars) {
      if (!cal.isReadOnly) return cal;
    }

    return calendars.first;
  }

  /// Synchronizes a collection of task notes with the device calendar.
  ///
  /// Tasks with `scheduled != null` that are active (`todo` or `in-progress`) are pushed as events.
  /// Tasks that have a `googleCalendarEventId` but are marked `done`, `archived`, or have
  /// `scheduled == null` are removed from the native calendar.
  Future<DeviceCalendarSyncResult> syncTasks(List<TaskNote> tasks) async {
    final hasPerms = await dataSource.hasPermissions();
    if (!hasPerms) {
      final granted = await dataSource.requestPermissions();
      if (!granted) {
        return const DeviceCalendarSyncResult(error: 'Calendar permission denied by user.');
      }
    }

    final targetCal = await resolveTargetCalendar();
    if (targetCal == null) {
      return const DeviceCalendarSyncResult(error: 'No active calendars found on device.');
    }

    int created = 0;
    int updated = 0;
    int deleted = 0;
    final List<TaskNote> modifiedTasks = [];

    for (final task in tasks) {
      final isScheduled = task.scheduled != null;
      final isActive = task.status != TaskStatus.done && task.status != TaskStatus.archived;

      if (isScheduled && isActive) {
        DateTime? startDt;
        try {
          startDt = DateTime.parse(task.scheduled!);
        } catch (_) {}

        if (startDt == null) continue;

        final durationMinutes = task.timeEstimate > 0 ? task.timeEstimate : 45;
        final endDt = startDt.add(Duration(minutes: durationMinutes));

        final modalityTag = task.modality.name.toUpperCase();
        final title = '🎯 [$modalityTag] ${task.title}';
        final descBuffer = StringBuffer();
        descBuffer.writeln('Priority: ${task.priority.name} | Urgency Tier: ${task.urgencyTier}');
        descBuffer.writeln('Tags: ${task.tags.join(', ')}');
        if (task.projectRef != null && task.projectRef!.isNotEmpty) {
          descBuffer.writeln('Project: ${task.projectRef}');
        }
        if (task.linkedZettels.isNotEmpty) {
          descBuffer.writeln('Linked Zettels: ${task.linkedZettels.join(', ')}');
        }
        descBuffer.write('Managed by Chrysalis Mobile');
        final description = descBuffer.toString();

        final event = DeviceCalendarEvent(
          id: task.googleCalendarEventId,
          calendarId: targetCal.id,
          title: title,
          start: startDt,
          end: endDt,
          description: description,
        );

        final eventId = await dataSource.createOrUpdateEvent(
          calendarId: targetCal.id,
          event: event,
        );

        if (eventId != null) {
          if (task.googleCalendarEventId == null) {
            created++;
            modifiedTasks.add(task.copyWith(googleCalendarEventId: eventId));
          } else {
            updated++;
          }
        }
      } else if (task.googleCalendarEventId != null) {
        // Task was completed, archived, or unscheduled -> remove from calendar
        final removed = await dataSource.deleteEvent(
          calendarId: targetCal.id,
          eventId: task.googleCalendarEventId!,
        );

        if (removed) {
          deleted++;
          modifiedTasks.add(task.copyWith(clearGoogleCalendarEventId: true));
        }
      }
    }

    return DeviceCalendarSyncResult(
      createdCount: created,
      updatedCount: updated,
      deletedCount: deleted,
      modifiedTasks: modifiedTasks,
    );
  }
}
