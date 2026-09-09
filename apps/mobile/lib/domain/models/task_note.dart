import '../../core/constants/timezones.dart';
import 'cognitive_modality.dart';
import 'energy_friction.dart';
import 'task_priority.dart';
import 'task_status.dart';

/// Universal TaskNote Entity representing a Chrysalis task file.
///
/// Strictly enforces all 13 frontmatter fields, explicit local timezone
/// serialization (default: -05:00), and lifecycle state transitions.
class TaskNote {
  /// 1. Imperative Task Title
  final String title;

  /// 2. Task lifecycle status (todo, in-progress, done, archived)
  final TaskStatus status;

  /// 3. Creation timestamp with explicit timezone offset
  final String dateCreated;

  /// 4. Backward-compatible alias for dateCreated
  final String created;

  /// 5. Due date in YYYY-MM-DD format, or null
  final String? due;

  /// 6. Scheduled start timestamp with explicit timezone offset, or null
  final String? scheduled;

  /// 7. Task priority (urgent, high, normal, low, none)
  final TaskPriority priority;

  /// 8. Urgency tier on 1 (Lowest) to 4 (Highest) scale
  final int urgencyTier;

  /// 9. Bio-cognitive modality (analytical, kinetic, synthesis, administrative)
  final CognitiveModality modality;

  /// 10. Estimated time in minutes (baseline duration * active tag multiplier)
  final int timeEstimate;

  /// 11. Energy requirement (high, medium, low)
  final EnergyLevel energy;

  /// 12. Friction rating (high, medium, low)
  final FrictionLevel friction;

  /// 13. Starter wedge status (true if 3-step Starter Wedge is injected)
  final bool microChunked;

  /// Tags list (e.g. ['task', 'pillar-1/research'])
  final List<String> tags;

  /// List of wikilinks to relevant Slipbox atomic research notes
  final List<String> linkedZettels;

  /// Wikilink to parent project roadmap in Projects/*/Roadmap.md, or null
  final String? projectRef;

  /// Optional Google Calendar event synchronization ID
  final String? googleCalendarEventId;

  /// Optional ISO timestamp when the task was started
  final String? startedAt;

  /// Optional ISO timestamp when the task was marked completed
  final String? completedAt;

  /// Markdown content body beneath the frontmatter block
  final String body;

  /// Vault relative path (e.g. "TaskNotes/Tasks/example-task.md")
  final String? path;

  /// Custom / unmodeled frontmatter fields preserved across round-trips
  final Map<String, dynamic> customFields;

  TaskNote({
    required this.title,
    this.status = TaskStatus.todo,
    String? dateCreated,
    String? created,
    this.due,
    this.scheduled,
    this.priority = TaskPriority.normal,
    int? urgencyTier,
    this.modality = CognitiveModality.analytical,
    this.timeEstimate = 45,
    this.energy = EnergyLevel.medium,
    this.friction = FrictionLevel.medium,
    this.microChunked = false,
    List<String>? tags,
    List<String>? linkedZettels,
    this.projectRef,
    this.googleCalendarEventId,
    this.startedAt,
    this.completedAt,
    this.body = '',
    this.path,
    Map<String, dynamic>? customFields,
  })  : dateCreated = dateCreated ?? TimezoneUtils.formatIsoWithOffset(DateTime.now()),
        created = created ?? (dateCreated ?? TimezoneUtils.formatIsoWithOffset(DateTime.now())),
        urgencyTier = (urgencyTier != null && urgencyTier >= 1 && urgencyTier <= 4)
            ? urgencyTier
            : priority.defaultUrgencyTier.clamp(1, 4),
        tags = tags ?? ['task'],
        linkedZettels = linkedZettels ?? const [],
        customFields = customFields ?? {} {
    _validate();
  }

