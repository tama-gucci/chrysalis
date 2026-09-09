import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/domain/models/biometrics.dart';
import 'package:chrysalis_mobile/domain/models/cognitive_modality.dart';
import 'package:chrysalis_mobile/domain/models/task_note.dart';
import 'package:chrysalis_mobile/domain/models/ultradian_sprint.dart';
import 'package:chrysalis_mobile/presentation/theme/app_theme.dart';
import 'package:chrysalis_mobile/presentation/widgets/active_sprint_card.dart';
import 'package:chrysalis_mobile/presentation/widgets/morning_calibration_sheet.dart';
import 'package:chrysalis_mobile/presentation/widgets/rapid_capture_bar.dart';
import 'package:chrysalis_mobile/presentation/widgets/ultradian_timeline_widget.dart';

void main() {
  group('Presentation Widgets', () {
    testWidgets('ActiveSprintCard renders active sprint and triggers callbacks', (tester) async {
      bool completed = false;
      bool paused = false;

      final block = DiurnalBlock(
        id: 'peak_1',
        sprintType: SprintType.peak,
        modality: CognitiveModality.analytical,
        startTime: DateTime.now().subtract(const Duration(minutes: 20)),
        endTime: DateTime.now().add(const Duration(minutes: 55)),
        title: 'Analytical Sprint 1: Architecture Review',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: ChrysalisTheme.darkTheme,
          home: Scaffold(
            body: ActiveSprintCard(
              activeBlock: block,
              onComplete: () => completed = true,
              onPause: () => paused = true,
            ),
          ),
        ),
      );

      expect(find.text('Analytical Sprint 1: Architecture Review'), findsOneWidget);
      expect(find.text('PEAK SPRINT'), findsOneWidget);

      await tester.tap(find.text('Complete Session'));
      await tester.pump();
      expect(completed, isTrue);

      await tester.tap(find.text('Pause'));
      await tester.pump();
      expect(paused, isTrue);
    });

    testWidgets('UltradianTimelineWidget renders sprint blocks and decompression buffers', (tester) async {
      final now = DateTime.now();
      final schedule = DiurnalSchedule(
        date: now,
        wakeTime: DateTime(now.year, now.month, now.day, 7, 30),
        energyScore: 4,
        blocks: [
          DiurnalBlock(
            id: 'b1',
            sprintType: SprintType.peak,
            modality: CognitiveModality.analytical,
            startTime: DateTime(now.year, now.month, now.day, 8, 15),
            endTime: DateTime(now.year, now.month, now.day, 9, 30),
            title: 'Grant Review',
          ),
          DiurnalBlock(
            id: 'b2',
            sprintType: SprintType.decompression,
            modality: CognitiveModality.administrative,
            startTime: DateTime(now.year, now.month, now.day, 9, 30),
            endTime: DateTime(now.year, now.month, now.day, 9, 45),
            title: '15m Decompression',
          ),
        ],
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: ChrysalisTheme.darkTheme,
          home: Scaffold(
            body: UltradianTimelineWidget(schedule: schedule),
          ),
        ),
      );

      expect(find.text('Grant Review'), findsOneWidget);
      expect(find.text('15m Decompression'), findsOneWidget);
      expect(find.text('15m Reset & Decompression'), findsOneWidget);
    });

    testWidgets('RapidCaptureBar parses shorthand and emits created TaskNote', (tester) async {
      TaskNote? createdTask;

      await tester.pumpWidget(
        MaterialApp(
          theme: ChrysalisTheme.darkTheme,
          home: Scaffold(
            bottomNavigationBar: RapidCaptureBar(
              onTaskCreated: (task) => createdTask = task,
            ),
          ),
        ),
      );

      // Enter shorthand text
      await tester.enterText(
        find.byType(TextField),
        'Clean workshop desk #habits ~25m !1 @kinetic',
      );
      await tester.pump();

      // Check live chip previews appear
      expect(find.text('@kinetic'), findsOneWidget);
      expect(find.text('~25m'), findsOneWidget);
      expect(find.text('!tier 1'), findsOneWidget);
      expect(find.text('#habits'), findsOneWidget);

      // Submit
      await tester.tap(find.byIcon(Icons.add_task));
      await tester.pump();

      expect(createdTask, isNotNull);
      expect(createdTask!.title, equals('Clean workshop desk'));
      expect(createdTask!.timeEstimate, equals(25));
      expect(createdTask!.modality, equals(CognitiveModality.kinetic));
      expect(createdTask!.urgencyTier, equals(1));
    });

    testWidgets('MorningCalibrationSheet displays telemetry insights and invokes onCalibrate', (tester) async {
      DateTime? calibratedWake;
      int? calibratedEnergy;

      final bio = BiometricTelemetry(
        date: DateTime.now(),
        sleep: SleepSession(
          startTime: DateTime.now().subtract(const Duration(hours: 8)),
          endTime: DateTime.now(),
          deepSleepMinutes: 110,
          remSleepMinutes: 90,
          lightSleepMinutes: 260,
          awakeMinutes: 20,
          efficiencyPercent: 92.0,
        ),
        restingHeartRate: RestingHeartRate(timestamp: DateTime.now(), bpm: 54),
        hrv: HeartRateVariability(timestamp: DateTime.now(), rmssdMillis: 65),
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: ChrysalisTheme.darkTheme,
          home: Scaffold(
            body: MorningCalibrationSheet(
              initialWakeTime: DateTime(2026, 9, 5, 7, 45),
              initialEnergy: 3,
              biometrics: bio,
              onCalibrate: (w, e) {
                calibratedWake = w;
                calibratedEnergy = e;
              },
            ),
          ),
        ),
      );

      expect(find.text('Morning Calibration (/calibrate)'), findsOneWidget);
      expect(find.text('Health Connect Telemetry Ingested'), findsOneWidget);
      expect(find.textContaining('Sleep: 8.0h'), findsOneWidget);

      await tester.tap(find.text('Calibrate Today & Lock Sprints'));
      await tester.pump();

      expect(calibratedWake, isNotNull);
      expect(calibratedEnergy, inInclusiveRange(1, 5));
    });
  });
}
