import 'dart:io';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'app_database.dart';

/// Database factory for mobile client runtime and unit testing.
class DatabaseFactory {
  /// Creates an in-memory SQLite database instance (used for tests and memory-only mode).
  static AppDatabase createInMemory() {
    return AppDatabase(NativeDatabase.memory());
  }

  /// Creates a persistent SQLite database instance stored at the given file path.
  static AppDatabase createPersistent(File dbFile) {
    return AppDatabase(
      LazyDatabase(() async {
        return NativeDatabase(dbFile);
      }),
    );
  }
}
