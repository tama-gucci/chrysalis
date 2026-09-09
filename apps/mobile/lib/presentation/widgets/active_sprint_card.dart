import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../domain/models/ultradian_sprint.dart';
import '../theme/app_theme.dart';

/// Hero Card for the currently active ultradian focus sprint.
class ActiveSprintCard extends StatelessWidget {
  final DiurnalBlock? activeBlock;
  final VoidCallback onComplete;
  final VoidCallback onPause;

  const ActiveSprintCard({
    super.key,
    required this.activeBlock,
    required this.onComplete,
    required this.onPause,
  });

  @override
  Widget build(BuildContext context) {
    if (activeBlock == null) {
      return Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: ChrysalisTheme.surfaceDark,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white10),
        ),
        child: const Row(
          children: [
            Icon(Icons.bedtime_outlined, color: Colors.blueGrey, size: 28),
            SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'No Sprint In Progress',
                    style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  Text(
                    'Check Diurnal Timeline below for your next scheduled window.',
                    style: TextStyle(fontSize: 12, color: Colors.white60),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    final block = activeBlock!;
    final modalityColor = ChrysalisTheme.forModality(block.modality);
    final timeFormat = DateFormat('hh:mm a');

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            modalityColor.withValues(alpha: 0.35),
            ChrysalisTheme.surfaceDark,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: modalityColor.withValues(alpha: 0.6), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: modalityColor.withValues(alpha: 0.2),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: modalityColor,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  block.sprintType.label.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.8,
                  ),
                ),
              ),
              Text(
                '${timeFormat.format(block.startTime)} – ${timeFormat.format(block.endTime)}',
                style: const TextStyle(color: Colors.white70, fontSize: 12),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            block.title,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Modality: ${block.modality.yamlValue} • ${block.durationMinutes}m Ultradian Block',
            style: TextStyle(fontSize: 13, color: Colors.white.withValues(alpha: 0.8)),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  icon: const Icon(Icons.check_circle_outline, size: 18),
                  label: const Text('Complete Session'),
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.greenAccent.shade400,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  onPressed: onComplete,
                ),
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                icon: const Icon(Icons.pause, size: 18),
                label: const Text('Pause'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white70,
                  side: const BorderSide(color: Colors.white24),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: onPause,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
