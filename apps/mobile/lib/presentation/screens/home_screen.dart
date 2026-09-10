import 'dart:async';
import 'package:flutter/material.dart';
import '../../domain/models/biometrics.dart';
import '../../domain/models/task_note.dart';
import '../../domain/models/task_status.dart';
import '../../domain/models/ultradian_sprint.dart';
import '../../domain/parser/task_note_parser.dart';
import '../../domain/services/bio_cognitive_scheduler.dart';
import '../../domain/services/biometric_service.dart';
import '../../data/sync/vault_synchronizer.dart';
import '../../transport/hybrid_orchestrator_transport.dart';
import '../../transport/orchestrator_transport.dart';
import '../theme/app_theme.dart';
import '../widgets/active_sprint_card.dart';
import '../../domain/services/share_receiver_service.dart';
import '../../domain/services/share_auto_staging_controller.dart';
import '../widgets/morning_calibration_sheet.dart';
import '../widgets/orchestrator_status_chip.dart';
import '../widgets/rapid_capture_bar.dart';
import '../widgets/ultradian_timeline_widget.dart';

/// Main Chrysalis Mobile Dashboard Screen.
class HomeScreen extends StatefulWidget {
  final VaultSynchronizer synchronizer;
  final HybridOrchestratorTransport transport;
  final BiometricDataSource biometricSource;
  final ShareReceiverService? shareReceiverService;
  final ShareAutoStagingController? shareAutoStagingController;

