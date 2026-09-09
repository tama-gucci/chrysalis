import 'cognitive_modality.dart';

/// Sprint types according to ultradian rhythms.
enum SprintType {
  /// 75-90m uninterrupted deep work
  peak('Peak Sprint', 75, 90),

  /// 15m mandatory bio-cognitive decompression buffer
  decompression('Decompression Buffer', 15, 15),

  /// 45-60m low-friction kinetic / admin defrost
  slump('Slump & Kinetic Defrost', 45, 60),

  /// 60-90m synthesis & reflection recovery window
  recovery('Recovery & Synthesis', 60, 90);

  final String label;
  final int minDurationMinutes;
  final int maxDurationMinutes;

  const SprintType(this.label, this.minDurationMinutes, this.maxDurationMinutes);
}

/// A scheduled block on today's diurnal timeline.
class DiurnalBlock {
  final String id;
  final SprintType sprintType;
  final CognitiveModality modality;
  final DateTime startTime;
  final DateTime endTime;
  final String title;
  final String? taskPath;
  final bool isCompleted;

  const DiurnalBlock({
    required this.id,
    required this.sprintType,
    required this.modality,
    required this.startTime,
    required this.endTime,
    required this.title,
    this.taskPath,
    this.isCompleted = false,
  });

  int get durationMinutes => endTime.difference(startTime).inMinutes;

  bool isCurrent(DateTime now) {
    return now.isAfter(startTime) && now.isBefore(endTime);
  }

  bool isPast(DateTime now) {
    return now.isAfter(endTime);
  }

  bool isUpcoming(DateTime now) {
    return now.isBefore(startTime);
  }

  DiurnalBlock copyWith({
    String? id,
    SprintType? sprintType,
    CognitiveModality? modality,
    DateTime? startTime,
    DateTime? endTime,
    String? title,
    String? taskPath,
    bool? isCompleted,
  }) {
    return DiurnalBlock(
      id: id ?? this.id,
      sprintType: sprintType ?? this.sprintType,
      modality: modality ?? this.modality,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      title: title ?? this.title,
      taskPath: taskPath ?? this.taskPath,
      isCompleted: isCompleted ?? this.isCompleted,
    );
  }
}

/// Full diurnal plan for a day.
class DiurnalSchedule {
  final DateTime date;
  final DateTime wakeTime;
  final int energyScore;
  final List<DiurnalBlock> blocks;

  const DiurnalSchedule({
    required this.date,
    required this.wakeTime,
    required this.energyScore,
    required this.blocks,
  });

  DiurnalBlock? currentBlock([DateTime? currentTime]) {
    final now = currentTime ?? DateTime.now();
    for (final block in blocks) {
      if (block.isCurrent(now)) return block;
    }
    return null;
  }

  DiurnalBlock? nextBlock([DateTime? currentTime]) {
    final now = currentTime ?? DateTime.now();
    for (final block in blocks) {
      if (block.isUpcoming(now)) return block;
    }
    return null;
  }
}
