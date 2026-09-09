import '../models/cognitive_modality.dart';
import '../models/task_note.dart';
import '../models/ultradian_sprint.dart';

/// Service implementing Chrysalis Bio-Cognitive Ultradian Scheduling
/// and Telemetry Multiplier Learning.
class BioCognitiveScheduler {
  /// Default duration of a peak ultradian focus sprint in minutes (75-90m).
  static const int defaultPeakSprintMinutes = 75;

  /// Mandatory decompression buffer in minutes.
  static const int decompressionBufferMinutes = 15;

  /// Lower bound for dynamic tag multipliers.
  static const double minMultiplier = 0.20;

  /// Upper bound for dynamic tag multipliers.
  static const double maxMultiplier = 2.00;

  /// Generates a standardized diurnal schedule around the user's wake time and energy score.
  static DiurnalSchedule generateDiurnalSchedule({
    required DateTime date,
    required DateTime wakeTime,
    required int energyScore,
    List<TaskNote> candidateTasks = const [],
  }) {
    final blocks = <DiurnalBlock>[];

    // 1. Morning Buffer & Ingestion (45 mins after wake)
    var currentCursor = wakeTime.add(const Duration(minutes: 30));
    final morningBufferEnd = currentCursor.add(const Duration(minutes: 45));
    blocks.add(
      DiurnalBlock(
        id: 'morning_buffer',
        sprintType: SprintType.decompression,
        modality: CognitiveModality.administrative,
        startTime: currentCursor,
        endTime: morningBufferEnd,
        title: 'Morning Buffer & Intake (/calibrate)',
      ),
    );
    currentCursor = morningBufferEnd;

    // Determine sprint duration based on energy (1-2: 60m, 3-4: 75m, 5: 90m)
    final int peakSprintDuration;
    if (energyScore >= 5) {
      peakSprintDuration = 90;
    } else if (energyScore <= 2) {
      peakSprintDuration = 60;
    } else {
      peakSprintDuration = defaultPeakSprintMinutes;
    }

    final assignedTasks = <TaskNote>{};

    // 2. Peak Sprint 1 (Analytical Focus)
    final sprint1End = currentCursor.add(Duration(minutes: peakSprintDuration));
    final task1 = _pickTaskForModality(
      candidateTasks.where((t) => !assignedTasks.contains(t)).toList(),
      CognitiveModality.analytical,
    );
    if (task1 != null) assignedTasks.add(task1);
    blocks.add(
      DiurnalBlock(
        id: 'peak_sprint_1',
        sprintType: SprintType.peak,
        modality: CognitiveModality.analytical,
        startTime: currentCursor,
        endTime: sprint1End,
        title: task1?.title ?? 'Peak Sprint 1: Analytical Focus',
        taskPath: task1?.path,
      ),
    );
    currentCursor = sprint1End;

    // 3. Mandatory Decompression Buffer (15m)
    final buffer1End = currentCursor.add(const Duration(minutes: decompressionBufferMinutes));
    blocks.add(
      DiurnalBlock(
        id: 'decompression_1',
        sprintType: SprintType.decompression,
        modality: CognitiveModality.administrative,
        startTime: currentCursor,
        endTime: buffer1End,
        title: 'Decompression Buffer (15m Rest & Hydrate)',
      ),
    );
    currentCursor = buffer1End;

    // 4. Peak Sprint 2 (Analytical or Synthesis)
    final sprint2End = currentCursor.add(Duration(minutes: peakSprintDuration));
    final task2 = _pickTaskForModality(
      candidateTasks.where((t) => !assignedTasks.contains(t)).toList(),
      CognitiveModality.analytical,
    );
    if (task2 != null) assignedTasks.add(task2);
    blocks.add(
      DiurnalBlock(
        id: 'peak_sprint_2',
        sprintType: SprintType.peak,
        modality: CognitiveModality.analytical,
        startTime: currentCursor,
        endTime: sprint2End,
        title: task2?.title ?? 'Peak Sprint 2: Deep Analytical Work',
        taskPath: task2?.path,
      ),
    );
    currentCursor = sprint2End;

    // 5. Lunch & Midday Recharge (60m)
    final lunchEnd = currentCursor.add(const Duration(minutes: 60));
    blocks.add(
      DiurnalBlock(
        id: 'midday_recharge',
        sprintType: SprintType.decompression,
        modality: CognitiveModality.kinetic,
        startTime: currentCursor,
        endTime: lunchEnd,
        title: 'Midday Recharge & Nutrition',
      ),
    );
    currentCursor = lunchEnd;

    // 6. Slump & Kinetic Defrost Window (45-60m Kinetic)
    final slumpEnd = currentCursor.add(const Duration(minutes: 50));
    final task3 = _pickTaskForModality(
      candidateTasks.where((t) => !assignedTasks.contains(t)).toList(),
      CognitiveModality.kinetic,
    );
    if (task3 != null) assignedTasks.add(task3);
    blocks.add(
      DiurnalBlock(
        id: 'slump_defrost',
        sprintType: SprintType.slump,
        modality: CognitiveModality.kinetic,
        startTime: currentCursor,
        endTime: slumpEnd,
        title: task3?.title ?? 'Slump & Kinetic Defrost',
        taskPath: task3?.path,
      ),
    );
    currentCursor = slumpEnd;

    // 7. Decompression Buffer (15m)
    final buffer2End = currentCursor.add(const Duration(minutes: decompressionBufferMinutes));
    blocks.add(
      DiurnalBlock(
        id: 'decompression_2',
        sprintType: SprintType.decompression,
        modality: CognitiveModality.administrative,
        startTime: currentCursor,
        endTime: buffer2End,
        title: 'Decompression Buffer (15m Walk)',
      ),
    );
    currentCursor = buffer2End;

    // 8. Recovery & Synthesis Window (60-90m Synthesis)
    final recoveryEnd = currentCursor.add(const Duration(minutes: 75));
    final task4 = _pickTaskForModality(
      candidateTasks.where((t) => !assignedTasks.contains(t)).toList(),
      CognitiveModality.synthesis,
      allowCrossModalityFallback: true,
    );
    if (task4 != null) assignedTasks.add(task4);
    blocks.add(
      DiurnalBlock(
        id: 'recovery_synthesis',
        sprintType: SprintType.recovery,
        modality: CognitiveModality.synthesis,
        startTime: currentCursor,
        endTime: recoveryEnd,
        title: task4?.title ?? 'Recovery & Synthesis Horizon',
        taskPath: task4?.path,
      ),
    );

    return DiurnalSchedule(
      date: date,
      wakeTime: wakeTime,
      energyScore: energyScore,
      blocks: blocks,
    );
  }