  const HomeScreen({
    super.key,
    required this.synchronizer,
    required this.transport,
    required this.biometricSource,
    this.shareReceiverService,
    this.shareAutoStagingController,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  DiurnalSchedule? _schedule;
  BiometricTelemetry? _biometrics;
  List<TaskNote> _cachedTasks = [];
  StreamSubscription? _notesSubscription;
  StreamSubscription? _transportSub;
  StreamSubscription? _eventSub;
  TransportConnectionState _transportState = TransportConnectionState.disconnected;

  @override
  void initState() {
    super.initState();
    _transportState = widget.transport.currentState;
    _transportSub = widget.transport.connectionState.listen((state) {
      if (mounted) {
        setState(() {
          _transportState = state;
        });
      }
    });

    _eventSub = widget.transport.incomingEvents.listen((event) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(event.content),
            duration: const Duration(seconds: 3),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    });

    // Watch SQLite CachedNotes synchronously so subscription is ready for disposal
    _notesSubscription = widget.synchronizer.database.watchAllCachedNotes().listen((rows) {
      final tasks = <TaskNote>[];
      for (final r in rows) {
        try {
          tasks.add(TaskNoteParser.parse(r.content, path: r.path, strictTimezone: false));
        } catch (_) {}
      }
      if (mounted) {
        _cachedTasks = tasks;
        _regenerateSchedule(updateState: true);
      }
    });

    _regenerateSchedule(updateState: false);
    _loadBiometrics();
  }

  Future<void> _loadBiometrics() async {
    try {
      final bio = await widget.biometricSource.getTelemetryForDate(DateTime.now());
      if (mounted) {
        _biometrics = bio;
        _regenerateSchedule(updateState: true);
      }
    } catch (_) {}
  }

  void _regenerateSchedule({bool updateState = true}) {
    final now = DateTime.now();
    final wakeTime = _biometrics?.inferredWakeTime ??
        DateTime(now.year, now.month, now.day, 7, 30);
    final energy = _biometrics?.computedReadinessScore ?? 3;

    final schedule = BioCognitiveScheduler.generateDiurnalSchedule(
      date: now,
      wakeTime: wakeTime,
      energyScore: energy,
      candidateTasks: _cachedTasks,
    );

    if (updateState && mounted) {
      setState(() {
        _schedule = schedule;
      });
    } else {
      _schedule = schedule;
    }
  }

  void _openCalibrationSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => MorningCalibrationSheet(
        initialWakeTime: _schedule?.wakeTime ?? DateTime.now(),
        initialEnergy: _schedule?.energyScore ?? 3,
        biometrics: _biometrics,
        onCalibrate: (wakeTime, energy) async {
          setState(() {
            _schedule = BioCognitiveScheduler.generateDiurnalSchedule(
              date: DateTime.now(),
              wakeTime: wakeTime,
              energyScore: energy,
              candidateTasks: _cachedTasks,
            );
          });
          // Dispatch /morning slash command through orchestrator transport
          await widget.transport.sendCommand('/morning', parameters: {
            'wake': '${wakeTime.hour.toString().padLeft(2, '0')}:${wakeTime.minute.toString().padLeft(2, '0')}',
            'energy': energy,
          });
        },
      ),
    );
  }

  void _handleTaskCreated(TaskNote task) async {
    await widget.synchronizer.saveTask(task);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Task "${task.title}" saved (<10ms) & journaled.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  void _handleCompleteBlock(DiurnalBlock block) async {
    // Find task assigned to block if any
    if (block.taskPath != null) {
      final task = _cachedTasks.firstWhere(
        (t) => t.path == block.taskPath,
        orElse: () => TaskNote(title: block.title, path: block.taskPath),
      );
      if (task.status != TaskStatus.done) {
        final updated = task.transitionTo(TaskStatus.done);
        await widget.synchronizer.saveTask(updated);
      }
    }
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Session "${block.title}" completed! Telemetry recorded.'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _showOrchestratorMenu() {
    showModalBottomSheet(
      context: context,
      backgroundColor: ChrysalisTheme.surfaceDark,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Antigravity Orchestrator (${_transportState.name})',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  ActionChip(
                    avatar: const Icon(Icons.wb_sunny, size: 16),
                    label: const Text('/morning'),
                    onPressed: () {
                      Navigator.pop(ctx);
                      _openCalibrationSheet();
                    },
                  ),
                  ActionChip(
                    avatar: const Icon(Icons.nightlight_round, size: 16),
                    label: const Text('/evening'),
                    onPressed: () {
                      Navigator.pop(ctx);
                      widget.transport.sendCommand('/evening');
                    },
                  ),
                  ActionChip(
                    avatar: const Icon(Icons.medical_services_outlined, size: 16),
                    label: const Text('/doctor'),
                    onPressed: () {
                      Navigator.pop(ctx);
                      widget.transport.sendCommand('/doctor');
                    },
                  ),
                  ActionChip(
                    avatar: const Icon(Icons.pause_circle_outline, size: 16),
                    label: const Text('/pause'),
                    onPressed: () {
                      Navigator.pop(ctx);
                      widget.transport.sendCommand('/pause', parameters: {'mode': 'flow'});
                    },
                  ),
                  if (widget.shareReceiverService != null)
                    ActionChip(
                      avatar: const Icon(Icons.share_outlined, size: 16),
                      label: const Text('Share Focus'),
                      onPressed: () {
                        Navigator.pop(ctx);
                        final active = _schedule?.currentBlock();
                        final title = active?.title ?? 'Active Chrysalis Sprint';
                        widget.shareReceiverService?.shareContent(
                          'Currently in Chrysalis focus session: $title',
                          title: title,
                        );
                      },
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _notesSubscription?.cancel();
    _transportSub?.cancel();
    _eventSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final activeBlock = _schedule?.currentBlock();

    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.bubble_chart, color: ChrysalisTheme.primaryTeal),
            SizedBox(width: 8),
            Text(
              'Chrysalis',
              style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 0.5),
            ),
          ],
        ),
        actions: [
          OrchestratorStatusChip(
            state: _transportState,
            onTap: _showOrchestratorMenu,
          ),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.wb_sunny_outlined, color: Colors.amber),
            tooltip: 'Morning Calibration',
            onPressed: _openCalibrationSheet,
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: RefreshIndicator(
              onRefresh: () async {
                await widget.synchronizer.drainMutationJournal();
                await widget.synchronizer.ingestAllRemoteTasks();
              },
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const SizedBox(height: 8),
                    // Active Ultradian Sprint Card
                    ActiveSprintCard(
                      activeBlock: activeBlock,
                      onComplete: () {
                        if (activeBlock != null) {
                          _handleCompleteBlock(activeBlock);
                        }
                      },
                      onPause: () {
                        widget.transport.sendCommand('/pause');
                      },
                    ),

                    const Padding(
                      padding: EdgeInsets.fromLTRB(16, 16, 16, 6),
                      child: Row(
                        children: [
                          Icon(Icons.access_time_outlined, size: 16, color: ChrysalisTheme.primaryTeal),
                          SizedBox(width: 6),
                          Text(
                            "Today's Diurnal Timeline (75-90m Sprints • 15m Buffers)",
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: Colors.white70,
                            ),
                          ),
                        ],
                      ),
                    ),

                    if (_schedule != null)
                      UltradianTimelineWidget(
                        schedule: _schedule!,
                        onBlockCompleted: _handleCompleteBlock,
                      ),
                    const SizedBox(height: 80),
                  ],
                ),
              ),
            ),
          ),
          // Pinned rapid shorthand capture bar at bottom
          RapidCaptureBar(
            onTaskCreated: _handleTaskCreated,
          ),
        ],
      ),
    );
  }
}
