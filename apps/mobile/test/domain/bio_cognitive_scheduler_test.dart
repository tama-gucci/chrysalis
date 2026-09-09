import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/domain/models/cognitive_modality.dart';
import 'package:chrysalis_mobile/domain/models/task_note.dart';
import 'package:chrysalis_mobile/domain/models/ultradian_sprint.dart';
import 'package:chrysalis_mobile/domain/services/bio_cognitive_scheduler.dart';

void main() {
  group('BioCognitiveScheduler', () {
    final testDate = DateTime(2026, 9, 5);
    final wakeTime = DateTime(2026, 9, 5, 7, 30);

    test('generates ultradian schedule with 75m sprints and 15m decompression buffers', () {
      final schedule = BioCognitiveScheduler.generateDiurnalSchedule(
        date: testDate,
        wakeTime: wakeTime,
        energyScore: 3,
      );

      expect(schedule.blocks.isNotEmpty, isTrue);

      // Verify Morning Buffer
      final morningBuffer = schedule.blocks.first;
      expect(morningBuffer.sprintType, equals(SprintType.decompression));
      expect(morningBuffer.durationMinutes, equals(45));

      // Verify Peak Sprint 1
      final sprint1 = schedule.blocks[1];
      expect(sprint1.sprintType, equals(SprintType.peak));
      expect(sprint1.durationMinutes, equals(75));
      expect(sprint1.modality, equals(CognitiveModality.analytical));

      // Verify Mandatory 15m Decompression Buffer between sprint 1 and sprint 2
      final buffer1 = schedule.blocks[2];
      expect(buffer1.sprintType, equals(SprintType.decompression));
      expect(buffer1.durationMinutes, equals(15));

      // Verify Peak Sprint 2
      final sprint2 = schedule.blocks[3];
      expect(sprint2.sprintType, equals(SprintType.peak));
      expect(sprint2.durationMinutes, equals(75));

      // Verify Slump Window (Kinetic)
      final slump = schedule.blocks.firstWhere((b) => b.sprintType == SprintType.slump);
      expect(slump.modality, equals(CognitiveModality.kinetic));

      // Verify Recovery Window (Synthesis)
      final recovery = schedule.blocks.firstWhere((b) => b.sprintType == SprintType.recovery);
      expect(recovery.modality, equals(CognitiveModality.synthesis));
    });

    test('scales peak sprint duration to 90m for high energy (5) and 60m for low energy (1-2)', () {
      final highEnergy = BioCognitiveScheduler.generateDiurnalSchedule(
        date: testDate,
        wakeTime: wakeTime,
        energyScore: 5,
      );
      final highSprint = highEnergy.blocks.firstWhere((b) => b.sprintType == SprintType.peak);
      expect(highSprint.durationMinutes, equals(90));

      final lowEnergy = BioCognitiveScheduler.generateDiurnalSchedule(
        date: testDate,
        wakeTime: wakeTime,
        energyScore: 2,
      );
      final lowSprint = lowEnergy.blocks.firstWhere((b) => b.sprintType == SprintType.peak);
      expect(lowSprint.durationMinutes, equals(60));
    });

    test('assigns candidate tasks matching modality to appropriate diurnal blocks', () {
      final tasks = [
        TaskNote(
          title: 'Deep Research Task',
          modality: CognitiveModality.analytical,
          path: 'TaskNotes/Tasks/research.md',
        ),
        TaskNote(
          title: 'Physical Workshop Cleanup',
          modality: CognitiveModality.kinetic,
          path: 'TaskNotes/Tasks/cleanup.md',
        ),
      ];

      final schedule = BioCognitiveScheduler.generateDiurnalSchedule(
        date: testDate,
        wakeTime: wakeTime,
        energyScore: 4,
        candidateTasks: tasks,
      );

      final sprint1 = schedule.blocks.firstWhere((b) => b.id == 'peak_sprint_1');
      expect(sprint1.taskPath, equals('TaskNotes/Tasks/research.md'));

      final slump = schedule.blocks.firstWhere((b) => b.id == 'slump_defrost');
      expect(slump.taskPath, equals('TaskNotes/Tasks/cleanup.md'));
    });

    test('learnTagMultiplier updates multipliers and clamps to constitutional bounds [0.20, 2.00]', () {
      // Normal adjustment: estimated 60m, actual 75m -> multiplier slightly increases
      final updated1 = BioCognitiveScheduler.learnTagMultiplier(
        currentMultiplier: 1.00,
        estimatedMinutes: 60,
        actualMinutes: 75,
      );
      expect(updated1, greaterThan(1.00));
      expect(updated1, lessThan(1.20));

      // Overdue task clamping at upper bound 2.00
      final cappedMax = BioCognitiveScheduler.learnTagMultiplier(
        currentMultiplier: 1.95,
        estimatedMinutes: 30,
        actualMinutes: 300,
      );
      expect(cappedMax, equals(2.00));

      // Fast task clamping at lower bound 0.20
      final cappedMin = BioCognitiveScheduler.learnTagMultiplier(
        currentMultiplier: 0.25,
        estimatedMinutes: 300,
        actualMinutes: 10,
      );
      expect(cappedMin, equals(0.20));
    });

    test('candidate tasks are deduplicated across diurnal blocks', () {
      final tasks = [
        TaskNote(
          title: 'Lone Candidate Task',
          modality: CognitiveModality.analytical,
          path: 'TaskNotes/Tasks/lone-task.md',
        ),
      ];

      final schedule = BioCognitiveScheduler.generateDiurnalSchedule(
        date: testDate,
        wakeTime: wakeTime,
        energyScore: 3,
        candidateTasks: tasks,
      );

      final assignedPaths = schedule.blocks
          .where((b) => b.taskPath != null)
          .map((b) => b.taskPath)
          .toList();

      // The task must appear at most once across all blocks
      expect(assignedPaths.length, equals(1));
      expect(assignedPaths.first, equals('TaskNotes/Tasks/lone-task.md'));
    });
  });
}
