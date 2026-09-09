import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/core/exceptions/app_exceptions.dart';
import 'package:chrysalis_mobile/domain/models/biometrics.dart';
import 'package:chrysalis_mobile/domain/services/health_connect_platform_channel_data_source.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('HealthConnectPlatformChannelDataSource Tests', () {
    const channelName = 'org.chrysalis.mobile/health_connect';
    const channel = MethodChannel(channelName);
    late HealthConnectPlatformChannelDataSource dataSource;

    setUp(() {
      dataSource = HealthConnectPlatformChannelDataSource(channel: channel);
    });

    tearDown(() {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null);
    });

    test('isAvailable returns boolean from platform channel', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'isAvailable') return true;
        return null;
      });

      expect(await dataSource.isAvailable(), isTrue);

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'isAvailable') return false;
        return null;
      });

      expect(await dataSource.isAvailable(), isFalse);
    });

    test('hasPermissions and requestPermissions return boolean from channel', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'hasPermissions') return true;
        if (methodCall.method == 'requestPermissions') return true;
        return null;
      });

      expect(await dataSource.hasPermissions(), isTrue);
      expect(await dataSource.requestPermissions(), isTrue);
    });

    test('getTelemetryForDate correctly parses sleep stages, RHR, and HRV', () async {
      final targetDate = DateTime(2026, 9, 4);

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        if (methodCall.method == 'getTelemetryForDate') {
          return <String, dynamic>{
            'sleep': <String, dynamic>{
              'startTime': '2026-09-03T23:30:00.000',
              'endTime': '2026-09-04T07:15:00.000',
              'deepSleepMinutes': 105,
              'remSleepMinutes': 90,
              'lightSleepMinutes': 250,
              'awakeMinutes': 20,
              'efficiencyPercent': 92.5,
              'intervals': [
                {
                  'stage': 'light',
                  'startTime': '2026-09-03T23:30:00.000',
                  'endTime': '2026-09-04T00:30:00.000',
                },
                {
                  'stage': 'deep',
                  'startTime': '2026-09-04T00:30:00.000',
                  'endTime': '2026-09-04T02:15:00.000',
                },
                {
                  'stage': 'rem',
                  'startTime': '2026-09-04T02:15:00.000',
                  'endTime': '2026-09-04T03:45:00.000',
                },
                {
                  'stage': 'awake',
                  'startTime': '2026-09-04T03:45:00.000',
                  'endTime': '2026-09-04T04:05:00.000',
                },
              ],
            },
            'restingHeartRate': <String, dynamic>{
              'timestamp': '2026-09-04T06:45:00.000',
              'bpm': 52,
            },
            'hrv': <String, dynamic>{
              'timestamp': '2026-09-04T07:00:00.000',
              'rmssdMillis': 74.5,
            },
          };
        }
        return null;
      });

      final telemetry = await dataSource.getTelemetryForDate(targetDate);
      expect(telemetry.date, equals(targetDate));
      expect(telemetry.sleep, isNotNull);
      expect(telemetry.sleep!.deepSleepMinutes, equals(105));
      expect(telemetry.sleep!.remSleepMinutes, equals(90));
      expect(telemetry.sleep!.lightSleepMinutes, equals(250));
      expect(telemetry.sleep!.awakeMinutes, equals(20));
      expect(telemetry.sleep!.efficiencyPercent, equals(92.5));
      expect(telemetry.sleep!.intervals.length, equals(4));
      expect(telemetry.sleep!.intervals[1].stage, equals(SleepStageType.deep));
      expect(telemetry.sleep!.intervals[2].stage, equals(SleepStageType.rem));
      expect(telemetry.sleep!.intervals[3].stage, equals(SleepStageType.awake));

      expect(telemetry.restingHeartRate?.bpm, equals(52));
      expect(telemetry.hrv?.rmssdMillis, equals(74.5));
      expect(telemetry.inferredWakeTime, equals(DateTime(2026, 9, 4, 7, 15)));

      // Algorithmic readiness check: 7.75h sleep + >40% restorative + HRV >= 65 + RHR < 60 -> Score 5
      expect(telemetry.computedReadinessScore, equals(5));
      expect(telemetry.readinessReasoning, contains('Sleep: 7.8h (93% eff)'));
      expect(telemetry.readinessReasoning, contains('HRV: 75ms'));
      expect(telemetry.readinessReasoning, contains('RHR: 52bpm'));
    });

    test('getTelemetryForDate handles partial data with missing records', () async {
      final targetDate = DateTime(2026, 9, 4);

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        return <String, dynamic>{
          'sleep': <String, dynamic>{
            'startTime': '2026-09-04T00:00:00.000',
            'endTime': '2026-09-04T06:00:00.000',
            'deepSleepMinutes': 60,
            'remSleepMinutes': 60,
            'lightSleepMinutes': 220,
            'awakeMinutes': 20,
            'efficiencyPercent': 88.0,
            'intervals': [],
          },
          // RHR and HRV omitted
        };
      });

      final telemetry = await dataSource.getTelemetryForDate(targetDate);
      expect(telemetry.sleep, isNotNull);
      expect(telemetry.restingHeartRate, isNull);
      expect(telemetry.hrv, isNull);
      expect(telemetry.computedReadinessScore, isNotNull);
    });

    test('getTelemetryForDate throws BiometricsException on platform exception', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
        throw PlatformException(code: 'UNAVAILABLE', message: 'Health Connect is not installed');
      });

      expect(
        () => dataSource.getTelemetryForDate(DateTime(2026, 9, 4)),
        throwsA(isA<BiometricsException>()),
      );
    });
  });
}
