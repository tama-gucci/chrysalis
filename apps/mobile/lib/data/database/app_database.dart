import 'package:drift/drift.dart';
import 'tables.dart';

part 'app_database.g.dart';

@DriftDatabase(tables: [CachedNotes, MutationJournal])
class AppDatabase extends _$AppDatabase {
  AppDatabase(super.e);

  @override
  int get schemaVersion => 1;

  // CachedNotes Queries

  Future<List<CachedNote>> getAllCachedNotes() => select(cachedNotes).get();

  Stream<List<CachedNote>> watchAllCachedNotes() => select(cachedNotes).watch();

  Future<CachedNote?> getCachedNoteByPath(String path) =>
      (select(cachedNotes)..where((tbl) => tbl.path.equals(path))).getSingleOrNull();

  Future<void> upsertCachedNote(CachedNotesCompanion note) =>
      into(cachedNotes).insertOnConflictUpdate(note);

  Future<int> deleteCachedNote(String path) =>
      (delete(cachedNotes)..where((tbl) => tbl.path.equals(path))).go();

  // MutationJournal Queries

  Future<int> insertMutation(MutationJournalCompanion mutation) =>
      into(mutationJournal).insert(mutation);

  Future<List<MutationJournalData>> getPendingMutations() => (select(mutationJournal)
        ..where((tbl) => tbl.syncState.equals('pending'))
        ..orderBy([(tbl) => OrderingTerm.asc(tbl.createdAt)]))
      .get();

  Stream<List<MutationJournalData>> watchPendingMutations() => (select(mutationJournal)
        ..where((tbl) => tbl.syncState.equals('pending'))
        ..orderBy([(tbl) => OrderingTerm.asc(tbl.createdAt)]))
      .watch();

  Future<void> markMutationInFlight(int id) async {
    final entry = await (select(mutationJournal)..where((tbl) => tbl.id.equals(id))).getSingleOrNull();
    final count = (entry?.retryCount ?? 0) + 1;
    await (update(mutationJournal)..where((tbl) => tbl.id.equals(id))).write(
      MutationJournalCompanion(
        syncState: const Value('in_flight'),
        retryCount: Value(count),
      ),
    );
  }

  Future<void> markMutationSynced(int id, DateTime timestamp) =>
      (update(mutationJournal)..where((tbl) => tbl.id.equals(id))).write(
        MutationJournalCompanion(
          syncState: const Value('synced'),
          syncedAt: Value(timestamp),
        ),
      );

  Future<void> markMutationFailed(int id, String error) =>
      (update(mutationJournal)..where((tbl) => tbl.id.equals(id))).write(
        MutationJournalCompanion(
          syncState: const Value('failed'),
          errorMessage: Value(error),
        ),
      );

  Future<int> resetInFlightMutations() =>
      (update(mutationJournal)..where((tbl) => tbl.syncState.equals('in_flight'))).write(
        const MutationJournalCompanion(
          syncState: Value('pending'),
        ),
      );
}
