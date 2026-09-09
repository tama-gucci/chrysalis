/// Timezone handling for Chrysalis.
///
/// System Invariant: All frontmatter ISO timestamps must strictly serialize
/// with the explicit local timezone offset defined in Scheduling-Memory.md
/// (default: "-05:00"). Never write raw UTC "Z" strings.
class TimezoneUtils {
  static const String defaultTimezoneOffset = '-05:00';

  /// Regex matching ISO 8601 timestamps with an explicit offset (+/-HH:mm or +/-HHmm)
  static final RegExp _explicitOffsetPattern = RegExp(
    r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?([+-][0-9]{2}:?[0-9]{2})$',
  );

  /// Checks whether an ISO string includes an explicit non-Z timezone offset.
  static bool hasExplicitTimezoneOffset(String timestamp) {
    return _explicitOffsetPattern.hasMatch(timestamp.trim());
  }

  /// Formats a [DateTime] with an explicit timezone offset string (e.g. "-05:00").
  /// Replaces raw 'Z' with the local offset.
  static String formatIsoWithOffset(
    DateTime dateTime, {
    String offset = defaultTimezoneOffset,
  }) {
    final cleanOffset = normalizeOffset(offset);
    final isNegative = cleanOffset.startsWith('-');
    final parts = cleanOffset.substring(1).split(':');
    final offsetHours = int.parse(parts[0]);
    final offsetMinutes = parts.length > 1 ? int.parse(parts[1]) : 0;
    final totalOffsetMinutes = (offsetHours * 60 + offsetMinutes) * (isNegative ? -1 : 1);

    // Convert to UTC first to avoid local DST anomalies and platform differences
    final utc = dateTime.toUtc();
    final targetDt = utc.add(Duration(minutes: totalOffsetMinutes));

    final year = targetDt.year.toString().padLeft(4, '0');
    final month = targetDt.month.toString().padLeft(2, '0');
    final day = targetDt.day.toString().padLeft(2, '0');
    final hour = targetDt.hour.toString().padLeft(2, '0');
    final minute = targetDt.minute.toString().padLeft(2, '0');
    final second = targetDt.second.toString().padLeft(2, '0');

    return '$year-$month-${day}T$hour:$minute:$second$cleanOffset';
  }

  /// Normalizes an offset string (e.g. "-0500" -> "-05:00", "-5" -> "-05:00").
  static String normalizeOffset(String offset) {
    final trimmed = offset.trim();
    if (trimmed == 'Z' || trimmed == 'z') {
      return defaultTimezoneOffset;
    }
    if (RegExp(r'^[+-]\d{2}:\d{2}$').hasMatch(trimmed)) {
      return trimmed;
    }
    if (RegExp(r'^[+-]\d{4}$').hasMatch(trimmed)) {
      return '${trimmed.substring(0, 3)}:${trimmed.substring(3, 5)}';
    }
    return defaultTimezoneOffset;
  }

  /// Parses an ISO 8601 string and ensures it has an explicit offset.
  /// Throws [FormatException] if [strict] is true and a raw 'Z' or no offset is found.
  static DateTime parseIsoWithOffset(String isoString, {bool strict = true}) {
    final trimmed = isoString.trim();
    if (trimmed.endsWith('Z') || trimmed.endsWith('z')) {
      if (strict) {
        throw FormatException(
          'Chrysalis Invariant Violation: raw UTC "Z" timestamp rejected: "$isoString". '
          'Explicit local offset (e.g. $defaultTimezoneOffset) is required.',
        );
      }
    }

    if (strict && !_explicitOffsetPattern.hasMatch(trimmed)) {
      throw FormatException(
        'Chrysalis Invariant Violation: timestamp missing explicit offset: "$isoString". '
        'Expected format YYYY-MM-DDTHH:mm:ss-05:00',
      );
    }

    return DateTime.parse(trimmed);
  }

  /// Returns today's date formatted as YYYY-MM-DD.
  static String todayDateString([DateTime? dt]) {
    final now = dt ?? DateTime.now();
    final year = now.year.toString().padLeft(4, '0');
    final month = now.month.toString().padLeft(2, '0');
    final day = now.day.toString().padLeft(2, '0');
    return '$year-$month-$day';
  }
}
