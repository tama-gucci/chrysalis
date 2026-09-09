import 'package:drift/drift.dart';

/// Local cache table mirroring markdown notes from the vault.
class CachedNotes extends Table {
  /// Relative vault path (e.g. "TaskNotes/Tasks/example-task.md")
  TextColumn get path => text()();

  /// Parsed task title
  TextColumn get title => text()();

  /// Task lifecycle status ('todo', 'in-progress', 'done', 'archived')
  TextColumn get status => text()();

  /// Complete raw Markdown content
  TextColumn get content => text()();

  /// Extracted YAML frontmatter string
  TextColumn get frontmatterYaml => text()();

  /// Remote ETag or revision hash for delta synchronization
  TextColumn get etag => text().nullable()();

  /// Remote modification timestamp
  DateTimeColumn get lastModifiedRemote => dateTime().nullable()();

  /// Timestamp when saved to local SQLite cache
  DateTimeColumn get lastCachedLocally => dateTime()();

  /// True if modified locally and awaiting sync
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {path};
}

/// Offline mutation journal table recording pending changes before pushing to remote vault.
class MutationJournal extends Table {
  /// Auto-incrementing primary key
  IntColumn get id => integer().autoIncrement()();

  /// Vault file path being mutated
  TextColumn get path => text()();

  /// 'upsert', 'delete', or 'status_change'
  TextColumn get mutationType => text()();

  /// Payload content (full file markdown or change delta)
  TextColumn get payload => text()();

  /// SHA-256 hash of the payload for integrity checking
  TextColumn get payloadSha256 => text()();

  /// Timestamp when mutation occurred on mobile device
  DateTimeColumn get createdAt => dateTime()();

  /// 'pending', 'in_flight', 'synced', 'failed'
  TextColumn get syncState => text()();

  /// Number of sync attempts
  IntColumn get retryCount => integer().withDefault(const Constant(0))();

  /// Error message if last sync attempt failed
  TextColumn get errorMessage => text().nullable()();

  /// Timestamp when successfully drained to remote vault
  DateTimeColumn get syncedAt => dateTime().nullable()();
}
