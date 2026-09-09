import 'package:flutter/services.dart';
import '../../core/exceptions/app_exceptions.dart';
import '../models/biometrics.dart';
import 'biometric_service.dart';

/// Platform channel implementation of [BiometricDataSource] connecting to Android Health Connect.
///
/// Communicates with native Android Kotlin code via the MethodChannel `org.chrysalis.mobile/health_connect`
/// to read sleep sessions, stages, resting heart rate, and heart rate variability (HRV RMSSD).
class HealthConnectPlatformChannelDataSource implements BiometricDataSource {
  final MethodChannel _channel;

  HealthConnectPlatformChannelDataSource({MethodChannel? channel})
      : _channel = channel ?? const MethodChannel('org.chrysalis.mobile/health_connect');

  @override
  String get providerName => 'Android Health Connect';

  @override
  Future<bool> isAvailable() async {
    try {
      final available = await _channel.invokeMethod<bool>('isAvailable');
      return available ?? false;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> hasPermissions() async {
    try {
      final granted = await _channel.invokeMethod<bool>('hasPermissions');
      return granted ?? false;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> requestPermissions() async {
    try {
      final granted = await _channel.invokeMethod<bool>('requestPermissions');
      return granted ?? false;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<BiometricTelemetry> getTelemetryForDate(DateTime date) async {
    try {
      final response = await _channel.invokeMapMethod<String, dynamic>(
        'getTelemetryForDate',
        {
          'date': date.toIso8601String(),
          'dateEpochMs': date.millisecondsSinceEpoch,
        },
      );

      if (response == null) {
        return BiometricTelemetry(date: date);
      }

      SleepSession? sleepSession;
      final sleepMap = response['sleep'] as Map<dynamic, dynamic>?;
      if (sleepMap != null) {
        final start = DateTime.parse(sleepMap['startTime'] as String);
        final end = DateTime.parse(sleepMap['endTime'] as String);
        final deep = (sleepMap['deepSleepMinutes'] as num?)?.toInt() ?? 0;
        final rem = (sleepMap['remSleepMinutes'] as num?)?.toInt() ?? 0;
        final light = (sleepMap['lightSleepMinutes'] as num?)?.toInt() ?? 0;
        final awake = (sleepMap['awakeMinutes'] as num?)?.toInt() ?? 0;
        final efficiency = (sleepMap['efficiencyPercent'] as num?)?.toDouble() ?? 0.0;

        final rawIntervals = sleepMap['intervals'] as List<dynamic>? ?? [];
        final intervals = <SleepStageInterval>[];

        for (final raw in rawIntervals) {
          if (raw is Map) {
            final stageStr = (raw['stage'] as String? ?? 'light').toLowerCase();
            final stage = _parseSleepStage(stageStr);
            final stageStart = DateTime.parse(raw['startTime'] as String);
            final stageEnd = DateTime.parse(raw['endTime'] as String);

            intervals.add(SleepStageInterval(
              stage: stage,
              startTime: stageStart,
              endTime: stageEnd,
            ));
          }
        }

        sleepSession = SleepSession(
          startTime: start,
          endTime: end,
          deepSleepMinutes: deep,
          remSleepMinutes: rem,
          lightSleepMinutes: light,
          awakeMinutes: awake,
          efficiencyPercent: efficiency,
          intervals: intervals,
        );
      }

      RestingHeartRate? restingHeartRate;
      final rhrMap = response['restingHeartRate'] as Map<dynamic, dynamic>?;
      if (rhrMap != null) {
        final timestamp = DateTime.parse(rhrMap['timestamp'] as String);
        final bpm = (rhrMap['bpm'] as num).toInt();
        restingHeartRate = RestingHeartRate(timestamp: timestamp, bpm: bpm);
      }

      HeartRateVariability? hrv;
      final hrvMap = response['hrv'] as Map<dynamic, dynamic>?;
      if (hrvMap != null) {
        final timestamp = DateTime.parse(hrvMap['timestamp'] as String);
        final rmssd = (hrvMap['rmssdMillis'] as num).toDouble();
        hrv = HeartRateVariability(timestamp: timestamp, rmssdMillis: rmssd);
      }

      return BiometricTelemetry(
        date: date,
        sleep: sleepSession,
        restingHeartRate: restingHeartRate,
        hrv: hrv,
      );
    } on PlatformException catch (e) {
      throw BiometricsException('Platform channel error querying Health Connect: ${e.message}', e);
    } catch (e) {
      throw BiometricsException('Failed to process biometric telemetry: $e', e);
    }
  }

  SleepStageType _parseSleepStage(String stage) {
    switch (stage) {
      case 'awake':
      case 'out_of_bed':
        return SleepStageType.awake;
      case 'deep':
        return SleepStageType.deep;
      case 'rem':
        return SleepStageType.rem;
      case 'light':
      default:
        return SleepStageType.light;
    }
  }
}
