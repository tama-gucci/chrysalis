// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_database.dart';

// ignore_for_file: type=lint
class $CachedNotesTable extends CachedNotes
    with TableInfo<$CachedNotesTable, CachedNote> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedNotesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _pathMeta = const VerificationMeta('path');
  @override
  late final GeneratedColumn<String> path = GeneratedColumn<String>(
    'path',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _titleMeta = const VerificationMeta('title');
  @override
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
    'title',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
    'status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _contentMeta = const VerificationMeta(
    'content',
  );
  @override
  late final GeneratedColumn<String> content = GeneratedColumn<String>(
    'content',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _frontmatterYamlMeta = const VerificationMeta(
    'frontmatterYaml',
  );
  @override
  late final GeneratedColumn<String> frontmatterYaml = GeneratedColumn<String>(
    'frontmatter_yaml',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _etagMeta = const VerificationMeta('etag');
  @override
  late final GeneratedColumn<String> etag = GeneratedColumn<String>(
    'etag',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _lastModifiedRemoteMeta =
      const VerificationMeta('lastModifiedRemote');
  @override
  late final GeneratedColumn<DateTime> lastModifiedRemote =
      GeneratedColumn<DateTime>(
        'last_modified_remote',
        aliasedName,
        true,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _lastCachedLocallyMeta = const VerificationMeta(
    'lastCachedLocally',
  );
  @override
  late final GeneratedColumn<DateTime> lastCachedLocally =
      GeneratedColumn<DateTime>(
        'last_cached_locally',
        aliasedName,
        false,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _isDirtyMeta = const VerificationMeta(
    'isDirty',
  );
  @override
  late final GeneratedColumn<bool> isDirty = GeneratedColumn<bool>(
    'is_dirty',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_dirty" IN (0, 1))',
    ),
    defaultValue: const Constant(false),
  );
  @override
  List<GeneratedColumn> get $columns => [
    path,
    title,
    status,
    content,
    frontmatterYaml,
    etag,
    lastModifiedRemote,
    lastCachedLocally,
    isDirty,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_notes';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedNote> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('path')) {
      context.handle(
        _pathMeta,
        path.isAcceptableOrUnknown(data['path']!, _pathMeta),
      );
    } else if (isInserting) {
      context.missing(_pathMeta);
    }
    if (data.containsKey('title')) {
      context.handle(
        _titleMeta,
        title.isAcceptableOrUnknown(data['title']!, _titleMeta),
      );
    } else if (isInserting) {
      context.missing(_titleMeta);
    }
    if (data.containsKey('status')) {
      context.handle(
        _statusMeta,
        status.isAcceptableOrUnknown(data['status']!, _statusMeta),
      );
    } else if (isInserting) {
      context.missing(_statusMeta);
    }
    if (data.containsKey('content')) {
      context.handle(
        _contentMeta,
        content.isAcceptableOrUnknown(data['content']!, _contentMeta),
      );
    } else if (isInserting) {
      context.missing(_contentMeta);
    }
    if (data.containsKey('frontmatter_yaml')) {
      context.handle(
        _frontmatterYamlMeta,
        frontmatterYaml.isAcceptableOrUnknown(
          data['frontmatter_yaml']!,
          _frontmatterYamlMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_frontmatterYamlMeta);
    }
    if (data.containsKey('etag')) {
      context.handle(
        _etagMeta,
        etag.isAcceptableOrUnknown(data['etag']!, _etagMeta),
      );
    }
    if (data.containsKey('last_modified_remote')) {
      context.handle(
        _lastModifiedRemoteMeta,
        lastModifiedRemote.isAcceptableOrUnknown(
          data['last_modified_remote']!,
          _lastModifiedRemoteMeta,
        ),
      );
    }
    if (data.containsKey('last_cached_locally')) {
      context.handle(
        _lastCachedLocallyMeta,
        lastCachedLocally.isAcceptableOrUnknown(
          data['last_cached_locally']!,
          _lastCachedLocallyMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_lastCachedLocallyMeta);
    }
    if (data.containsKey('is_dirty')) {
      context.handle(
        _isDirtyMeta,
        isDirty.isAcceptableOrUnknown(data['is_dirty']!, _isDirtyMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {path};
  @override
  CachedNote map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedNote(
      path: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}path'],
      )!,
      title: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}title'],
      )!,
      status: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}status'],
      )!,
      content: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}content'],
      )!,
      frontmatterYaml: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}frontmatter_yaml'],
      )!,
      etag: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}etag'],
      ),
      lastModifiedRemote: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}last_modified_remote'],
      ),
      lastCachedLocally: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}last_cached_locally'],
      )!,
      isDirty: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_dirty'],
      )!,
    );
  }

  @override
  $CachedNotesTable createAlias(String alias) {
    return $CachedNotesTable(attachedDatabase, alias);
  }
}

class CachedNote extends DataClass implements Insertable<CachedNote> {
  /// Relative vault path (e.g. "TaskNotes/Tasks/example-task.md")
  final String path;

  /// Parsed task title
  final String title;

  /// Task lifecycle status ('todo', 'in-progress', 'done', 'archived')
  final String status;

  /// Complete raw Markdown content
  final String content;

  /// Extracted YAML frontmatter string
  final String frontmatterYaml;

