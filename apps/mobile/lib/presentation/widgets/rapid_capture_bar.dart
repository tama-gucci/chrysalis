import 'package:flutter/material.dart';
import '../../domain/models/task_note.dart';
import '../../domain/parser/task_shorthand_parser.dart';
import '../theme/app_theme.dart';

/// Rapid Shorthand Task Capture Bar with live token previews.
class RapidCaptureBar extends StatefulWidget {
  final ValueChanged<TaskNote> onTaskCreated;

  const RapidCaptureBar({
    super.key,
    required this.onTaskCreated,
  });

  @override
  State<RapidCaptureBar> createState() => _RapidCaptureBarState();
}

class _RapidCaptureBarState extends State<RapidCaptureBar> {
  final TextEditingController _controller = TextEditingController();
  ParsedShorthand? _liveParsed;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    final text = _controller.text;
    if (text.trim().isNotEmpty) {
      setState(() {
        _liveParsed = TaskShorthandParser.parse(text);
      });
    } else {
      setState(() {
        _liveParsed = null;
      });
    }
  }

  void _submit() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    final parsed = TaskShorthandParser.parse(text);
    final task = parsed.toTaskNote();
    widget.onTaskCreated(task);

    _controller.clear();
    setState(() {
      _liveParsed = null;
    });
  }

  @override
  void dispose() {
    _controller.removeListener(_onTextChanged);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: ChrysalisTheme.surfaceDark,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Live parsed chips preview
            if (_liveParsed != null && _liveParsed!.title.isNotEmpty) ...[
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: [
                  Chip(
                    visualDensity: VisualDensity.compact,
                    backgroundColor: ChrysalisTheme.forModality(_liveParsed!.modality).withValues(alpha: 0.2),
                    side: BorderSide(color: ChrysalisTheme.forModality(_liveParsed!.modality)),
                    label: Text(
                      '@${_liveParsed!.modality.yamlValue}',
                      style: TextStyle(
                        color: ChrysalisTheme.forModality(_liveParsed!.modality),
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  Chip(
                    visualDensity: VisualDensity.compact,
                    backgroundColor: Colors.blueGrey.withValues(alpha: 0.3),
                    label: Text(
                      '~${_liveParsed!.durationMinutes}m',
                      style: const TextStyle(fontSize: 11),
                    ),
                  ),
                  Chip(
                    visualDensity: VisualDensity.compact,
                    backgroundColor: Colors.redAccent.withValues(alpha: 0.2),
                    side: const BorderSide(color: Colors.redAccent),
                    label: Text(
                      '!tier ${_liveParsed!.urgencyTier}',
                      style: const TextStyle(color: Colors.redAccent, fontSize: 11),
                    ),
                  ),
                  for (final tag in _liveParsed!.tags.where((t) => t != 'task'))
                    Chip(
                      visualDensity: VisualDensity.compact,
                      backgroundColor: Colors.teal.withValues(alpha: 0.2),
                      side: const BorderSide(color: Colors.teal),
                      label: Text(
                        '#$tag',
                        style: const TextStyle(color: Colors.tealAccent, fontSize: 11),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 6),
            ],
            // Input row
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    style: const TextStyle(color: Colors.white, fontSize: 14),
                    decoration: InputDecoration(
                      hintText: 'Review grant #research ~75m !3 @analytical',
                      hintStyle: TextStyle(color: Colors.grey.shade500, fontSize: 13),
                      filled: true,
                      fillColor: Colors.black26,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                    ),
                    onSubmitted: (_) => _submit(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  icon: const Icon(Icons.add_task),
                  tooltip: 'Capture Task',
                  onPressed: _submit,
                  style: IconButton.styleFrom(
                    backgroundColor: ChrysalisTheme.primaryTeal,
                    foregroundColor: Colors.black,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
