/// Task priority values in Chrysalis.
enum TaskPriority {
  urgent('urgent', 4),
  high('high', 3),
  normal('normal', 2),
  low('low', 1),
  none('none', 0);

  final String yamlValue;
  final int defaultUrgencyTier;

  const TaskPriority(this.yamlValue, this.defaultUrgencyTier);

  static TaskPriority fromString(String raw) {
    final normalized = raw.trim().toLowerCase();
    switch (normalized) {
      case 'urgent':
        return TaskPriority.urgent;
      case 'high':
        return TaskPriority.high;
      case 'normal':
        return TaskPriority.normal;
      case 'low':
        return TaskPriority.low;
      case 'none':
        return TaskPriority.none;
      default:
        return TaskPriority.normal;
    }
  }
}
