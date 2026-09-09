/// Biometric domain abstractions prepared for Google Health Connect API ingestion.
library;

enum SleepStageType {
  awake,
  light,
  deep,
  rem,
}

class SleepStageInterval {
  final SleepStageType stage;
  final DateTime startTime;
  final DateTime endTime;

  const SleepStageInterval({
    required this.stage,
    required this.startTime,
    required this.endTime,
  });

  int get durationMinutes => endTime.difference(startTime).inMinutes;
}

class SleepSession {
  final DateTime startTime;
  final DateTime endTime;
  final int deepSleepMinutes;
  final int remSleepMinutes;
  final int lightSleepMinutes;
  final int awakeMinutes;
  final double efficiencyPercent;
  final List<SleepStageInterval> intervals;

  const SleepSession({
    required this.startTime,
    required this.endTime,
    required this.deepSleepMinutes,
    required this.remSleepMinutes,
    required this.lightSleepMinutes,
    required this.awakeMinutes,
    required this.efficiencyPercent,
    this.intervals = const [],
  });

  int get totalMinutes => endTime.difference(startTime).inMinutes;
  int get restorativeSleepMinutes => deepSleepMinutes + remSleepMinutes;
}

class RestingHeartRate {
  final DateTime timestamp;
  final int bpm;

  const RestingHeartRate({
    required this.timestamp,
    required this.bpm,
  });
}

class HeartRateVariability {
  final DateTime timestamp;
  /// Root Mean Square of Successive Differences (RMSSD) in milliseconds
  final double rmssdMillis;

  const HeartRateVariability({
    required this.timestamp,
    required this.rmssdMillis,
  });
}

/// Consolidated daily biometric record.
class BiometricTelemetry {
  final DateTime date;
  final SleepSession? sleep;
  final RestingHeartRate? restingHeartRate;
  final HeartRateVariability? hrv;

  const BiometricTelemetry({
    required this.date,
    this.sleep,
    this.restingHeartRate,
    this.hrv,
  });

  /// Inferred wake time from the sleep record (or fallback to morning baseline)
  DateTime? get inferredWakeTime => sleep?.endTime;

  /// Algorithmic readiness / energy score (1 to 5) for morning calibration.
  int get computedReadinessScore {
    double score = 3.0; // Baseline normal

    if (sleep != null) {
      final hours = sleep!.totalMinutes / 60.0;
      if (hours >= 7.5) {
        score += 1.0;
      } else if (hours < 6.0) {
        score -= 1.0;
      }

      // Restorative sleep proportion
      if (sleep!.totalMinutes > 0) {
        final restorativePct = sleep!.restorativeSleepMinutes / sleep!.totalMinutes;
        if (restorativePct > 0.40) {
          score += 0.5;
        } else if (restorativePct < 0.20) {
          score -= 0.5;
        }
      }
    }

    if (hrv != null) {
      if (hrv!.rmssdMillis >= 65) {
        score += 0.5;
      } else if (hrv!.rmssdMillis < 35) {
        score -= 0.5;
      }
    }

    if (restingHeartRate != null) {
      if (restingHeartRate!.bpm < 60) {
        score += 0.5;
      } else if (restingHeartRate!.bpm > 75) {
        score -= 0.5;
      }
    }

    return score.round().clamp(1, 5);
  }

  String get readinessReasoning {
    final parts = <String>[];
    if (sleep != null) {
      final hrs = (sleep!.totalMinutes / 60).toStringAsFixed(1);
      parts.add('Sleep: ${hrs}h (${sleep!.efficiencyPercent.toStringAsFixed(0)}% eff)');
    }
    if (hrv != null) {
      parts.add('HRV: ${hrv!.rmssdMillis.toStringAsFixed(0)}ms');
    }
    if (restingHeartRate != null) {
      parts.add('RHR: ${restingHeartRate!.bpm}bpm');
    }
    if (parts.isEmpty) {
      return 'No biometric data available; default baseline applied.';
    }
    return parts.join(' • ');
  }
}
