import 'package:flutter/material.dart';
import '../../domain/models/cognitive_modality.dart';
import '../../domain/models/task_status.dart';

/// Chrysalis Material 3 Theme & Cognitive Modality Palette.
class ChrysalisTheme {
  // Brand accent colors
  static const Color primaryTeal = Color(0xFF00B4D8);
  static const Color primaryDark = Color(0xFF0F172A);
  static const Color surfaceDark = Color(0xFF1E293B);

  // Modality Colors
  static const Color modalityAnalytical = Color(0xFF6366F1); // Indigo
  static const Color modalityKinetic = Color(0xFFF59E0B);    // Amber
  static const Color modalitySynthesis = Color(0xFF10B981);  // Emerald
  static const Color modalityAdministrative = Color(0xFF64748B); // Slate

  // Status Colors
  static const Color statusTodo = Color(0xFF94A3B8);
  static const Color statusInProgress = Color(0xFF38BDF8);
  static const Color statusDone = Color(0xFF22C55E);
  static const Color statusArchived = Color(0xFF475569);

  static Color forModality(CognitiveModality modality) {
    switch (modality) {
      case CognitiveModality.analytical:
        return modalityAnalytical;
      case CognitiveModality.kinetic:
        return modalityKinetic;
      case CognitiveModality.synthesis:
        return modalitySynthesis;
      case CognitiveModality.administrative:
        return modalityAdministrative;
    }
  }

  static Color forStatus(TaskStatus status) {
    switch (status) {
      case TaskStatus.todo:
        return statusTodo;
      case TaskStatus.inProgress:
        return statusInProgress;
      case TaskStatus.done:
        return statusDone;
      case TaskStatus.archived:
        return statusArchived;
    }
  }

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryTeal,
        brightness: Brightness.dark,
        surface: surfaceDark,
      ),
      scaffoldBackgroundColor: primaryDark,
      cardTheme: const CardThemeData(
        color: surfaceDark,
        elevation: 2,
        margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: primaryDark,
        elevation: 0,
        centerTitle: false,
      ),
    );
  }
}
