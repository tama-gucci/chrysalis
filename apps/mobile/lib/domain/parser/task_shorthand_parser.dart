import '../models/cognitive_modality.dart';
import '../models/energy_friction.dart';
import '../models/task_note.dart';
import '../models/task_priority.dart';
import '../models/task_status.dart';

/// Result of parsing a rapid shorthand input string.
class ParsedShorthand {
  final String rawInput;
  final String title;
  final List<String> tags;
  final int durationMinutes;
  final int urgencyTier;
  final TaskPriority priority;
  final CognitiveModality modality;
  final EnergyLevel energy;
  final FrictionLevel friction;
  final List<String> linkedZettels;
  final String? projectRef;

  const ParsedShorthand({
    required this.rawInput,
    required this.title,
    required this.tags,
    this.linkedZettels = const [],
    this.projectRef,
    required this.durationMinutes,
    required this.urgencyTier,
    required this.priority,
    required this.modality,
    required this.energy,
    required this.friction,
  });

  /// Instantiates a complete [TaskNote] from this parsed shorthand.
  TaskNote toTaskNote({
    String? path,
    String? dueDate,
  }) {
    return TaskNote(
      title: title,
      status: TaskStatus.todo,
      due: dueDate,
      priority: priority,
      urgencyTier: urgencyTier,
      modality: modality,
      timeEstimate: durationMinutes,
      energy: energy,
      friction: friction,
      tags: tags.isEmpty ? ['task'] : tags,
      linkedZettels: linkedZettels,
      projectRef: projectRef,
      path: path,
    );
  }
}

/// Rapid Shorthand Task Capture Parser.
///
/// Syntax examples:
/// - "Write grant proposal #pillar-1/grants ~75m !3 @analytical"
/// - "Fix mobile layout overflow ~30m !4 @analytical"
/// - "Clean workspace desk #habits ~15m !1 @kinetic"
class TaskShorthandParser {
  static final RegExp _tagRegex = RegExp(r'(?:^|\s)#([a-zA-Z][a-zA-Z0-9_\-\/]*)');
  static final RegExp _durationRegex = RegExp(r'(?:^|\s)~(\d+(?:\.\d+)?)(m|min|h|hr)?(?=\s|$)', caseSensitive: false);
  static final RegExp _urgencyRegex = RegExp(r'(?:^|\s)!([1-4]|urgent|high|normal|low)(?=\s|$)', caseSensitive: false);
  static final RegExp _modalityRegex = RegExp(r'(?:^|\s)@(analytical|kinetic|synthesis|admin|administrative)(?=\s|$)', caseSensitive: false);
  static final RegExp _wikilinkRegex = RegExp(r'\[\[(.*?)\]\]');

  static ParsedShorthand parse(String input) {
    var working = input.trim();

    // 0. Extract WikiLinks ([[Projects/...]] or [[Zettel...]])
    final linkedZettels = <String>[];
    String? projectRef;
    final wikilinkMatches = _wikilinkRegex.allMatches(working).toList();
    for (final m in wikilinkMatches) {
      final inner = m.group(1)?.trim();
      if (inner != null && inner.isNotEmpty) {
        final link = '[[$inner]]';
        if (inner.startsWith('Projects/') || inner.contains('Roadmap')) {
          projectRef = link;
        } else {
          linkedZettels.add(link);
        }
      }
    }
    working = working.replaceAll(_wikilinkRegex, ' ');

    // 1. Extract Tags
    final tags = <String>['task'];
    final tagMatches = _tagRegex.allMatches(working).toList();
    for (final m in tagMatches) {
      final tag = m.group(1);
      if (tag != null && !tags.contains(tag)) {
        tags.add(tag);
      }
    }
    working = working.replaceAll(_tagRegex, ' ');

    // 2. Extract Duration (~45m, ~1.5h, etc.)
    int durationMinutes = 45; // default ultradian half-sprint baseline
    final durationMatch = _durationRegex.firstMatch(working);
    if (durationMatch != null) {
      final valueStr = durationMatch.group(1)!;
      final unit = (durationMatch.group(2) ?? 'm').toLowerCase();
      final numVal = double.tryParse(valueStr) ?? 45.0;
      if (unit.startsWith('h')) {
        durationMinutes = (numVal * 60).round();
      } else {
        durationMinutes = numVal.round();
      }
      working = working.replaceFirst(durationMatch.group(0)!, ' ');
    }

    // 3. Extract Urgency / Priority (!1, !2, !3, !4 or !urgent, etc.)
    int urgencyTier = 2;
    TaskPriority priority = TaskPriority.normal;
    final urgencyMatch = _urgencyRegex.firstMatch(working);
    if (urgencyMatch != null) {
      final raw = urgencyMatch.group(1)!.toLowerCase();
      switch (raw) {
        case '4':
        case 'urgent':
          urgencyTier = 4;
          priority = TaskPriority.urgent;
          break;
        case '3':
        case 'high':
          urgencyTier = 3;
          priority = TaskPriority.high;
          break;
        case '2':
        case 'normal':
          urgencyTier = 2;
          priority = TaskPriority.normal;
          break;
        case '1':
        case 'low':
          urgencyTier = 1;
          priority = TaskPriority.low;
          break;
      }
      working = working.replaceFirst(urgencyMatch.group(0)!, ' ');
    }

    // 4. Extract Modality (@analytical, @kinetic, @synthesis, @administrative)
    CognitiveModality modality = CognitiveModality.analytical;
    final modalityMatch = _modalityRegex.firstMatch(working);
    if (modalityMatch != null) {
      final raw = modalityMatch.group(1)!.toLowerCase();
      if (raw == 'kinetic') {
        modality = CognitiveModality.kinetic;
      } else if (raw == 'synthesis') {
        modality = CognitiveModality.synthesis;
      } else if (raw.startsWith('admin')) {
        modality = CognitiveModality.administrative;
      } else {
        modality = CognitiveModality.analytical;
      }
      working = working.replaceFirst(modalityMatch.group(0)!, ' ');
    }

    // Infer energy & friction from modality & duration
    EnergyLevel energy = EnergyLevel.medium;
    FrictionLevel friction = FrictionLevel.medium;
    if (modality == CognitiveModality.analytical && durationMinutes >= 60) {
      energy = EnergyLevel.high;
      friction = FrictionLevel.high;
    } else if (modality == CognitiveModality.administrative || durationMinutes <= 20) {
      energy = EnergyLevel.low;
      friction = FrictionLevel.low;
    }

    // 5. Remaining text is clean title
    final cleanTitle = working.replaceAll(RegExp(r'\s+'), ' ').trim();
    final finalTitle = cleanTitle.isNotEmpty ? cleanTitle : 'Untitled Task';

    return ParsedShorthand(
      rawInput: input,
      title: finalTitle,
      tags: tags,
      linkedZettels: linkedZettels,
      projectRef: projectRef,
      durationMinutes: durationMinutes.clamp(5, 360),
      urgencyTier: urgencyTier,
      priority: priority,
      modality: modality,
      energy: energy,
      friction: friction,
    );
  }
}
