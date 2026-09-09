/// Energy requirement level.
enum EnergyLevel {
  high('high'),
  medium('medium'),
  low('low');

  final String yamlValue;
  const EnergyLevel(this.yamlValue);

  static EnergyLevel fromString(String raw) {
    final normalized = raw.trim().toLowerCase();
    switch (normalized) {
      case 'high':
        return EnergyLevel.high;
      case 'medium':
        return EnergyLevel.medium;
      case 'low':
        return EnergyLevel.low;
      default:
        return EnergyLevel.medium;
    }
  }
}

/// Friction rating for task initiation.
enum FrictionLevel {
  high('high'),
  medium('medium'),
  low('low');

  final String yamlValue;
  const FrictionLevel(this.yamlValue);

  static FrictionLevel fromString(String raw) {
    final normalized = raw.trim().toLowerCase();
    switch (normalized) {
      case 'high':
        return FrictionLevel.high;
      case 'medium':
        return FrictionLevel.medium;
      case 'low':
        return FrictionLevel.low;
      default:
        return FrictionLevel.medium;
    }
  }
}
