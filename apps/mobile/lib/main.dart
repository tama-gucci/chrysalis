import 'package:flutter/material.dart';
import 'core/constants/timezones.dart';
import 'data/database/connection.dart';
import 'data/storage/in_memory_vault_storage_provider.dart';
import 'data/sync/vault_synchronizer.dart';
import 'domain/models/task_note.dart';
import 'domain/models/cognitive_modality.dart';
import 'domain/models/task_priority.dart';
import 'domain/services/biometric_service.dart';
import 'presentation/screens/home_screen.dart';
import 'presentation/theme/app_theme.dart';
import 'transport/ambient_gateway_client.dart';
import 'transport/hybrid_orchestrator_transport.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 1. Initialize offline-first SQLite database
  final db = DatabaseFactory.createInMemory();

  // 2. Initialize vault storage provider (In-Memory for agile Phase 1 testing)
  final storage = InMemoryVaultStorageProvider();
  await storage.initialize();

  // 3. Initialize offline-first synchronization engine
  final synchronizer = VaultSynchronizer(
    database: db,
    storageProvider: storage,
  );
  await synchronizer.initialize();

  // Seed with standard starter tasks
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

  // 4. Initialize Orchestrator Transport (Hybrid Engine)
  final gatewayClient = AmbientGatewayClient();
  final transport = HybridOrchestratorTransport(
    gatewayClient: gatewayClient,
    storageProvider: storage,
  );
  await transport.initialize();

  // 5. Initialize Biometrics Source (Google Health Connect)
  final biometricSource = MockHealthConnectDataSource();

  runApp(
    ChrysalisApp(
      synchronizer: synchronizer,
      transport: transport,
      biometricSource: biometricSource,
    ),
  );
}

class ChrysalisApp extends StatelessWidget {
  final VaultSynchronizer synchronizer;
  final HybridOrchestratorTransport transport;
  final BiometricDataSource biometricSource;

  const ChrysalisApp({
    super.key,
    required this.synchronizer,
    required this.transport,
    required this.biometricSource,
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
      ),
    );
  }
}
