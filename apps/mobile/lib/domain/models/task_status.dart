/// Task lifecycle statuses in Chrysalis.
enum TaskStatus {
  todo('todo'),
  inProgress('in-progress'),
  done('done'),
  archived('archived');

  final String yamlValue;
  const TaskStatus(this.yamlValue);

  static TaskStatus fromString(String raw) {
    final normalized = raw.trim().toLowerCase();
    switch (normalized) {
      case 'todo':
        return TaskStatus.todo;
      case 'in-progress':
      case 'inprogress':
      case 'in_progress':
        return TaskStatus.inProgress;
      case 'done':
      case 'completed':
        return TaskStatus.done;
      case 'archived':
      case 'archive':
        return TaskStatus.archived;
      default:
        throw ArgumentError('Invalid TaskStatus: "$raw". Allowed: todo, in-progress, done, archived');
    }
  }

  bool canTransitionTo(TaskStatus target) {
    if (this == target) return true;
    switch (this) {
      case TaskStatus.todo:
        return target == TaskStatus.inProgress || target == TaskStatus.done || target == TaskStatus.archived;
      case TaskStatus.inProgress:
        return target == TaskStatus.done || target == TaskStatus.todo || target == TaskStatus.archived;
      case TaskStatus.done:
        return target == TaskStatus.archived || target == TaskStatus.todo;
      case TaskStatus.archived:
        return target == TaskStatus.todo;
    }
  }
}
