import '../models/biometrics.dart';
export 'health_connect_platform_channel_data_source.dart';

/// Contract for biometric telemetry ingestion (Google Health Connect API abstraction).
abstract class BiometricDataSource {
  String get providerName;

  /// Checks whether Health Connect is supported and installed on this device.
  Future<bool> isAvailable();

  /// Checks whether the user has granted read permissions for Sleep, Heart Rate, and HRV.
  Future<bool> hasPermissions();

  /// Prompts the Android OS Health Connect permission screen.
  Future<bool> requestPermissions();

  /// Fetches aggregated telemetry for the given date (defaults to today).
  Future<BiometricTelemetry> getTelemetryForDate(DateTime date);
}

/// Standalone mock implementation for headless environments, testing, and iOS/Desktop fallbacks.
class MockHealthConnectDataSource implements BiometricDataSource {
  bool _hasPermission = true;

  @override
  String get providerName => 'Google Health Connect (Simulated)';

  @override
  Future<bool> isAvailable() async => true;

  @override
  Future<bool> hasPermissions() async => _hasPermission;

  @override
  Future<bool> requestPermissions() async {
    _hasPermission = true;
    return true;
  }

  @override
  Future<BiometricTelemetry> getTelemetryForDate(DateTime date) async {
    final wakeTime = DateTime(date.year, date.month, date.day, 7, 45);
    final sleepStartTime = wakeTime.subtract(const Duration(hours: 7, minutes: 45));

    final sleep = SleepSession(
      startTime: sleepStartTime,
      endTime: wakeTime,
      deepSleepMinutes: 110,
      remSleepMinutes: 95,
      lightSleepMinutes: 240,
      awakeMinutes: 20,
      efficiencyPercent: 91.5,
      intervals: [
        SleepStageInterval(
          stage: SleepStageType.light,
          startTime: sleepStartTime,
          endTime: sleepStartTime.add(const Duration(minutes: 60)),
        ),
        SleepStageInterval(
          stage: SleepStageType.deep,
          startTime: sleepStartTime.add(const Duration(minutes: 60)),
          endTime: sleepStartTime.add(const Duration(minutes: 170)),
        ),
        SleepStageInterval(
          stage: SleepStageType.rem,
          startTime: sleepStartTime.add(const Duration(minutes: 170)),
          endTime: wakeTime,
        ),
      ],
    );

    final rhr = RestingHeartRate(
      timestamp: wakeTime.subtract(const Duration(minutes: 30)),
      bpm: 54,
    );

    final hrv = HeartRateVariability(
      timestamp: wakeTime.subtract(const Duration(minutes: 15)),
      rmssdMillis: 68.0,
    );

    return BiometricTelemetry(
      date: date,
      sleep: sleep,
      restingHeartRate: rhr,
      hrv: hrv,
    );
  }
}