  static TaskNote? _pickTaskForModality(
    List<TaskNote> tasks,
    CognitiveModality modality, {
    bool allowCrossModalityFallback = false,
  }) {
    // 1. Direct modality match
    for (final t in tasks) {
      if (!t.isCompleted && t.modality == modality) {
        return t;
      }
    }
    // 2. Compatible modality: synthesis can pair with peak analytical sprints
    if (modality == CognitiveModality.analytical) {
      for (final t in tasks) {
        if (!t.isCompleted && t.modality == CognitiveModality.synthesis) {
          return t;
        }
      }
    }
    // 3. Fallback across modalities only if explicitly allowed (e.g. final window)
    if (allowCrossModalityFallback) {
      for (final t in tasks) {
        if (!t.isCompleted) return t;
      }
    }
    return null;
  }

  /// Calculates an updated dynamic tag multiplier using session telemetry.
  /// Formula: M_new = clamp(M_old * (T_actual / T_est), 0.20, 2.00)
  static double learnTagMultiplier({
    required double currentMultiplier,
    required int estimatedMinutes,
    required int actualMinutes,
  }) {
    if (estimatedMinutes <= 0 || actualMinutes <= 0) {
      return currentMultiplier.clamp(minMultiplier, maxMultiplier);
    }
    final ratio = actualMinutes / estimatedMinutes;
    // Apply smoothing factor (0.3 weight to new telemetry)
    final updated = currentMultiplier * (0.7 + 0.3 * ratio);
    return double.parse(updated.clamp(minMultiplier, maxMultiplier).toStringAsFixed(2));
  }
}