  /// Remote ETag or revision hash for delta synchronization
  final String? etag;

  /// Remote modification timestamp
  final DateTime? lastModifiedRemote;

  /// Timestamp when saved to local SQLite cache
  final DateTime lastCachedLocally;

  /// True if modified locally and awaiting sync
  final bool isDirty;
  const CachedNote({
    required this.path,
    required this.title,
    required this.status,
    required this.content,
    required this.frontmatterYaml,
    this.etag,
    this.lastModifiedRemote,
    required this.lastCachedLocally,
    required this.isDirty,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['path'] = Variable<String>(path);
    map['title'] = Variable<String>(title);
    map['status'] = Variable<String>(status);
    map['content'] = Variable<String>(content);
    map['frontmatter_yaml'] = Variable<String>(frontmatterYaml);
    if (!nullToAbsent || etag != null) {
      map['etag'] = Variable<String>(etag);
    }
    if (!nullToAbsent || lastModifiedRemote != null) {
      map['last_modified_remote'] = Variable<DateTime>(lastModifiedRemote);
    }
    map['last_cached_locally'] = Variable<DateTime>(lastCachedLocally);
    map['is_dirty'] = Variable<bool>(isDirty);
    return map;
  }

  CachedNotesCompanion toCompanion(bool nullToAbsent) {
    return CachedNotesCompanion(
      path: Value(path),
      title: Value(title),
      status: Value(status),
      content: Value(content),
      frontmatterYaml: Value(frontmatterYaml),
      etag: etag == null && nullToAbsent ? const Value.absent() : Value(etag),
      lastModifiedRemote: lastModifiedRemote == null && nullToAbsent
          ? const Value.absent()
          : Value(lastModifiedRemote),
      lastCachedLocally: Value(lastCachedLocally),
      isDirty: Value(isDirty),
    );
  }

  factory CachedNote.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedNote(
      path: serializer.fromJson<String>(json['path']),
      title: serializer.fromJson<String>(json['title']),
      status: serializer.fromJson<String>(json['status']),
      content: serializer.fromJson<String>(json['content']),
      frontmatterYaml: serializer.fromJson<String>(json['frontmatterYaml']),
      etag: serializer.fromJson<String?>(json['etag']),
      lastModifiedRemote: serializer.fromJson<DateTime?>(
        json['lastModifiedRemote'],
      ),
      lastCachedLocally: serializer.fromJson<DateTime>(
        json['lastCachedLocally'],
      ),
      isDirty: serializer.fromJson<bool>(json['isDirty']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'path': serializer.toJson<String>(path),
      'title': serializer.toJson<String>(title),
      'status': serializer.toJson<String>(status),
      'content': serializer.toJson<String>(content),
      'frontmatterYaml': serializer.toJson<String>(frontmatterYaml),
      'etag': serializer.toJson<String?>(etag),
      'lastModifiedRemote': serializer.toJson<DateTime?>(lastModifiedRemote),
      'lastCachedLocally': serializer.toJson<DateTime>(lastCachedLocally),
      'isDirty': serializer.toJson<bool>(isDirty),
    };
  }

  CachedNote copyWith({
    String? path,
    String? title,
    String? status,
    String? content,
    String? frontmatterYaml,
    Value<String?> etag = const Value.absent(),
    Value<DateTime?> lastModifiedRemote = const Value.absent(),
    DateTime? lastCachedLocally,
    bool? isDirty,
  }) => CachedNote(
    path: path ?? this.path,
    title: title ?? this.title,
    status: status ?? this.status,
    content: content ?? this.content,
    frontmatterYaml: frontmatterYaml ?? this.frontmatterYaml,
    etag: etag.present ? etag.value : this.etag,
    lastModifiedRemote: lastModifiedRemote.present
        ? lastModifiedRemote.value
        : this.lastModifiedRemote,
    lastCachedLocally: lastCachedLocally ?? this.lastCachedLocally,
    isDirty: isDirty ?? this.isDirty,
  );
  CachedNote copyWithCompanion(CachedNotesCompanion data) {
    return CachedNote(
      path: data.path.present ? data.path.value : this.path,
      title: data.title.present ? data.title.value : this.title,
      status: data.status.present ? data.status.value : this.status,
      content: data.content.present ? data.content.value : this.content,
      frontmatterYaml: data.frontmatterYaml.present
          ? data.frontmatterYaml.value
          : this.frontmatterYaml,
      etag: data.etag.present ? data.etag.value : this.etag,
      lastModifiedRemote: data.lastModifiedRemote.present
          ? data.lastModifiedRemote.value
          : this.lastModifiedRemote,
      lastCachedLocally: data.lastCachedLocally.present
          ? data.lastCachedLocally.value
          : this.lastCachedLocally,
      isDirty: data.isDirty.present ? data.isDirty.value : this.isDirty,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedNote(')
          ..write('path: $path, ')
          ..write('title: $title, ')
          ..write('status: $status, ')
          ..write('content: $content, ')
          ..write('frontmatterYaml: $frontmatterYaml, ')
          ..write('etag: $etag, ')
          ..write('lastModifiedRemote: $lastModifiedRemote, ')
          ..write('lastCachedLocally: $lastCachedLocally, ')
          ..write('isDirty: $isDirty')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    path,
    title,
    status,
    content,
    frontmatterYaml,
    etag,
    lastModifiedRemote,
    lastCachedLocally,
    isDirty,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedNote &&
          other.path == this.path &&
          other.title == this.title &&
          other.status == this.status &&
          other.content == this.content &&
          other.frontmatterYaml == this.frontmatterYaml &&
          other.etag == this.etag &&
          other.lastModifiedRemote == this.lastModifiedRemote &&
          other.lastCachedLocally == this.lastCachedLocally &&
          other.isDirty == this.isDirty);
}

class CachedNotesCompanion extends UpdateCompanion<CachedNote> {
  final Value<String> path;
  final Value<String> title;
  final Value<String> status;
  final Value<String> content;
  final Value<String> frontmatterYaml;
  final Value<String?> etag;
  final Value<DateTime?> lastModifiedRemote;
  final Value<DateTime> lastCachedLocally;
  final Value<bool> isDirty;
  final Value<int> rowid;
  const CachedNotesCompanion({
    this.path = const Value.absent(),
    this.title = const Value.absent(),
    this.status = const Value.absent(),
    this.content = const Value.absent(),
    this.frontmatterYaml = const Value.absent(),
    this.etag = const Value.absent(),
    this.lastModifiedRemote = const Value.absent(),
    this.lastCachedLocally = const Value.absent(),
    this.isDirty = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CachedNotesCompanion.insert({
    required String path,
    required String title,
    required String status,
    required String content,
    required String frontmatterYaml,
    this.etag = const Value.absent(),
    this.lastModifiedRemote = const Value.absent(),
    required DateTime lastCachedLocally,
    this.isDirty = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : path = Value(path),
       title = Value(title),
       status = Value(status),
       content = Value(content),
       frontmatterYaml = Value(frontmatterYaml),
       lastCachedLocally = Value(lastCachedLocally);
  static Insertable<CachedNote> custom({
    Expression<String>? path,
    Expression<String>? title,
    Expression<String>? status,
    Expression<String>? content,
    Expression<String>? frontmatterYaml,
    Expression<String>? etag,
    Expression<DateTime>? lastModifiedRemote,
    Expression<DateTime>? lastCachedLocally,
    Expression<bool>? isDirty,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (path != null) 'path': path,
      if (title != null) 'title': title,
      if (status != null) 'status': status,
      if (content != null) 'content': content,
      if (frontmatterYaml != null) 'frontmatter_yaml': frontmatterYaml,
      if (etag != null) 'etag': etag,
      if (lastModifiedRemote != null)
        'last_modified_remote': lastModifiedRemote,
      if (lastCachedLocally != null) 'last_cached_locally': lastCachedLocally,
      if (isDirty != null) 'is_dirty': isDirty,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CachedNotesCompanion copyWith({
    Value<String>? path,
    Value<String>? title,
    Value<String>? status,
    Value<String>? content,
    Value<String>? frontmatterYaml,
    Value<String?>? etag,
    Value<DateTime?>? lastModifiedRemote,
    Value<DateTime>? lastCachedLocally,
    Value<bool>? isDirty,
    Value<int>? rowid,
  }) {
    return CachedNotesCompanion(
      path: path ?? this.path,
      title: title ?? this.title,
      status: status ?? this.status,
      content: content ?? this.content,
      frontmatterYaml: frontmatterYaml ?? this.frontmatterYaml,
      etag: etag ?? this.etag,
      lastModifiedRemote: lastModifiedRemote ?? this.lastModifiedRemote,
      lastCachedLocally: lastCachedLocally ?? this.lastCachedLocally,
      isDirty: isDirty ?? this.isDirty,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (path.present) {
      map['path'] = Variable<String>(path.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (content.present) {
      map['content'] = Variable<String>(content.value);
    }
    if (frontmatterYaml.present) {
      map['frontmatter_yaml'] = Variable<String>(frontmatterYaml.value);
    }
    if (etag.present) {
      map['etag'] = Variable<String>(etag.value);
    }
    if (lastModifiedRemote.present) {
      map['last_modified_remote'] = Variable<DateTime>(
        lastModifiedRemote.value,
      );
    }
    if (lastCachedLocally.present) {
      map['last_cached_locally'] = Variable<DateTime>(lastCachedLocally.value);
    }
    if (isDirty.present) {
      map['is_dirty'] = Variable<bool>(isDirty.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedNotesCompanion(')
          ..write('path: $path, ')
          ..write('title: $title, ')
          ..write('status: $status, ')
          ..write('content: $content, ')
          ..write('frontmatterYaml: $frontmatterYaml, ')
          ..write('etag: $etag, ')
          ..write('lastModifiedRemote: $lastModifiedRemote, ')
          ..write('lastCachedLocally: $lastCachedLocally, ')
          ..write('isDirty: $isDirty, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $MutationJournalTable extends MutationJournal
    with TableInfo<$MutationJournalTable, MutationJournalData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $MutationJournalTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _pathMeta = const VerificationMeta('path');
  @override
  late final GeneratedColumn<String> path = GeneratedColumn<String>(
    'path',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _mutationTypeMeta = const VerificationMeta(
    'mutationType',
  );
  @override
  late final GeneratedColumn<String> mutationType = GeneratedColumn<String>(
    'mutation_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _payloadMeta = const VerificationMeta(
    'payload',
  );
  @override
  late final GeneratedColumn<String> payload = GeneratedColumn<String>(
    'payload',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _payloadSha256Meta = const VerificationMeta(
    'payloadSha256',
  );
  @override
  late final GeneratedColumn<String> payloadSha256 = GeneratedColumn<String>(
    'payload_sha256',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _syncStateMeta = const VerificationMeta(
    'syncState',
  );
  @override
  late final GeneratedColumn<String> syncState = GeneratedColumn<String>(
    'sync_state',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _retryCountMeta = const VerificationMeta(
    'retryCount',
  );
  @override
  late final GeneratedColumn<int> retryCount = GeneratedColumn<int>(
    'retry_count',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _errorMessageMeta = const VerificationMeta(
    'errorMessage',
  );
  @override
  late final GeneratedColumn<String> errorMessage = GeneratedColumn<String>(
    'error_message',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _syncedAtMeta = const VerificationMeta(
    'syncedAt',
  );
  @override
  late final GeneratedColumn<DateTime> syncedAt = GeneratedColumn<DateTime>(
    'synced_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    path,
    mutationType,
    payload,
    payloadSha256,
    createdAt,
    syncState,
    retryCount,
    errorMessage,
    syncedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'mutation_journal';
  @override
  VerificationContext validateIntegrity(
    Insertable<MutationJournalData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('path')) {
      context.handle(
        _pathMeta,
        path.isAcceptableOrUnknown(data['path']!, _pathMeta),
      );
    } else if (isInserting) {
      context.missing(_pathMeta);
    }
    if (data.containsKey('mutation_type')) {
      context.handle(
        _mutationTypeMeta,
        mutationType.isAcceptableOrUnknown(
          data['mutation_type']!,
          _mutationTypeMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_mutationTypeMeta);
    }
    if (data.containsKey('payload')) {
      context.handle(
        _payloadMeta,
        payload.isAcceptableOrUnknown(data['payload']!, _payloadMeta),
      );
    } else if (isInserting) {
      context.missing(_payloadMeta);
    }
    if (data.containsKey('payload_sha256')) {
      context.handle(
        _payloadSha256Meta,
        payloadSha256.isAcceptableOrUnknown(
          data['payload_sha256']!,
          _payloadSha256Meta,
        ),
      );
    } else if (isInserting) {
      context.missing(_payloadSha256Meta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('sync_state')) {
      context.handle(
        _syncStateMeta,
        syncState.isAcceptableOrUnknown(data['sync_state']!, _syncStateMeta),
      );
    } else if (isInserting) {
      context.missing(_syncStateMeta);
    }
    if (data.containsKey('retry_count')) {
      context.handle(
        _retryCountMeta,
        retryCount.isAcceptableOrUnknown(data['retry_count']!, _retryCountMeta),
      );
    }
    if (data.containsKey('error_message')) {
      context.handle(
        _errorMessageMeta,
        errorMessage.isAcceptableOrUnknown(
          data['error_message']!,
          _errorMessageMeta,
        ),
      );
    }
    if (data.containsKey('synced_at')) {
      context.handle(
        _syncedAtMeta,
        syncedAt.isAcceptableOrUnknown(data['synced_at']!, _syncedAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  MutationJournalData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MutationJournalData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      path: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}path'],
      )!,
      mutationType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}mutation_type'],
      )!,
      payload: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}payload'],
      )!,
      payloadSha256: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}payload_sha256'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      syncState: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sync_state'],
      )!,
      retryCount: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}retry_count'],
      )!,
      errorMessage: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}error_message'],
      ),
      syncedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}synced_at'],
      ),
    );
  }

  @override
  $MutationJournalTable createAlias(String alias) {
    return $MutationJournalTable(attachedDatabase, alias);
  }
}

class MutationJournalData extends DataClass
    implements Insertable<MutationJournalData> {
  /// Auto-incrementing primary key
  final int id;

  /// Vault file path being mutated
  final String path;

  /// 'upsert', 'delete', or 'status_change'
  final String mutationType;

  /// Payload content (full file markdown or change delta)
  final String payload;

  /// SHA-256 hash of the payload for integrity checking
  final String payloadSha256;

  /// Timestamp when mutation occurred on mobile device
  final DateTime createdAt;

  /// 'pending', 'in_flight', 'synced', 'failed'
  final String syncState;

  /// Number of sync attempts
  final int retryCount;

  /// Error message if last sync attempt failed
  final String? errorMessage;

  /// Timestamp when successfully drained to remote vault
  final DateTime? syncedAt;
  const MutationJournalData({
    required this.id,
    required this.path,
    required this.mutationType,
    required this.payload,
    required this.payloadSha256,
    required this.createdAt,
    required this.syncState,
    required this.retryCount,
    this.errorMessage,
    this.syncedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['path'] = Variable<String>(path);
    map['mutation_type'] = Variable<String>(mutationType);
    map['payload'] = Variable<String>(payload);
    map['payload_sha256'] = Variable<String>(payloadSha256);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['sync_state'] = Variable<String>(syncState);
    map['retry_count'] = Variable<int>(retryCount);
    if (!nullToAbsent || errorMessage != null) {
      map['error_message'] = Variable<String>(errorMessage);
    }
    if (!nullToAbsent || syncedAt != null) {
      map['synced_at'] = Variable<DateTime>(syncedAt);
    }
    return map;
  }

  MutationJournalCompanion toCompanion(bool nullToAbsent) {
    return MutationJournalCompanion(
      id: Value(id),
      path: Value(path),
      mutationType: Value(mutationType),
      payload: Value(payload),
      payloadSha256: Value(payloadSha256),
      createdAt: Value(createdAt),
      syncState: Value(syncState),
      retryCount: Value(retryCount),
      errorMessage: errorMessage == null && nullToAbsent
          ? const Value.absent()
          : Value(errorMessage),
      syncedAt: syncedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(syncedAt),
    );
  }

  factory MutationJournalData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MutationJournalData(
      id: serializer.fromJson<int>(json['id']),
      path: serializer.fromJson<String>(json['path']),
      mutationType: serializer.fromJson<String>(json['mutationType']),
      payload: serializer.fromJson<String>(json['payload']),
      payloadSha256: serializer.fromJson<String>(json['payloadSha256']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      syncState: serializer.fromJson<String>(json['syncState']),
      retryCount: serializer.fromJson<int>(json['retryCount']),
      errorMessage: serializer.fromJson<String?>(json['errorMessage']),
      syncedAt: serializer.fromJson<DateTime?>(json['syncedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'path': serializer.toJson<String>(path),
      'mutationType': serializer.toJson<String>(mutationType),
      'payload': serializer.toJson<String>(payload),
      'payloadSha256': serializer.toJson<String>(payloadSha256),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'syncState': serializer.toJson<String>(syncState),
      'retryCount': serializer.toJson<int>(retryCount),
      'errorMessage': serializer.toJson<String?>(errorMessage),
      'syncedAt': serializer.toJson<DateTime?>(syncedAt),
    };
  }

  MutationJournalData copyWith({
    int? id,
    String? path,
    String? mutationType,
    String? payload,
    String? payloadSha256,
    DateTime? createdAt,
    String? syncState,
    int? retryCount,
    Value<String?> errorMessage = const Value.absent(),
    Value<DateTime?> syncedAt = const Value.absent(),
  }) => MutationJournalData(
    id: id ?? this.id,
    path: path ?? this.path,
    mutationType: mutationType ?? this.mutationType,
    payload: payload ?? this.payload,
    payloadSha256: payloadSha256 ?? this.payloadSha256,
    createdAt: createdAt ?? this.createdAt,
    syncState: syncState ?? this.syncState,
    retryCount: retryCount ?? this.retryCount,
    errorMessage: errorMessage.present ? errorMessage.value : this.errorMessage,
    syncedAt: syncedAt.present ? syncedAt.value : this.syncedAt,
  );
  MutationJournalData copyWithCompanion(MutationJournalCompanion data) {
    return MutationJournalData(
      id: data.id.present ? data.id.value : this.id,
      path: data.path.present ? data.path.value : this.path,
      mutationType: data.mutationType.present
          ? data.mutationType.value
          : this.mutationType,
      payload: data.payload.present ? data.payload.value : this.payload,
      payloadSha256: data.payloadSha256.present
          ? data.payloadSha256.value
          : this.payloadSha256,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      syncState: data.syncState.present ? data.syncState.value : this.syncState,
      retryCount: data.retryCount.present
          ? data.retryCount.value
          : this.retryCount,
      errorMessage: data.errorMessage.present
          ? data.errorMessage.value
          : this.errorMessage,
      syncedAt: data.syncedAt.present ? data.syncedAt.value : this.syncedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MutationJournalData(')
          ..write('id: $id, ')
          ..write('path: $path, ')
          ..write('mutationType: $mutationType, ')
          ..write('payload: $payload, ')
          ..write('payloadSha256: $payloadSha256, ')
          ..write('createdAt: $createdAt, ')
          ..write('syncState: $syncState, ')
          ..write('retryCount: $retryCount, ')
          ..write('errorMessage: $errorMessage, ')
          ..write('syncedAt: $syncedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    path,
    mutationType,
    payload,
    payloadSha256,
    createdAt,
    syncState,
    retryCount,
    errorMessage,
    syncedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MutationJournalData &&
          other.id == this.id &&
          other.path == this.path &&
          other.mutationType == this.mutationType &&
          other.payload == this.payload &&
          other.payloadSha256 == this.payloadSha256 &&
          other.createdAt == this.createdAt &&
          other.syncState == this.syncState &&
          other.retryCount == this.retryCount &&
          other.errorMessage == this.errorMessage &&
          other.syncedAt == this.syncedAt);
}

class MutationJournalCompanion extends UpdateCompanion<MutationJournalData> {
  final Value<int> id;
  final Value<String> path;
  final Value<String> mutationType;
  final Value<String> payload;
  final Value<String> payloadSha256;
  final Value<DateTime> createdAt;
  final Value<String> syncState;
  final Value<int> retryCount;
  final Value<String?> errorMessage;
  final Value<DateTime?> syncedAt;
  const MutationJournalCompanion({
    this.id = const Value.absent(),
    this.path = const Value.absent(),
    this.mutationType = const Value.absent(),
    this.payload = const Value.absent(),
    this.payloadSha256 = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.syncState = const Value.absent(),
    this.retryCount = const Value.absent(),
    this.errorMessage = const Value.absent(),
    this.syncedAt = const Value.absent(),
  });
  MutationJournalCompanion.insert({
    this.id = const Value.absent(),
    required String path,
    required String mutationType,
    required String payload,
    required String payloadSha256,
    required DateTime createdAt,
    required String syncState,
    this.retryCount = const Value.absent(),
    this.errorMessage = const Value.absent(),
    this.syncedAt = const Value.absent(),
  }) : path = Value(path),
       mutationType = Value(mutationType),
       payload = Value(payload),
       payloadSha256 = Value(payloadSha256),
       createdAt = Value(createdAt),
       syncState = Value(syncState);
  static Insertable<MutationJournalData> custom({
    Expression<int>? id,
    Expression<String>? path,
    Expression<String>? mutationType,
    Expression<String>? payload,
    Expression<String>? payloadSha256,
    Expression<DateTime>? createdAt,
    Expression<String>? syncState,
    Expression<int>? retryCount,
    Expression<String>? errorMessage,
    Expression<DateTime>? syncedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (path != null) 'path': path,
      if (mutationType != null) 'mutation_type': mutationType,
      if (payload != null) 'payload': payload,
      if (payloadSha256 != null) 'payload_sha256': payloadSha256,
      if (createdAt != null) 'created_at': createdAt,
      if (syncState != null) 'sync_state': syncState,
      if (retryCount != null) 'retry_count': retryCount,
      if (errorMessage != null) 'error_message': errorMessage,
      if (syncedAt != null) 'synced_at': syncedAt,
    });
  }

  MutationJournalCompanion copyWith({
    Value<int>? id,
    Value<String>? path,
    Value<String>? mutationType,
    Value<String>? payload,
    Value<String>? payloadSha256,
    Value<DateTime>? createdAt,
    Value<String>? syncState,
    Value<int>? retryCount,
    Value<String?>? errorMessage,
    Value<DateTime?>? syncedAt,
  }) {
    return MutationJournalCompanion(
      id: id ?? this.id,
      path: path ?? this.path,
      mutationType: mutationType ?? this.mutationType,
      payload: payload ?? this.payload,
      payloadSha256: payloadSha256 ?? this.payloadSha256,
      createdAt: createdAt ?? this.createdAt,
      syncState: syncState ?? this.syncState,
      retryCount: retryCount ?? this.retryCount,
      errorMessage: errorMessage ?? this.errorMessage,
      syncedAt: syncedAt ?? this.syncedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (path.present) {
      map['path'] = Variable<String>(path.value);
    }
    if (mutationType.present) {
      map['mutation_type'] = Variable<String>(mutationType.value);
    }
    if (payload.present) {
      map['payload'] = Variable<String>(payload.value);
    }
    if (payloadSha256.present) {
      map['payload_sha256'] = Variable<String>(payloadSha256.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (syncState.present) {
      map['sync_state'] = Variable<String>(syncState.value);
    }
    if (retryCount.present) {
      map['retry_count'] = Variable<int>(retryCount.value);
    }
    if (errorMessage.present) {
      map['error_message'] = Variable<String>(errorMessage.value);
    }
    if (syncedAt.present) {
      map['synced_at'] = Variable<DateTime>(syncedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('MutationJournalCompanion(')
          ..write('id: $id, ')
          ..write('path: $path, ')
          ..write('mutationType: $mutationType, ')
          ..write('payload: $payload, ')
          ..write('payloadSha256: $payloadSha256, ')
          ..write('createdAt: $createdAt, ')
          ..write('syncState: $syncState, ')
          ..write('retryCount: $retryCount, ')
          ..write('errorMessage: $errorMessage, ')
          ..write('syncedAt: $syncedAt')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $CachedNotesTable cachedNotes = $CachedNotesTable(this);
  late final $MutationJournalTable mutationJournal = $MutationJournalTable(
    this,
  );
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    cachedNotes,
    mutationJournal,
  ];
}

typedef $$CachedNotesTableCreateCompanionBuilder =
    CachedNotesCompanion Function({
      required String path,
      required String title,
      required String status,
      required String content,
      required String frontmatterYaml,
      Value<String?> etag,
      Value<DateTime?> lastModifiedRemote,
      required DateTime lastCachedLocally,
      Value<bool> isDirty,
      Value<int> rowid,
    });
typedef $$CachedNotesTableUpdateCompanionBuilder =
    CachedNotesCompanion Function({
      Value<String> path,
      Value<String> title,
      Value<String> status,
      Value<String> content,
      Value<String> frontmatterYaml,
      Value<String?> etag,
      Value<DateTime?> lastModifiedRemote,
      Value<DateTime> lastCachedLocally,
      Value<bool> isDirty,
      Value<int> rowid,
    });

class $$CachedNotesTableFilterComposer
    extends Composer<_$AppDatabase, $CachedNotesTable> {
  $$CachedNotesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get path => $composableBuilder(
    column: $table.path,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get content => $composableBuilder(
    column: $table.content,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get frontmatterYaml => $composableBuilder(
    column: $table.frontmatterYaml,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get etag => $composableBuilder(
    column: $table.etag,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get lastModifiedRemote => $composableBuilder(
    column: $table.lastModifiedRemote,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get lastCachedLocally => $composableBuilder(
    column: $table.lastCachedLocally,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get isDirty => $composableBuilder(
    column: $table.isDirty,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedNotesTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedNotesTable> {
  $$CachedNotesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get path => $composableBuilder(
    column: $table.path,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get content => $composableBuilder(
    column: $table.content,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get frontmatterYaml => $composableBuilder(
    column: $table.frontmatterYaml,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get etag => $composableBuilder(
    column: $table.etag,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get lastModifiedRemote => $composableBuilder(
    column: $table.lastModifiedRemote,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get lastCachedLocally => $composableBuilder(
    column: $table.lastCachedLocally,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get isDirty => $composableBuilder(
    column: $table.isDirty,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedNotesTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedNotesTable> {
  $$CachedNotesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get path =>
      $composableBuilder(column: $table.path, builder: (column) => column);

  GeneratedColumn<String> get title =>
      $composableBuilder(column: $table.title, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<String> get content =>
      $composableBuilder(column: $table.content, builder: (column) => column);

  GeneratedColumn<String> get frontmatterYaml => $composableBuilder(
    column: $table.frontmatterYaml,
    builder: (column) => column,
  );

  GeneratedColumn<String> get etag =>
      $composableBuilder(column: $table.etag, builder: (column) => column);

  GeneratedColumn<DateTime> get lastModifiedRemote => $composableBuilder(
    column: $table.lastModifiedRemote,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get lastCachedLocally => $composableBuilder(
    column: $table.lastCachedLocally,
    builder: (column) => column,
  );

  GeneratedColumn<bool> get isDirty =>
      $composableBuilder(column: $table.isDirty, builder: (column) => column);
}

class $$CachedNotesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedNotesTable,
          CachedNote,
          $$CachedNotesTableFilterComposer,
          $$CachedNotesTableOrderingComposer,
          $$CachedNotesTableAnnotationComposer,
          $$CachedNotesTableCreateCompanionBuilder,
          $$CachedNotesTableUpdateCompanionBuilder,
          (
            CachedNote,
            BaseReferences<_$AppDatabase, $CachedNotesTable, CachedNote>,
          ),
          CachedNote,
          PrefetchHooks Function()
        > {
  $$CachedNotesTableTableManager(_$AppDatabase db, $CachedNotesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedNotesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedNotesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedNotesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> path = const Value.absent(),
                Value<String> title = const Value.absent(),
                Value<String> status = const Value.absent(),
                Value<String> content = const Value.absent(),
                Value<String> frontmatterYaml = const Value.absent(),
                Value<String?> etag = const Value.absent(),
                Value<DateTime?> lastModifiedRemote = const Value.absent(),
                Value<DateTime> lastCachedLocally = const Value.absent(),
                Value<bool> isDirty = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedNotesCompanion(
                path: path,
                title: title,
                status: status,
                content: content,
                frontmatterYaml: frontmatterYaml,
                etag: etag,
                lastModifiedRemote: lastModifiedRemote,
                lastCachedLocally: lastCachedLocally,
                isDirty: isDirty,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String path,
                required String title,
                required String status,
                required String content,
                required String frontmatterYaml,
                Value<String?> etag = const Value.absent(),
                Value<DateTime?> lastModifiedRemote = const Value.absent(),
                required DateTime lastCachedLocally,
                Value<bool> isDirty = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedNotesCompanion.insert(
                path: path,
                title: title,
                status: status,
                content: content,
                frontmatterYaml: frontmatterYaml,
                etag: etag,
                lastModifiedRemote: lastModifiedRemote,
                lastCachedLocally: lastCachedLocally,
                isDirty: isDirty,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$CachedNotesTable, CachedNote>(table),
                  BaseReferences<_$AppDatabase, $CachedNotesTable, CachedNote>(
                    db,
                    table,
                    e,
                  ),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedNotesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedNotesTable,
      CachedNote,
      $$CachedNotesTableFilterComposer,
      $$CachedNotesTableOrderingComposer,
      $$CachedNotesTableAnnotationComposer,
      $$CachedNotesTableCreateCompanionBuilder,
      $$CachedNotesTableUpdateCompanionBuilder,
      (
        CachedNote,
        BaseReferences<_$AppDatabase, $CachedNotesTable, CachedNote>,
      ),
      CachedNote,
      PrefetchHooks Function()
    >;
typedef $$MutationJournalTableCreateCompanionBuilder =
    MutationJournalCompanion Function({
      Value<int> id,
      required String path,
      required String mutationType,
      required String payload,
      required String payloadSha256,
      required DateTime createdAt,
      required String syncState,
      Value<int> retryCount,
      Value<String?> errorMessage,
      Value<DateTime?> syncedAt,
    });
typedef $$MutationJournalTableUpdateCompanionBuilder =
    MutationJournalCompanion Function({
      Value<int> id,
      Value<String> path,
      Value<String> mutationType,
      Value<String> payload,
      Value<String> payloadSha256,
      Value<DateTime> createdAt,
      Value<String> syncState,
      Value<int> retryCount,
      Value<String?> errorMessage,
      Value<DateTime?> syncedAt,
    });

class $$MutationJournalTableFilterComposer
    extends Composer<_$AppDatabase, $MutationJournalTable> {
  $$MutationJournalTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get path => $composableBuilder(
    column: $table.path,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get mutationType => $composableBuilder(
    column: $table.mutationType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get payload => $composableBuilder(
    column: $table.payload,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get payloadSha256 => $composableBuilder(
    column: $table.payloadSha256,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get syncState => $composableBuilder(
    column: $table.syncState,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get retryCount => $composableBuilder(
    column: $table.retryCount,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get errorMessage => $composableBuilder(
    column: $table.errorMessage,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get syncedAt => $composableBuilder(
    column: $table.syncedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$MutationJournalTableOrderingComposer
    extends Composer<_$AppDatabase, $MutationJournalTable> {
  $$MutationJournalTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get path => $composableBuilder(
    column: $table.path,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get mutationType => $composableBuilder(
    column: $table.mutationType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get payload => $composableBuilder(
    column: $table.payload,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get payloadSha256 => $composableBuilder(
    column: $table.payloadSha256,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get syncState => $composableBuilder(
    column: $table.syncState,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get retryCount => $composableBuilder(
    column: $table.retryCount,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get errorMessage => $composableBuilder(
    column: $table.errorMessage,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get syncedAt => $composableBuilder(
    column: $table.syncedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$MutationJournalTableAnnotationComposer
    extends Composer<_$AppDatabase, $MutationJournalTable> {
  $$MutationJournalTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get path =>
      $composableBuilder(column: $table.path, builder: (column) => column);

  GeneratedColumn<String> get mutationType => $composableBuilder(
    column: $table.mutationType,
    builder: (column) => column,
  );

  GeneratedColumn<String> get payload =>
      $composableBuilder(column: $table.payload, builder: (column) => column);

  GeneratedColumn<String> get payloadSha256 => $composableBuilder(
    column: $table.payloadSha256,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get syncState =>
      $composableBuilder(column: $table.syncState, builder: (column) => column);

  GeneratedColumn<int> get retryCount => $composableBuilder(
    column: $table.retryCount,
    builder: (column) => column,
  );

  GeneratedColumn<String> get errorMessage => $composableBuilder(
    column: $table.errorMessage,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get syncedAt =>
      $composableBuilder(column: $table.syncedAt, builder: (column) => column);
}

class $$MutationJournalTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $MutationJournalTable,
          MutationJournalData,
          $$MutationJournalTableFilterComposer,
          $$MutationJournalTableOrderingComposer,
          $$MutationJournalTableAnnotationComposer,
          $$MutationJournalTableCreateCompanionBuilder,
          $$MutationJournalTableUpdateCompanionBuilder,
          (
            MutationJournalData,
            BaseReferences<
              _$AppDatabase,
              $MutationJournalTable,
              MutationJournalData
            >,
          ),
          MutationJournalData,
          PrefetchHooks Function()
        > {
  $$MutationJournalTableTableManager(
    _$AppDatabase db,
    $MutationJournalTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$MutationJournalTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$MutationJournalTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$MutationJournalTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> path = const Value.absent(),
                Value<String> mutationType = const Value.absent(),
                Value<String> payload = const Value.absent(),
                Value<String> payloadSha256 = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<String> syncState = const Value.absent(),
                Value<int> retryCount = const Value.absent(),
                Value<String?> errorMessage = const Value.absent(),
                Value<DateTime?> syncedAt = const Value.absent(),
              }) => MutationJournalCompanion(
                id: id,
                path: path,
                mutationType: mutationType,
                payload: payload,
                payloadSha256: payloadSha256,
                createdAt: createdAt,
                syncState: syncState,
                retryCount: retryCount,
                errorMessage: errorMessage,
                syncedAt: syncedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String path,
                required String mutationType,
                required String payload,
                required String payloadSha256,
                required DateTime createdAt,
                required String syncState,
                Value<int> retryCount = const Value.absent(),
                Value<String?> errorMessage = const Value.absent(),
                Value<DateTime?> syncedAt = const Value.absent(),
              }) => MutationJournalCompanion.insert(
                id: id,
                path: path,
                mutationType: mutationType,
                payload: payload,
                payloadSha256: payloadSha256,
                createdAt: createdAt,
                syncState: syncState,
                retryCount: retryCount,
                errorMessage: errorMessage,
                syncedAt: syncedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$MutationJournalTable, MutationJournalData>(
                    table,
                  ),
                  BaseReferences<
                    _$AppDatabase,
                    $MutationJournalTable,
                    MutationJournalData
                  >(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$MutationJournalTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $MutationJournalTable,
      MutationJournalData,
      $$MutationJournalTableFilterComposer,
      $$MutationJournalTableOrderingComposer,
      $$MutationJournalTableAnnotationComposer,
      $$MutationJournalTableCreateCompanionBuilder,
      $$MutationJournalTableUpdateCompanionBuilder,
      (
        MutationJournalData,
        BaseReferences<
          _$AppDatabase,
          $MutationJournalTable,
          MutationJournalData
        >,
      ),
      MutationJournalData,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$CachedNotesTableTableManager get cachedNotes =>
      $$CachedNotesTableTableManager(_db, _db.cachedNotes);
  $$MutationJournalTableTableManager get mutationJournal =>
      $$MutationJournalTableTableManager(_db, _db.mutationJournal);
}
