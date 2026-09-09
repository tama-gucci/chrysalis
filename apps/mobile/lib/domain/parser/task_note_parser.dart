import 'package:yaml/yaml.dart';
import '../../core/constants/timezones.dart';
import '../../core/exceptions/app_exceptions.dart';
import '../models/cognitive_modality.dart';
import '../models/energy_friction.dart';
import '../models/task_note.dart';
import '../models/task_priority.dart';
import '../models/task_status.dart';

/// Universal TaskNotes Parser and Serializer for Chrysalis.
///
/// Complies with the 13-field Universal TaskNotes Frontmatter Schema
/// and the Absolute Explicit Local Timezone Invariant (-05:00).
class TaskNoteParser {
  static const String defaultTimezone = TimezoneUtils.defaultTimezoneOffset;

  /// Parses raw markdown file content into a [TaskNote] domain object.
  static TaskNote parse(
    String content, {
    String? path,
    bool strictTimezone = true,
  }) {
    final trimmed = content.trimLeft();
    if (!trimmed.startsWith('---')) {
      throw const TaskParseException('File missing frontmatter opening delimiter ("---").');
    }

    final endFenceIndex = trimmed.indexOf('\n---', 3);
    if (endFenceIndex == -1) {
      throw const TaskParseException('File missing frontmatter closing delimiter ("---").');
    }

    final yamlString = trimmed.substring(3, endFenceIndex).trim();
    final body = trimmed.substring(endFenceIndex + 4).replaceFirst(RegExp(r'^\r?\n'), '');

    final dynamic yamlMap;
    try {
      yamlMap = loadYaml(yamlString);
    } catch (e) {
      throw TaskParseException('Invalid YAML syntax in frontmatter', e);
    }

    if (yamlMap is! Map) {
      throw const TaskParseException('Frontmatter does not evaluate to a YAML map.');
    }

    // 1. Title
    final rawTitle = yamlMap['title']?.toString().trim();
    if (rawTitle == null || rawTitle.isEmpty) {
      throw const TaskParseException('Frontmatter is missing required field: "title".');
    }

    // 2. Status
    final rawStatus = yamlMap['status']?.toString();
    final TaskStatus status;
    if (rawStatus == null || rawStatus.isEmpty) {
      status = TaskStatus.todo;
    } else {
      try {
        status = TaskStatus.fromString(rawStatus);
      } catch (e) {
        throw TaskParseException('Invalid status value: "$rawStatus"', e);
      }
    }

    // 3 & 4. dateCreated & created
    final rawDateCreated = yamlMap['dateCreated']?.toString();
    final rawCreated = yamlMap['created']?.toString();
    final String dateCreated;
    if (rawDateCreated != null && rawDateCreated.isNotEmpty) {
      dateCreated = _validateOrNormalizeTimestamp(rawDateCreated, strictTimezone, 'dateCreated');
    } else if (rawCreated != null && rawCreated.isNotEmpty) {
      dateCreated = _validateOrNormalizeTimestamp(rawCreated, strictTimezone, 'created');
    } else {
      dateCreated = TimezoneUtils.formatIsoWithOffset(DateTime.now(), offset: defaultTimezone);
    }

    final created = rawCreated != null && rawCreated.isNotEmpty
        ? _validateOrNormalizeTimestamp(rawCreated, strictTimezone, 'created')
        : dateCreated;

    // 5. Due
    final rawDue = yamlMap['due']?.toString().trim();
    final String? due;
    if (rawDue == null || rawDue == 'null' || rawDue.isEmpty) {
      due = null;
    } else {
      // Normalize unquoted YAML dates (e.g. "2026-09-10 00:00:00.000" -> "2026-09-10")
      due = rawDue.length >= 10 ? rawDue.substring(0, 10) : rawDue;
    }

    // 6. Scheduled
    final rawScheduled = yamlMap['scheduled']?.toString().trim();
    final String? scheduled;
    if (rawScheduled == null || rawScheduled == 'null' || rawScheduled.isEmpty) {
      scheduled = null;
    } else {
      scheduled = _validateOrNormalizeTimestamp(rawScheduled, strictTimezone, 'scheduled');
    }

    // 7. Priority
    final rawPriority = yamlMap['priority']?.toString();
    final priority = rawPriority != null ? TaskPriority.fromString(rawPriority) : TaskPriority.normal;

    // 8. Urgency Tier
    final rawTier = yamlMap['urgency_tier'];
    final int urgencyTier;
    if (rawTier is int && rawTier >= 1 && rawTier <= 4) {
      urgencyTier = rawTier;
    } else if (rawTier != null && int.tryParse(rawTier.toString()) != null) {
      urgencyTier = int.parse(rawTier.toString()).clamp(1, 4);
    } else {
      urgencyTier = priority.defaultUrgencyTier.clamp(1, 4);
    }

    // 9. Modality
    final rawModality = yamlMap['modality']?.toString();
    final modality = rawModality != null ? CognitiveModality.fromString(rawModality) : CognitiveModality.analytical;

    // 10. Time Estimate
    final rawEst = yamlMap['timeEstimate'];
    final int timeEstimate;
    if (rawEst is int) {
      timeEstimate = rawEst;
    } else if (rawEst != null && int.tryParse(rawEst.toString()) != null) {
      timeEstimate = int.parse(rawEst.toString());
    } else {
      timeEstimate = 45;
    }

    // 11. Energy
    final rawEnergy = yamlMap['energy']?.toString();
    final energy = rawEnergy != null ? EnergyLevel.fromString(rawEnergy) : EnergyLevel.medium;

    // 12. Friction
    final rawFriction = yamlMap['friction']?.toString();
    final friction = rawFriction != null ? FrictionLevel.fromString(rawFriction) : FrictionLevel.medium;

    // 13. Micro Chunked
    final rawChunked = yamlMap['micro_chunked'];
    final bool microChunked = rawChunked is bool ? rawChunked : (rawChunked?.toString() == 'true');

    // Tags
    final tags = <String>[];
    final rawTags = yamlMap['tags'];
    if (rawTags is List) {
      for (final t in rawTags) {
        if (t != null) tags.add(t.toString());
      }
    }
    if (tags.isEmpty) {
      tags.add('task');
    }

    final googleCalendarEventId = yamlMap['googleCalendarEventId']?.toString();
    final startedAt = yamlMap['startedAt']?.toString();
    final completedAt = yamlMap['completedAt']?.toString();

    // Hypergraph linked zettels and parent project reference
    final linkedZettels = <String>[];
    final rawZettels = yamlMap['linked_zettels'];
    if (rawZettels is List) {
      for (final z in rawZettels) {
        if (z != null) {
          final s = z.toString().trim().replaceAll('"', '');
          if (s.isNotEmpty) linkedZettels.add(s);
        }
      }
    }

    final rawProjectRef = yamlMap['project_ref']?.toString().trim();
    final String? projectRef;
    if (rawProjectRef == null || rawProjectRef == 'null' || rawProjectRef.isEmpty) {
      projectRef = null;
    } else {
      projectRef = rawProjectRef.replaceAll('"', '');
    }

    // Preserve custom / unknown frontmatter fields
    const knownKeys = {
      'title',
      'status',
      'dateCreated',
      'created',
      'due',
      'scheduled',
      'priority',
      'urgency_tier',
      'modality',
      'timeEstimate',
      'energy',
      'friction',
      'micro_chunked',
      'tags',
      'linked_zettels',
      'project_ref',
      'googleCalendarEventId',
      'startedAt',
      'completedAt',
    };
    final customFields = <String, dynamic>{};
    yamlMap.forEach((key, value) {
      final keyStr = key.toString();
      if (!knownKeys.contains(keyStr)) {
        customFields[keyStr] = value;
      }
    });

    return TaskNote(
      title: rawTitle,
      status: status,
      dateCreated: dateCreated,
      created: created,
      due: due,
      scheduled: scheduled,
      priority: priority,
      urgencyTier: urgencyTier,
      modality: modality,
      timeEstimate: timeEstimate,
      energy: energy,
      friction: friction,
      microChunked: microChunked,
      tags: tags,
      linkedZettels: linkedZettels,
      projectRef: projectRef,
      googleCalendarEventId: (googleCalendarEventId == 'null' || googleCalendarEventId == '') ? null : googleCalendarEventId,
      startedAt: (startedAt == 'null' || startedAt == '') ? null : startedAt,
      completedAt: (completedAt == 'null' || completedAt == '') ? null : completedAt,
      body: body,
      path: path,
      customFields: customFields,
    );
  }

