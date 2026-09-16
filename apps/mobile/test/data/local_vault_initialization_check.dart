// Run with: dart --packages=.dart_tool/package_config.json test/data/local_vault_initialization_check.dart
import 'dart:io';
import 'package:chrysalis_mobile/data/storage/local_vault_storage_provider.dart';

Future<void> main() async {
  final directory = await Directory.systemTemp.createTemp('chrysalis-init-');
  final provider = LocalVaultStorageProvider(rootDirectory: directory);
  try {
    final first = provider.initialize();
    final second = provider.initialize();
    if (!identical(first, second)) {
      throw StateError('Concurrent initialization must share one operation');
    }
    await Future.wait([first, second]);
    if (!identical(first, provider.initialize())) {
      throw StateError('Repeated initialization must reuse the original operation');
    }
    await provider.writeTextFile('chrysalis/Tasks/test.md', 'Synthetic test');
    if (await provider.readTextFile('chrysalis/Tasks/test.md') != 'Synthetic test') {
      throw StateError('Storage must remain usable after repeated initialization');
    }
    stdout.writeln('PASS: repeated initialization and file persistence');
  } finally {
    await provider.dispose();
    await directory.delete(recursive: true);
  }
}
