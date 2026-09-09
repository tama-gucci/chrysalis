/// Base domain exceptions for Chrysalis.
library;

abstract class ChrysalisException implements Exception {
  final String message;
  final dynamic cause;

  const ChrysalisException(this.message, [this.cause]);

  @override
  String toString() => '$runtimeType: $message${cause != null ? ' (Cause: $cause)' : ''}';
}

/// Thrown when parsing or serializing TaskNotes fails.
class TaskParseException extends ChrysalisException {
  const TaskParseException(super.message, [super.cause]);
}

/// Thrown when vault storage operations fail.
class VaultStorageException extends ChrysalisException {
  const VaultStorageException(super.message, [super.cause]);
}

/// Thrown when orchestrator communication fails.
class OrchestratorTransportException extends ChrysalisException {
  const OrchestratorTransportException(super.message, [super.cause]);
}

/// Thrown when biometrics ingestion fails.
class BiometricsException extends ChrysalisException {
  const BiometricsException(super.message, [super.cause]);
}
