import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/domain/models/biometrics.dart';
import 'package:chrysalis_mobile/domain/services/biometric_service.dart';

void main() {
  group('Biometric Domain & Health Connect Ingestion', () {
    test('computes sleep restorative minutes and efficiency', () {
      final start = DateTime(2026, 9, 4, 23, 0);
      final end = DateTime(2026, 9, 5, 7, 0);

      final sleep = SleepSession(
        startTime: start,
        endTime: end,
        deepSleepMinutes: 100,
        remSleepMinutes: 90,
        lightSleepMinutes: 250,
        awakeMinutes: 40,
        efficiencyPercent: 88.0,
      );

      expect(sleep.totalMinutes, equals(480)); // 8 hours
      expect(sleep.restorativeSleepMinutes, equals(190)); // 100 + 90
    });

    test('computes readiness score 4-5 for optimal sleep, low RHR, and high HRV', () {
      final start = DateTime(2026, 9, 4, 23, 0);
      final end = DateTime(2026, 9, 5, 7, 30);

      final telemetry = BiometricTelemetry(
        date: DateTime(2026, 9, 5),
        sleep: SleepSession(
          startTime: start,
          endTime: end,
          deepSleepMinutes: 120,
          remSleepMinutes: 100,
          lightSleepMinutes: 270,
          awakeMinutes: 20,
          efficiencyPercent: 94.0,
        ),
        restingHeartRate: RestingHeartRate(
          timestamp: end,
          bpm: 52,
        ),
        hrv: HeartRateVariability(
          timestamp: end,
          rmssdMillis: 72.0,
        ),
      );

      expect(telemetry.inferredWakeTime, equals(end));
      expect(telemetry.computedReadinessScore, greaterThanOrEqualTo(4));
      expect(telemetry.readinessReasoning, contains('Sleep: 8.5h'));
      expect(telemetry.readinessReasoning, contains('HRV: 72ms'));
      expect(telemetry.readinessReasoning, contains('RHR: 52bpm'));
    });

    test('MockHealthConnectDataSource returns valid telemetry', () async {
      final source = MockHealthConnectDataSource();
      expect(await source.isAvailable(), isTrue);
      expect(await source.hasPermissions(), isTrue);

      final data = await source.getTelemetryForDate(DateTime(2026, 9, 5));
      expect(data.sleep, isNotNull);
      expect(data.restingHeartRate, isNotNull);
      expect(data.hrv, isNotNull);
      expect(data.computedReadinessScore, inInclusiveRange(1, 5));
    });
  });
}
