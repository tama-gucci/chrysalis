import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'core/constants/timezones.dart';
import 'data/database/connection.dart';
import 'data/storage/local_vault_storage_provider.dart';
import 'data/sync/vault_synchronizer.dart';
import 'domain/models/task_note.dart';
import 'domain/models/cognitive_modality.dart';
import 'domain/models/task_priority.dart';
import 'domain/services/biometric_service.dart';
import 'domain/services/share_receiver_service.dart';
import 'domain/services/share_auto_staging_controller.dart';
import 'presentation/screens/home_screen.dart';
import 'presentation/theme/app_theme.dart';
import 'transport/ambient_gateway_client.dart';
import 'transport/hybrid_orchestrator_transport.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 1. Resolve persistent Vault root and Inbox directories
  final inboxDir = await ShareAutoStagingController.resolveDefaultInboxDirectoryAsync();
  final vaultDir = ShareAutoStagingController.resolveVaultDirectoryFromInbox(inboxDir);

  if (!await vaultDir.exists()) {
    await vaultDir.create(recursive: true);
  }
  if (!await inboxDir.exists()) {
    await inboxDir.create(recursive: true);
  }

  // 2. Initialize persistent SQLite database
  final dbFile = File(p.join(vaultDir.path, 'chrysalis.db'));
  if (!await dbFile.parent.exists()) {
    await dbFile.parent.create(recursive: true);
  }
  final db = DatabaseFactory.createPersistent(dbFile);

  // 3. Initialize persistent vault storage provider
  final storage = LocalVaultStorageProvider(rootDirectory: vaultDir);
  await storage.initialize();

  // 4. Initialize offline-first synchronization engine
  final synchronizer = VaultSynchronizer(
    database: db,
    storageProvider: storage,
  );
  await synchronizer.initialize();

  // Ingest existing vault tasks and guard starter task seeding behind empty database check
  final existingNotes = await db.getAllCachedNotes();
  if (existingNotes.isEmpty) {
    final ingested = await synchronizer.ingestAllRemoteTasks();
    if (ingested == 0) {
      await synchronizer.saveTask(
        TaskNote(
          title: 'Review Grant Proposal Architecture',
          due: TimezoneUtils.todayDateString(),
          modality: CognitiveModality.analytical,
          priority: TaskPriority.urgent,
          urgencyTier: 4,
          timeEstimate: 75,
          tags: ['task', 'pillar-1/grants'],
          body: '## Context & Objective\nComplete in-depth review of methodology section.',
        ),
      );

      await synchronizer.saveTask(
        TaskNote(
          title: 'Workspace Ergonomics & Cable Clean up',
          modality: CognitiveModality.kinetic,
          priority: TaskPriority.normal,
          urgencyTier: 2,
          timeEstimate: 30,
          tags: ['task', 'pillar-2/health'],
          body: '## Execution Checklist\n- [ ] Clean surface desk\n- [ ] Route monitor wires',
        ),
      );
    }
  } else {
    await synchronizer.ingestAllRemoteTasks();
  }

  // 5. Initialize Orchestrator Transport (Hybrid Engine)
  final gatewayClient = AmbientGatewayClient();
  final transport = HybridOrchestratorTransport(
    gatewayClient: gatewayClient,
    storageProvider: storage,
  );
  await transport.initialize();

  // 6. Initialize Biometrics Source (Google Health Connect)
  final biometricSource = MockHealthConnectDataSource();

  // 7. Initialize Universal Share Sheet Receiver & Auto-Staging Controller
  final shareReceiverService = ShareReceiverService();
  final shareAutoStagingController = ShareAutoStagingController(
    shareReceiverService: shareReceiverService,
    inboxDirectory: inboxDir,
    storageProvider: storage,
  );
  await shareAutoStagingController.initialize();

  runApp(
    ChrysalisApp(
      synchronizer: synchronizer,
      transport: transport,
      biometricSource: biometricSource,
      shareReceiverService: shareReceiverService,
      shareAutoStagingController: shareAutoStagingController,
    ),
  );
}

class ChrysalisApp extends StatelessWidget {
  final VaultSynchronizer synchronizer;
  final HybridOrchestratorTransport transport;
  final BiometricDataSource biometricSource;
  final ShareReceiverService? shareReceiverService;
  final ShareAutoStagingController? shareAutoStagingController;

  const ChrysalisApp({
    super.key,
    required this.synchronizer,
    required this.transport,
    required this.biometricSource,
    this.shareReceiverService,
    this.shareAutoStagingController,
  });

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Chrysalis',
      debugShowCheckedModeBanner: false,
      theme: ChrysalisTheme.darkTheme,
      home: HomeScreen(
        synchronizer: synchronizer,
        transport: transport,
        biometricSource: biometricSource,
        shareReceiverService: shareReceiverService,
        shareAutoStagingController: shareAutoStagingController,
      ),
    );
  }
}
