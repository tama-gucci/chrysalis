import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:chrysalis_mobile/main.dart';
import 'package:chrysalis_mobile/data/database/connection.dart';
import 'package:chrysalis_mobile/data/storage/in_memory_vault_storage_provider.dart';
import 'package:chrysalis_mobile/data/sync/vault_synchronizer.dart';
import 'package:chrysalis_mobile/domain/services/biometric_service.dart';
import 'package:chrysalis_mobile/transport/ambient_gateway_client.dart';
import 'package:chrysalis_mobile/transport/hybrid_orchestrator_transport.dart';

void main() {
  testWidgets('ChrysalisApp boots and renders top-level dashboard', (WidgetTester tester) async {
    final db = DatabaseFactory.createInMemory();
    final storage = InMemoryVaultStorageProvider();
    await storage.initialize();

    final synchronizer = VaultSynchronizer(
      database: db,
      storageProvider: storage,
    );
    await synchronizer.initialize();

    final transport = HybridOrchestratorTransport(
      gatewayClient: AmbientGatewayClient(),
      storageProvider: storage,
    );
    await transport.initialize();

    final biometricSource = MockHealthConnectDataSource();

    await tester.pumpWidget(
      ChrysalisApp(
        synchronizer: synchronizer,
        transport: transport,
        biometricSource: biometricSource,
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    expect(find.text('Chrysalis'), findsOneWidget);

    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 10));

    await tester.runAsync(() async {
      await synchronizer.dispose();
      await transport.dispose();
      await storage.dispose();
    });
  }, timeout: const Timeout(Duration(seconds: 15)));
}
