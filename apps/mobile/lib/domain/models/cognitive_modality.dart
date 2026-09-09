/// Cognitive modality for bio-cognitive alignment and ultradian stacking.
enum CognitiveModality {
  analytical('analytical', 'Deep focus, logical analysis, research & code'),
  kinetic('kinetic', 'Physical execution, manual workflows, post-lunch slump defrost'),
  synthesis('synthesis', 'Holistic evaluation, creative writing, architectural review'),
  administrative('administrative', 'Logistics, email, organization, low-energy buffering');

  final String yamlValue;
  final String description;

  const CognitiveModality(this.yamlValue, this.description);

  static CognitiveModality fromString(String raw) {
    final normalized = raw.trim().toLowerCase();
    switch (normalized) {
      case 'analytical':
        return CognitiveModality.analytical;
      case 'kinetic':
        return CognitiveModality.kinetic;
      case 'synthesis':
        return CognitiveModality.synthesis;
      case 'administrative':
        return CognitiveModality.administrative;
      default:
        return CognitiveModality.analytical;
    }
  }

  /// Suggested diurnal window
  String get optimalWindow {
    switch (this) {
      case CognitiveModality.analytical:
        return 'Morning / Peak Focus Sprints';
      case CognitiveModality.kinetic:
        return 'Slump / Defrost Window (Early Afternoon)';
      case CognitiveModality.synthesis:
        return 'Late Afternoon / Recovery Horizon';
      case CognitiveModality.administrative:
        return 'Buffer Windows / Low Energy Slump';
    }
  }
}
