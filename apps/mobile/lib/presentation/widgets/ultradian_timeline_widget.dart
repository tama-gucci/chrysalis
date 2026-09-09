import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../domain/models/ultradian_sprint.dart';
import '../theme/app_theme.dart';

/// Diurnal Ultradian Timeline Widget.
///
/// Renders 75-90m focus sprints and 15m decompression buffers with
/// bio-cognitive modality coloring and active progress tracking.
class UltradianTimelineWidget extends StatelessWidget {
  final DiurnalSchedule schedule;
  final ValueChanged<DiurnalBlock>? onBlockTapped;
  final ValueChanged<DiurnalBlock>? onBlockCompleted;

  const UltradianTimelineWidget({
    super.key,
    required this.schedule,
    this.onBlockTapped,
    this.onBlockCompleted,
  });

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final timeFormat = DateFormat('hh:mm a');

    if (schedule.blocks.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32.0),
          child: Text(
            'No diurnal blocks scheduled.\nTap Morning Calibration to generate today\'s sprint blocks.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white60),
          ),
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: schedule.blocks.length,
      itemBuilder: (context, index) {
        final block = schedule.blocks[index];
        final isCurrent = block.isCurrent(now);
        final isPast = block.isPast(now);
        final modalityColor = ChrysalisTheme.forModality(block.modality);
        final isBuffer = block.sprintType == SprintType.decompression;

        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          color: isCurrent
              ? modalityColor.withValues(alpha: 0.18)
              : (isBuffer ? Colors.white.withValues(alpha: 0.04) : ChrysalisTheme.surfaceDark),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: isCurrent
                ? BorderSide(color: modalityColor, width: 2)
                : BorderSide(
                    color: isBuffer ? Colors.white10 : Colors.white12,
                    width: 1,
                  ),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Row(
              children: [
                // Time window column
                SizedBox(
                  width: 75,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        timeFormat.format(block.startTime),
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: isCurrent ? modalityColor : Colors.white70,
                        ),
                      ),
                      Text(
                        timeFormat.format(block.endTime),
                        style: const TextStyle(
                          fontSize: 11,
                          color: Colors.white38,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${block.durationMinutes}m',
                        style: TextStyle(
                          fontSize: 10,
                          color: isCurrent ? Colors.tealAccent : Colors.grey,
                        ),
                      ),
                    ],
                  ),
                ),

                // Vertical Divider
                Container(
                  width: 3,
                  height: 44,
                  margin: const EdgeInsets.symmetric(horizontal: 10),
                  decoration: BoxDecoration(
                    color: isBuffer ? Colors.grey.shade700 : modalityColor,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),

                // Title & Modality Info
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          if (isCurrent) ...[
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              margin: const EdgeInsets.only(right: 6),
                              decoration: BoxDecoration(
                                color: Colors.tealAccent.shade400,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: const Text(
                                'ACTIVE',
                                style: TextStyle(
                                  color: Colors.black,
                                  fontSize: 9,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ),
                          ],
                          Flexible(
                            child: Text(
                              block.title,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: isCurrent ? FontWeight.bold : FontWeight.w500,
                                color: isPast ? Colors.white54 : Colors.white,
                                decoration: block.isCompleted ? TextDecoration.lineThrough : null,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        isBuffer
                            ? '15m Reset & Decompression'
                            : '${block.sprintType.label} • ${block.modality.yamlValue.toUpperCase()}',
                        style: TextStyle(
                          fontSize: 11,
                          color: isBuffer ? Colors.grey : modalityColor.withValues(alpha: 0.9),
                        ),
                      ),
                    ],
                  ),
                ),

                // Action Checkbox
                if (!isBuffer) ...[
                  IconButton(
                    icon: Icon(
                      block.isCompleted
                          ? Icons.check_circle
                          : (isPast ? Icons.history : Icons.radio_button_unchecked),
                      color: block.isCompleted ? Colors.greenAccent : Colors.white38,
                    ),
                    onPressed: () => onBlockCompleted?.call(block),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
