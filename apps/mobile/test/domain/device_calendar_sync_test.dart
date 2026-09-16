import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/domain/models/cognitive_modality.dart';
import 'package:chrysalis_mobile/domain/models/energy_friction.dart';
import 'package:chrysalis_mobile/domain/models/task_note.dart';
import 'package:chrysalis_mobile/domain/models/task_priority.dart';
import 'package:chrysalis_mobile/domain/models/task_status.dart';
import 'package:chrysalis_mobile/domain/services/device_calendar_service.dart';
import 'package:chrysalis_mobile/domain/services/device_calendar_sync_coordinator.dart';

void main() {
  group('DeviceCalendarSyncCoordinator Tests (Mobile OS Bridge)', () {
    late MockDeviceCalendarDataSource mockDataSource;
    late DeviceCalendarSyncCoordinator coordinator;

    final baseScheduledTask = TaskNote(
      title: 'Analyze Financial Model',
      status: TaskStatus.todo,
      dateCreated: '2026-09-08T09:00:00-05:00',
      created: '2026-09-08T09:00:00-05:00',
      due: '2026-09-09',
      scheduled: '2026-09-09T10:00:00-05:00',
      priority: TaskPriority.high,
      urgencyTier: 3,
      modality: CognitiveModality.analytical,
      timeEstimate: 75,
      energy: EnergyLevel.high,
      friction: FrictionLevel.medium,
      microChunked: false,
      tags: ['task', 'pillar-1/finance'],
    );

    setUp(() {
      mockDataSource = MockDeviceCalendarDataSource();
      coordinator = DeviceCalendarSyncCoordinator(dataSource: mockDataSource);
    });

    test('Creates native calendar event and stamps googleCalendarEventId on task', () async {
      final result = await coordinator.syncTasks([baseScheduledTask]);

      expect(result.isSuccess, isTrue);
      expect(result.createdCount, equals(1));
      expect(result.updatedCount, equals(0));
      expect(result.deletedCount, equals(0));
      expect(result.modifiedTasks.length, equals(1));

      final modifiedTask = result.modifiedTasks.first;
      expect(modifiedTask.googleCalendarEventId, isNotNull);
      expect(modifiedTask.googleCalendarEventId, startsWith('evt_'));

      // Verify event was stored in mock calendar
      final events = mockDataSource.getEventsForCalendar('primary-google-cal');
      expect(events.length, equals(1));

      final event = events.values.first;
      expect(event.title, contains('🎯 [ANALYTICAL] Analyze Financial Model'));
      expect(event.start, equals(DateTime.parse('2026-09-09T10:00:00-05:00')));
      expect(event.end, equals(DateTime.parse('2026-09-09T10:00:00-05:00').add(const Duration(minutes: 75))));
      expect(event.description, contains('pillar-1/finance'));
    });

    test('Updates existing event when scheduled time changes', () async {
      // First sync creates the event
      final initialResult = await coordinator.syncTasks([baseScheduledTask]);
      final stampedTask = initialResult.modifiedTasks.first;
      final assignedEventId = stampedTask.googleCalendarEventId;

      // Reschedule task to 13:30
      final rescheduledTask = stampedTask.copyWith(
        scheduled: '2026-09-09T13:30:00-05:00',
      );

      final updateResult = await coordinator.syncTasks([rescheduledTask]);

      expect(updateResult.isSuccess, isTrue);
      expect(updateResult.createdCount, equals(0));
      expect(updateResult.updatedCount, equals(1));
      expect(updateResult.deletedCount, equals(0));

      final events = mockDataSource.getEventsForCalendar('primary-google-cal');
      expect(events.length, equals(1));
      expect(events[assignedEventId]?.start, equals(DateTime.parse('2026-09-09T13:30:00-05:00')));
    });

    test('Deletes calendar event and clears ID when task is marked done', () async {
      // First sync creates the event
      final initialResult = await coordinator.syncTasks([baseScheduledTask]);
      final stampedTask = initialResult.modifiedTasks.first;

      // Complete the task
      final completedTask = stampedTask.transitionTo(TaskStatus.done);

      final deleteResult = await coordinator.syncTasks([completedTask]);

      expect(deleteResult.isSuccess, isTrue);
      expect(deleteResult.deletedCount, equals(1));
      expect(deleteResult.modifiedTasks.length, equals(1));

      final modifiedTask = deleteResult.modifiedTasks.first;
      expect(modifiedTask.googleCalendarEventId, isNull);

      // Verify event was removed from calendar
      final events = mockDataSource.getEventsForCalendar('primary-google-cal');
      expect(events.isEmpty, isTrue);
    });

    test('Deletes calendar event when task is unscheduled (scheduled: null)', () async {
      final initialResult = await coordinator.syncTasks([baseScheduledTask]);
      final stampedTask = initialResult.modifiedTasks.first;

      // Unschedule the task
      final unscheduledTask = stampedTask.copyWith(clearScheduled: true);

      final deleteResult = await coordinator.syncTasks([unscheduledTask]);

      expect(deleteResult.isSuccess, isTrue);
      expect(deleteResult.deletedCount, equals(1));
      expect(deleteResult.modifiedTasks.first.googleCalendarEventId, isNull);

      final events = mockDataSource.getEventsForCalendar('primary-google-cal');
      expect(events.isEmpty, isTrue);
    });

    test('Returns error when user denies calendar permission', () async {
      mockDataSource.permissionGranted = false;
      mockDataSource.shouldGrantOnRequest = false;

      final result = await coordinator.syncTasks([baseScheduledTask]);

      expect(result.isSuccess, isFalse);
      expect(result.error, contains('permission denied'));
      expect(result.createdCount, equals(0));
    });

    test('Targets primary writable calendar when multiple calendars exist', () async {
      final multiCalSource = MockDeviceCalendarDataSource(
        initialCalendars: const [
          DeviceCalendarInfo(
            id: 'subscribed-holidays',
            name: 'US Holidays',
            accountName: 'holidays@example.com',
            isPrimary: false,
            isReadOnly: true,
          ),
          DeviceCalendarInfo(
            id: 'work-cal',
            name: 'Work Focus',
            accountName: 'work@example.com',
            isPrimary: true,
            isReadOnly: false,
          ),
        ],
      );

      final multiCoordinator = DeviceCalendarSyncCoordinator(dataSource: multiCalSource);
      final resolved = await multiCoordinator.resolveTargetCalendar();

      expect(resolved, isNotNull);
      expect(resolved!.id, equals('work-cal'));
      expect(resolved.name, equals('Work Focus'));
    });
  });
}
