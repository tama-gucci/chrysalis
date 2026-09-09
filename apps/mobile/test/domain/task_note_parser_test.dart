import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/core/exceptions/app_exceptions.dart';
import 'package:chrysalis_mobile/domain/models/cognitive_modality.dart';
import 'package:chrysalis_mobile/domain/models/energy_friction.dart';
import 'package:chrysalis_mobile/domain/models/task_note.dart';
import 'package:chrysalis_mobile/domain/models/task_priority.dart';
import 'package:chrysalis_mobile/domain/models/task_status.dart';
import 'package:chrysalis_mobile/domain/parser/task_note_parser.dart';

void main() {
  group('TaskNoteParser & Serializer', () {
    const validMarkdown = '''---
title: "Implement Android Frontend Architecture"
status: todo
dateCreated: "2026-09-04T19:00:00-05:00"
created: "2026-09-04T19:00:00-05:00"
due: "2026-09-07"
scheduled: "2026-09-05T10:00:00-05:00"
priority: high
urgency_tier: 3
modality: analytical
timeEstimate: 75
energy: high
friction: medium
micro_chunked: true
tags:
  - task
  - pillar-1/mobile
googleCalendarEventId: "evt-gcal-12345"
---

# Implement Android Frontend Architecture

## Context & Objective
Scaffold the clean architecture layers for Chrysalis mobile.

## Starter Wedge Execution Checklist
- [ ] Step 1: Initialize Flutter project
- [ ] Step 2: Implement domain models
- [ ] Step 3: Verify tests
''';

    test('parses all 13 frontmatter fields correctly', () {
      final task = TaskNoteParser.parse(validMarkdown);

      expect(task.title, equals('Implement Android Frontend Architecture'));
      expect(task.status, equals(TaskStatus.todo));
      expect(task.dateCreated, equals('2026-09-04T19:00:00-05:00'));
      expect(task.created, equals('2026-09-04T19:00:00-05:00'));
      expect(task.due, equals('2026-09-07'));
      expect(task.scheduled, equals('2026-09-05T10:00:00-05:00'));
      expect(task.priority, equals(TaskPriority.high));
      expect(task.urgencyTier, equals(3));
      expect(task.modality, equals(CognitiveModality.analytical));
      expect(task.timeEstimate, equals(75));
      expect(task.energy, equals(EnergyLevel.high));
      expect(task.friction, equals(FrictionLevel.medium));
      expect(task.microChunked, isTrue);
      expect(task.tags, containsAll(['task', 'pillar-1/mobile']));
      expect(task.googleCalendarEventId, equals('evt-gcal-12345'));
      expect(task.body, contains('## Context & Objective'));
    });

    test('enforces explicit local timezone (-05:00) and rejects raw UTC "Z"', () {
      const utcMarkdown = '''---
title: "Invalid UTC Task"
status: todo
dateCreated: "2026-09-04T19:00:00Z"
priority: normal
urgency_tier: 2
modality: analytical
timeEstimate: 45
energy: medium
friction: medium
micro_chunked: false
---
''';

      expect(
        () => TaskNoteParser.parse(utcMarkdown, strictTimezone: true),
        throwsA(isA<TaskParseException>().having(
          (e) => e.message,
          'message',
          contains('raw UTC "Z" in "dateCreated"'),
        )),
      );
    });

    test('serializes all 13 fields with explicit -05:00 timezone', () {
      final task = TaskNote(
        title: 'Serialize Test Task',
        status: TaskStatus.inProgress,
        dateCreated: '2026-09-04T12:00:00-05:00',
        due: '2026-09-10',
        scheduled: '2026-09-05T09:30:00-05:00',
        priority: TaskPriority.urgent,
        urgencyTier: 4,
        modality: CognitiveModality.synthesis,
        timeEstimate: 90,
        energy: EnergyLevel.high,
        friction: FrictionLevel.low,
        microChunked: true,
        tags: ['task', 'pillar-2/synthesis'],
        body: '## Context\nTesting serialization output.',
      );

      final serialized = TaskNoteParser.serialize(task);

      expect(serialized, startsWith('---\n'));
      expect(serialized, contains('title: "Serialize Test Task"'));
      expect(serialized, contains('status: in-progress'));
      expect(serialized, contains('dateCreated: "2026-09-04T12:00:00-05:00"'));
      expect(serialized, contains('created: "2026-09-04T12:00:00-05:00"'));
      expect(serialized, contains('due: "2026-09-10"'));
      expect(serialized, contains('scheduled: "2026-09-05T09:30:00-05:00"'));
      expect(serialized, contains('priority: urgent'));
      expect(serialized, contains('urgency_tier: 4'));
      expect(serialized, contains('modality: synthesis'));
      expect(serialized, contains('timeEstimate: 90'));
      expect(serialized, contains('energy: high'));
      expect(serialized, contains('friction: low'));
      expect(serialized, contains('micro_chunked: true'));
      expect(serialized, contains('tags:\n  - task\n  - pillar-2/synthesis'));
      expect(serialized, contains('## Context\nTesting serialization output.'));
      // Invariant: Never contains raw Z
      expect(serialized, isNot(contains('"Z"')));
    });

    test('round-trip fidelity: parse -> serialize -> parse retains equality', () {
      final original = TaskNoteParser.parse(validMarkdown);
      final serialized = TaskNoteParser.serialize(original);
      final reparsed = TaskNoteParser.parse(serialized);

      expect(reparsed.title, equals(original.title));
      expect(reparsed.status, equals(original.status));
      expect(reparsed.dateCreated, equals(original.dateCreated));
      expect(reparsed.due, equals(original.due));
      expect(reparsed.scheduled, equals(original.scheduled));
      expect(reparsed.priority, equals(original.priority));
      expect(reparsed.urgencyTier, equals(original.urgencyTier));
      expect(reparsed.modality, equals(original.modality));
      expect(reparsed.timeEstimate, equals(original.timeEstimate));
      expect(reparsed.energy, equals(original.energy));
      expect(reparsed.friction, equals(original.friction));
      expect(reparsed.microChunked, equals(original.microChunked));
      expect(reparsed.tags, equals(original.tags));
    });

    test('validates lifecycle transitions and computes actualDurationMinutes', () {
      final task = TaskNote(
        title: 'Lifecycle Task',
        status: TaskStatus.todo,
        timeEstimate: 60,
      );

      // Transition to in-progress
      final inProgress = task.transitionTo(
        TaskStatus.inProgress,
        now: DateTime.parse('2026-09-04T10:00:00-05:00'),
      );
      expect(inProgress.status, equals(TaskStatus.inProgress));
      expect(inProgress.startedAt, equals('2026-09-04T10:00:00-05:00'));

      // Transition to done
      final done = inProgress.transitionTo(
        TaskStatus.done,
        now: DateTime.parse('2026-09-04T11:15:00-05:00'),
      );
      expect(done.status, equals(TaskStatus.done));
      expect(done.completedAt, equals('2026-09-04T11:15:00-05:00'));
      expect(done.actualDurationMinutes, equals(75));

      // Transition to archived
      final archived = done.transitionTo(TaskStatus.archived);
      expect(archived.status, equals(TaskStatus.archived));

      // Archived cannot transition directly to in-progress
      expect(() => archived.transitionTo(TaskStatus.inProgress), throwsStateError);
    });

    test('throws ArgumentError on invalid title or negative estimate', () {
      expect(
        () => TaskNote(title: '   '),
        throwsArgumentError,
      );
      expect(
        () => TaskNote(title: 'Valid', timeEstimate: -10),
        throwsArgumentError,
      );
    });

    test('parses unquoted due dates and space-separated timestamps cleanly', () {
      const markdown = '''---
title: "Unquoted Dates Task"
status: todo
dateCreated: "2026-09-04 19:00:00-05:00"
due: 2026-09-10
scheduled: 2026-09-05 10:00:00-05:00
priority: normal
urgency_tier: 2
modality: analytical
timeEstimate: 45
energy: medium
friction: medium
micro_chunked: false
tags:
  - task
---
# Content
''';

      final task = TaskNoteParser.parse(markdown);
      expect(task.dateCreated, equals('2026-09-04T19:00:00-05:00'));
      expect(task.due, equals('2026-09-10'));
      expect(task.scheduled, equals('2026-09-05T10:00:00-05:00'));
    });

    test('preserves custom/unmodeled frontmatter fields on round-trip serialization', () {
      const markdown = '''---
title: "Custom Fields Task"
status: todo
dateCreated: "2026-09-04T19:00:00-05:00"
created: "2026-09-04T19:00:00-05:00"
due: null
scheduled: null
priority: normal
urgency_tier: 2
modality: analytical
timeEstimate: 45
energy: medium
friction: medium
micro_chunked: false
tags:
  - task
customProperty: "keepMe"
numericCustom: 42
---

# Custom Fields Task
''';

      final task = TaskNoteParser.parse(markdown);
      expect(task.customFields['customProperty'], equals('keepMe'));
      expect(task.customFields['numericCustom'], equals(42));

      final serialized = TaskNoteParser.serialize(task);
      expect(serialized, contains('customProperty: "keepMe"'));
      expect(serialized, contains('numericCustom: 42'));

      final reparsed = TaskNoteParser.parse(serialized);
      expect(reparsed.customFields['customProperty'], equals('keepMe'));
      expect(reparsed.customFields['numericCustom'], equals(42));
    });
  });
}