  void _validate() {
    if (title.trim().isEmpty) {
      throw ArgumentError('TaskNote title cannot be empty.');
    }
    if (urgencyTier < 1 || urgencyTier > 4) {
      throw RangeError.range(urgencyTier, 1, 4, 'urgencyTier');
    }
    if (timeEstimate < 0) {
      throw ArgumentError('TaskNote timeEstimate cannot be negative: $timeEstimate');
    }
    // Validate timezone on dateCreated
    if (!TimezoneUtils.hasExplicitTimezoneOffset(dateCreated)) {
      throw FormatException(
        'TaskNote dateCreated must have explicit timezone offset (e.g. -05:00): "$dateCreated"',
      );
    }
    // Validate timezone on scheduled if present
    if (scheduled != null && !TimezoneUtils.hasExplicitTimezoneOffset(scheduled!)) {
      throw FormatException(
        'TaskNote scheduled must have explicit timezone offset (e.g. -05:00): "$scheduled"',
      );
    }
  }

  bool get isCompleted => status == TaskStatus.done;
  bool get isScheduled => scheduled != null && scheduled!.isNotEmpty;
  bool get isInProgress => status == TaskStatus.inProgress;

  /// Creates a copy with specified fields updated.
  TaskNote copyWith({
    String? title,
    TaskStatus? status,
    String? dateCreated,
    String? created,
    String? due,
    String? scheduled,
    bool clearScheduled = false,
    TaskPriority? priority,
    int? urgencyTier,
    CognitiveModality? modality,
    int? timeEstimate,
    EnergyLevel? energy,
    FrictionLevel? friction,
    bool? microChunked,
    List<String>? tags,
    List<String>? linkedZettels,
    String? projectRef,
    bool clearProjectRef = false,
    String? googleCalendarEventId,
    bool clearGoogleCalendarEventId = false,
    String? startedAt,
    String? completedAt,
    String? body,
    String? path,
    Map<String, dynamic>? customFields,
  }) {
    return TaskNote(
      title: title ?? this.title,
      status: status ?? this.status,
      dateCreated: dateCreated ?? this.dateCreated,
      created: created ?? this.created,
      due: due ?? this.due,
      scheduled: clearScheduled ? null : (scheduled ?? this.scheduled),
      priority: priority ?? this.priority,
      urgencyTier: urgencyTier ?? this.urgencyTier,
      modality: modality ?? this.modality,
      timeEstimate: timeEstimate ?? this.timeEstimate,
      energy: energy ?? this.energy,
      friction: friction ?? this.friction,
      microChunked: microChunked ?? this.microChunked,
      tags: tags ?? List.from(this.tags),
      linkedZettels: linkedZettels ?? List.from(this.linkedZettels),
      projectRef: clearProjectRef ? null : (projectRef ?? this.projectRef),
      googleCalendarEventId: clearGoogleCalendarEventId
          ? null
          : (googleCalendarEventId ?? this.googleCalendarEventId),
      startedAt: startedAt ?? this.startedAt,
      completedAt: completedAt ?? this.completedAt,
      body: body ?? this.body,
      path: path ?? this.path,
      customFields: customFields ?? Map.from(this.customFields),
    );
  }

  /// Transition status to [targetStatus] while maintaining lifecycle integrity.
  TaskNote transitionTo(TaskStatus targetStatus, {DateTime? now}) {
    if (!status.canTransitionTo(targetStatus)) {
      throw StateError('Cannot transition TaskNote from ${status.name} to ${targetStatus.name}');
    }
    final timestamp = TimezoneUtils.formatIsoWithOffset(now ?? DateTime.now());

    String? newStartedAt = startedAt;
    String? newCompletedAt = completedAt;

    if (targetStatus == TaskStatus.inProgress && startedAt == null) {
      newStartedAt = timestamp;
    } else if (targetStatus == TaskStatus.done) {
      newCompletedAt = timestamp;
    }

    return copyWith(
      status: targetStatus,
      startedAt: newStartedAt,
      completedAt: newCompletedAt,
    );
  }

  /// Calculates actual duration in minutes if both startedAt and completedAt exist.
  int? get actualDurationMinutes {
    if (startedAt == null || completedAt == null) return null;
    try {
      final start = DateTime.parse(startedAt!);
      final end = DateTime.parse(completedAt!);
      return end.difference(start).inMinutes;
    } catch (_) {
      return null;
    }
  }

  @override
  String toString() => 'TaskNote(title: "$title", status: ${status.name}, est: ${timeEstimate}m)';
}
