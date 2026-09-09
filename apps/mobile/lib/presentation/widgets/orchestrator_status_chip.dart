import 'package:flutter/material.dart';
import '../../transport/orchestrator_transport.dart';

/// App Bar Chip indicating Hybrid Engine status (Ambient Gateway vs Substrate Mailbox).
class OrchestratorStatusChip extends StatelessWidget {
  final TransportConnectionState state;
  final VoidCallback onTap;

  const OrchestratorStatusChip({
    super.key,
    required this.state,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final Color dotColor;
    final String label;

    switch (state) {
      case TransportConnectionState.connectedGateway:
        dotColor = Colors.greenAccent;
        label = 'Ambient Gateway';
        break;
      case TransportConnectionState.bufferingMailbox:
        dotColor = Colors.amberAccent;
        label = 'Substrate Mailbox';
        break;
      case TransportConnectionState.connecting:
        dotColor = Colors.blueAccent;
        label = 'Connecting...';
        break;
      case TransportConnectionState.disconnected:
        dotColor = Colors.redAccent;
        label = 'Offline';
        break;
    }

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: dotColor.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: dotColor.withValues(alpha: 0.4)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: dotColor,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: dotColor.withValues(alpha: 0.6),
                    blurRadius: 4,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: dotColor,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
