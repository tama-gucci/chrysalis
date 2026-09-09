import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/domain/models/cognitive_modality.dart';
import 'package:chrysalis_mobile/domain/models/task_priority.dart';
import 'package:chrysalis_mobile/domain/parser/task_shorthand_parser.dart';

void main() {
  group('TaskShorthandParser', () {
    test('parses full shorthand string with all tokens', () {
      const input = 'Write grant proposal #pillar-1/grants ~75m !3 @analytical';
      final parsed = TaskShorthandParser.parse(input);

      expect(parsed.title, equals('Write grant proposal'));
      expect(parsed.tags, containsAll(['task', 'pillar-1/grants']));
      expect(parsed.durationMinutes, equals(75));
      expect(parsed.urgencyTier, equals(3));
      expect(parsed.priority, equals(TaskPriority.high));
      expect(parsed.modality, equals(CognitiveModality.analytical));
    });

    test('handles hour duration syntax (~1.5h, ~2h)', () {
      final parsed1 = TaskShorthandParser.parse('Deep coding ~1.5h');
      expect(parsed1.durationMinutes, equals(90));

      final parsed2 = TaskShorthandParser.parse('Architecture review ~2h');
      expect(parsed2.durationMinutes, equals(120));
    });

    test('parses kinetic and synthesis modalities', () {
      final kinetic = TaskShorthandParser.parse('Clean workshop @kinetic ~30m');
      expect(kinetic.modality, equals(CognitiveModality.kinetic));

      final synthesis = TaskShorthandParser.parse('Monthly review @synthesis ~60m');
      expect(synthesis.modality, equals(CognitiveModality.synthesis));

      final admin = TaskShorthandParser.parse('File expenses @admin ~15m');
      expect(admin.modality, equals(CognitiveModality.administrative));
    });

    test('parses urgency tiers 1 to 4 and textual priorities', () {
      final t4 = TaskShorthandParser.parse('Critical bug fix !4');
      expect(t4.urgencyTier, equals(4));
      expect(t4.priority, equals(TaskPriority.urgent));

      final t1 = TaskShorthandParser.parse('Someday read book !low');
      expect(t1.urgencyTier, equals(1));
      expect(t1.priority, equals(TaskPriority.low));
    });

    test('applies safe defaults when tokens are omitted', () {
      final parsed = TaskShorthandParser.parse('Just a simple task title');
      expect(parsed.title, equals('Just a simple task title'));
      expect(parsed.durationMinutes, equals(45));
      expect(parsed.urgencyTier, equals(2));
      expect(parsed.priority, equals(TaskPriority.normal));
      expect(parsed.modality, equals(CognitiveModality.analytical));
      expect(parsed.tags, equals(['task']));
    });

    test('converts ParsedShorthand directly into a valid TaskNote', () {
      final parsed = TaskShorthandParser.parse('Build Flutter App #dev/mobile ~90m !4 @analytical');
      final task = parsed.toTaskNote(dueDate: '2026-09-10');

      expect(task.title, equals('Build Flutter App'));
      expect(task.timeEstimate, equals(90));
      expect(task.urgencyTier, equals(4));
      expect(task.priority, equals(TaskPriority.urgent));
      expect(task.due, equals('2026-09-10'));
      expect(task.tags, containsAll(['task', 'dev/mobile']));
    });

    test('preserves issue numbers and embedded language symbols in title', () {
      final parsed = TaskShorthandParser.parse('Fix issue #123 in repo and master C# #pillar-1/dev ~30m');
      expect(parsed.title, equals('Fix issue #123 in repo and master C#'));
      expect(parsed.tags, containsAll(['task', 'pillar-1/dev']));
      expect(parsed.tags.contains('123'), isFalse);
      expect(parsed.durationMinutes, equals(30));
    });
  });
}