  /// Serializes a [TaskNote] into standardized Markdown with YAML frontmatter.
  static String serialize(
    TaskNote task, {
    String timezoneOffset = defaultTimezone,
  }) {
    final buffer = StringBuffer();
    buffer.writeln('---');

    // Escape title if it contains special characters
    final escapedTitle = _escapeYamlString(task.title);
    buffer.writeln('title: $escapedTitle');
    buffer.writeln('status: ${task.status.yamlValue}');

    // Ensure explicit offset
    final dateCreated = _ensureOffset(task.dateCreated, timezoneOffset);
    buffer.writeln('dateCreated: "$dateCreated"');
    buffer.writeln('created: "$dateCreated"');

    if (task.due != null && task.due!.isNotEmpty) {
      buffer.writeln('due: "${task.due}"');
    } else {
      buffer.writeln('due: null');
    }

    if (task.scheduled != null && task.scheduled!.isNotEmpty) {
      final scheduled = _ensureOffset(task.scheduled!, timezoneOffset);
      buffer.writeln('scheduled: "$scheduled"');
    } else {
      buffer.writeln('scheduled: null');
    }

    buffer.writeln('priority: ${task.priority.yamlValue}');
    buffer.writeln('urgency_tier: ${task.urgencyTier}');
    buffer.writeln('modality: ${task.modality.yamlValue}');
    buffer.writeln('timeEstimate: ${task.timeEstimate}');
    buffer.writeln('energy: ${task.energy.yamlValue}');
    buffer.writeln('friction: ${task.friction.yamlValue}');
    buffer.writeln('micro_chunked: ${task.microChunked}');

    if (task.tags.isNotEmpty) {
      buffer.writeln('tags:');
      for (final tag in task.tags) {
        buffer.writeln('  - $tag');
      }
    } else {
      buffer.writeln('tags:\n  - task');
    }

    if (task.linkedZettels.isNotEmpty) {
      buffer.writeln('linked_zettels:');
      for (final zettel in task.linkedZettels) {
        final clean = zettel.replaceAll('"', '');
        buffer.writeln('  - "$clean"');
      }
    } else {
      buffer.writeln('linked_zettels: []');
    }

    if (task.projectRef != null && task.projectRef!.isNotEmpty && task.projectRef != 'null') {
      final clean = task.projectRef!.replaceAll('"', '');
      buffer.writeln('project_ref: "$clean"');
    } else {
      buffer.writeln('project_ref: null');
    }

    if (task.googleCalendarEventId != null) {
      buffer.writeln('googleCalendarEventId: "${task.googleCalendarEventId}"');
    }
    if (task.startedAt != null) {
      buffer.writeln('startedAt: "${_ensureOffset(task.startedAt!, timezoneOffset)}"');
    }
    if (task.completedAt != null) {
      buffer.writeln('completedAt: "${_ensureOffset(task.completedAt!, timezoneOffset)}"');
    }

    if (task.customFields.isNotEmpty) {
      task.customFields.forEach((k, v) {
        if (v == null) {
          buffer.writeln('$k: null');
        } else if (v is String) {
          buffer.writeln('$k: "${v.replaceAll('"', r'\"')}"');
        } else {
          buffer.writeln('$k: $v');
        }
      });
    }

    buffer.writeln('---');

    // Append body or generate standard template body if empty
    if (task.body.trim().isNotEmpty) {
      buffer.writeln();
      buffer.write(task.body.trim());
      buffer.writeln();
    } else {
      buffer.writeln();
      buffer.writeln('# ${task.title}');
      buffer.writeln();
      buffer.writeln('## Context & Objective');
      buffer.writeln('Created via Chrysalis Mobile Client.');
      buffer.writeln();
      buffer.writeln('## Starter Wedge Execution Checklist');
      buffer.writeln('- [ ] Step 1: Open project context');
      buffer.writeln('- [ ] Step 2: Execute core sprint');
      buffer.writeln('- [ ] Step 3: Complete and record deliverable');
    }

    return buffer.toString();
  }

  static String _validateOrNormalizeTimestamp(String raw, bool strict, String field) {
    var trimmed = raw.trim().replaceAll('"', '').replaceAll("'", '');
    // Normalize space separator to 'T' if present (e.g. "2026-09-04 19:00:00-05:00")
    if (trimmed.contains(' ') && !trimmed.contains('T')) {
      trimmed = trimmed.replaceFirst(' ', 'T');
    }
    if (trimmed.endsWith('Z') || trimmed.endsWith('z')) {
      if (strict) {
        throw TaskParseException(
          'Chrysalis Invariant Violation: raw UTC "Z" in "$field" ($trimmed) is prohibited. '
          'Must specify explicit local offset like "$defaultTimezone".',
        );
      }
      return TimezoneUtils.formatIsoWithOffset(DateTime.parse(trimmed), offset: defaultTimezone);
    }
    if (!TimezoneUtils.hasExplicitTimezoneOffset(trimmed)) {
      if (strict) {
        throw TaskParseException(
          'Chrysalis Invariant Violation: "$field" ($trimmed) lacks explicit timezone offset (e.g. $defaultTimezone).',
        );
      }
      try {
        final parsed = DateTime.parse(trimmed);
        return TimezoneUtils.formatIsoWithOffset(parsed, offset: defaultTimezone);
      } catch (_) {
        return trimmed;
      }
    }
    return trimmed;
  }

  static String _ensureOffset(String timestamp, String offset) {
    var trimmed = timestamp.trim().replaceAll('"', '').replaceAll("'", '');
    if (trimmed.contains(' ') && !trimmed.contains('T')) {
      trimmed = trimmed.replaceFirst(' ', 'T');
    }
    if (trimmed.endsWith('Z') || trimmed.endsWith('z')) {
      final dt = DateTime.parse(trimmed);
      return TimezoneUtils.formatIsoWithOffset(dt, offset: offset);
    }
    if (!TimezoneUtils.hasExplicitTimezoneOffset(trimmed)) {
      try {
        final dt = DateTime.parse(trimmed);
        return TimezoneUtils.formatIsoWithOffset(dt, offset: offset);
      } catch (_) {
        return trimmed;
      }
    }
    return trimmed;
  }

  static String _escapeYamlString(String val) {
    return '"${val.replaceAll('"', r'\"')}"';
  }
}
