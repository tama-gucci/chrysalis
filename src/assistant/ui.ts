/** One queue shared by native settings, permission, questionnaire and quiz views. */
export class UIQueue {
  private tail: Promise<unknown> = Promise.resolve();
  run<T>(view: () => Promise<T>): Promise<T> {
    const next = this.tail.then(view, view);
    this.tail = next.catch(() => undefined);
    return next;
  }
}
export const assistantUI = new UIQueue();
