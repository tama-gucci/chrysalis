/** Hard call/concurrency limits; provider token accounting is separately observed. */
export class UsageBudget {
  private used = 0;
  private running = 0;
  private observations: any[] = [];
  readonly calls: number;
  readonly concurrency: number;
  constructor(calls: number, concurrency: number) {
    if (
      !Number.isSafeInteger(calls) ||
      calls < 1 ||
      calls > 100 ||
      !Number.isSafeInteger(concurrency) ||
      concurrency < 1 ||
      concurrency > 4
    )
      throw Error("Invalid usage budget");
    this.calls = calls;
    this.concurrency = concurrency;
  }
  reserve(component: string, turns = 1) {
    if (
      !Number.isSafeInteger(turns) ||
      turns < 1 ||
      this.used + turns > this.calls
    )
      throw Error("Session call limit reached");
    if (this.running >= this.concurrency)
      throw Error("Optional work is already running");
    this.used += turns;
    this.running++;
    let released = false;
    return (usage?: unknown) => {
      if (!released) {
        released = true;
        this.running--;
        this.observations.push({ component, usage: usage ?? null });
      }
    };
  }
  status() {
    return {
      reservedCalls: this.used,
      active: this.running,
      callLimit: this.calls,
      observations: structuredClone(this.observations),
      tokensKnown:
        this.observations.length > 0 &&
        this.observations.every((o) => o.usage !== null),
    };
  }
}
const budgets = new Map<string, UsageBudget>();
export function sharedBudget(
  state: string,
  calls: number,
  concurrency: number,
) {
  const current = budgets.get(state);
  if (
    current &&
    (current.calls !== calls || current.concurrency !== concurrency)
  ) {
    if (current.status().active)
      throw Error("Wait for optional work before changing limits");
    return resetBudget(state, calls, concurrency);
  }
  if (!current) budgets.set(state, new UsageBudget(calls, concurrency));
  return budgets.get(state)!;
}
export function resetBudget(state: string, calls: number, concurrency: number) {
  if (budgets.get(state)?.status().active)
    throw Error("Optional work is still active");
  const b = new UsageBudget(calls, concurrency);
  budgets.set(state, b);
  return b;
}
