import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../domain/models/biometrics.dart';
import '../theme/app_theme.dart';

/// Interactive Morning Calibration Sheet (/calibrate).
///
/// Ingests morning wake timestamp and energy telemetry (1-5),
/// displays Health Connect biometric insights, and shifts diurnal windows.
class MorningCalibrationSheet extends StatefulWidget {
  final DateTime initialWakeTime;
  final int initialEnergy;
  final BiometricTelemetry? biometrics;
  final void Function(DateTime wakeTime, int energy) onCalibrate;

  const MorningCalibrationSheet({
    super.key,
    required this.initialWakeTime,
    this.initialEnergy = 3,
    this.biometrics,
    required this.onCalibrate,
  });

  @override
  State<MorningCalibrationSheet> createState() => _MorningCalibrationSheetState();
}

class _MorningCalibrationSheetState extends State<MorningCalibrationSheet> {
  late DateTime _wakeTime;
  late double _energy;

  @override
  void initState() {
    super.initState();
    _wakeTime = widget.initialWakeTime;
    _energy = widget.initialEnergy.toDouble();

    // Auto-populate from biometric data if available
    if (widget.biometrics?.inferredWakeTime != null) {
      _wakeTime = widget.biometrics!.inferredWakeTime!;
      _energy = widget.biometrics!.computedReadinessScore.toDouble();
    }
  }

  String _getEnergyDescription(int score) {
    switch (score) {
      case 1:
        return '1 • Low Energy (Rest & Semantic Pause Recommended)';
      case 2:
        return '2 • Sluggish (Defrost first, Kinetic Focus)';
      case 3:
        return '3 • Baseline Focus (Standard 75m Ultradian Sprints)';
      case 4:
        return '4 • Optimal Flow (Analytical Stacking, High Output)';
      case 5:
        return '5 • Hyper-Peak Focus (90m Analytical Deep Work)';
      default:
        return '$score • Normal';
    }
  }

  Future<void> _selectWakeTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_wakeTime),
    );
    if (picked != null) {
      setState(() {
        _wakeTime = DateTime(
          _wakeTime.year,
          _wakeTime.month,
          _wakeTime.day,
          picked.hour,
          picked.minute,
        );
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final timeFormat = DateFormat('hh:mm a');
    final biometrics = widget.biometrics;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: const BoxDecoration(
        color: ChrysalisTheme.surfaceDark,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.wb_sunny_outlined, color: Colors.amber, size: 24),
                  SizedBox(width: 8),
                  Text(
                    'Morning Calibration (/calibrate)',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
              IconButton(
                icon: const Icon(Icons.close, color: Colors.grey),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Biometrics Card (Google Health Connect Ingestion)
          if (biometrics != null) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.teal.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.teal.withValues(alpha: 0.4)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.favorite, color: Colors.tealAccent, size: 16),
                      const SizedBox(width: 6),
                      Text(
                        'Health Connect Telemetry Ingested',
                        style: TextStyle(
                          color: Colors.tealAccent.shade100,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    biometrics.readinessReasoning,
                    style: const TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Wake Time Selector
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.alarm, color: ChrysalisTheme.primaryTeal),
            title: const Text('Wake Timestamp', style: TextStyle(color: Colors.white)),
            subtitle: Text(
              '${timeFormat.format(_wakeTime)} (Local -05:00)',
              style: const TextStyle(color: Colors.white70),
            ),
            trailing: OutlinedButton(
              onPressed: _selectWakeTime,
              child: const Text('Change'),
            ),
          ),

          const SizedBox(height: 12),

          // Energy Rating Slider
          Text(
            'Energy Score: ${_energy.round()}',
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            _getEnergyDescription(_energy.round()),
            style: TextStyle(
              fontSize: 12,
              color: Colors.amber.shade200,
            ),
          ),
          Slider(
            value: _energy,
            min: 1,
            max: 5,
            divisions: 4,
            activeColor: Colors.amber,
            onChanged: (val) {
              setState(() {
                _energy = val;
              });
            },
          ),

          const SizedBox(height: 20),

          // Calibrate Today Action Button
          FilledButton.icon(
            icon: const Icon(Icons.check_circle_outline),
            label: const Text('Calibrate Today & Lock Sprints'),
            style: FilledButton.styleFrom(
              backgroundColor: ChrysalisTheme.primaryTeal,
              foregroundColor: Colors.black,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: () {
              widget.onCalibrate(_wakeTime, _energy.round());
              Navigator.of(context).pop();
            },
          ),
        ],
      ),
    );
  }
}
