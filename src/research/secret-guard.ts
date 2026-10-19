/** Bounded literal matching. Secrets never become diagnostic-bearing regular expressions. */
type Node = { next: Map<string, number>; fail: number; length: number };
export class BrowserSecretGuard {
  private patterns: string[] = [];
  private nodes: Node[] = [{ next: new Map(), fail: 0, length: 0 }];
  private failed = false;
  enabled = false;
  configure(values: string[]) {
    try {
      if (this.failed) throw Error("failed");
      const patterns = new Set(this.patterns);
      for (const v of values)
        if (v) {
          for (const p of [
            v,
            v.trim(),
            v.replace(/\s+/g, " ").trim(),
            encodeURIComponent(v),
            encodeURI(v),
            Buffer.from(v).toString("base64"),
            JSON.stringify(v).slice(1, -1),
            Buffer.from(v).toString("hex"),
          ])
            if (p) patterns.add(p);
        }
      if (
        patterns.size > 16000 ||
        [...patterns].reduce((n, p) => n + p.length, 0) > 512 * 1024
      )
        throw Error("limit");
      const nodes: Node[] = [{ next: new Map(), fail: 0, length: 0 }];
      for (const p of patterns) {
        let n = 0;
        for (let i = 0; i < p.length; i++) {
          const c = p[i];
          if (!nodes[n].next.has(c)) {
            if (nodes.length >= 131072) throw Error("limit");
            nodes[n].next.set(c, nodes.length);
            nodes.push({ next: new Map(), fail: 0, length: 0 });
          }
          n = nodes[n].next.get(c)!;
        }
        nodes[n].length = Math.max(nodes[n].length, p.length);
      }
      const queue = [...nodes[0].next.values()];
      for (let i = 0; i < queue.length; i++) {
        const n = queue[i];
        for (const [c, child] of nodes[n].next) {
          let f = nodes[n].fail;
          while (f && !nodes[f].next.has(c)) f = nodes[f].fail;
          nodes[child].fail = nodes[f].next.get(c) ?? 0;
          nodes[child].length = Math.max(
            nodes[child].length,
            nodes[nodes[child].fail].length,
          );
          queue.push(child);
        }
      }
      this.patterns = [...patterns];
      this.nodes = nodes;
      this.enabled = patterns.size > 0;
    } catch {
      this.failed = true;
      this.enabled = true;
      throw Error("Private browser redaction unavailable; automation refused");
    }
  }
  text(value: string) {
    try {
      if (this.failed || value.length > 1024 * 1024) throw Error("limit");
      if (!this.enabled) return value;
      const coverage = new Int32Array(value.length + 1);
      let n = 0;
      for (let i = 0; i < value.length; i++) {
        const c = value[i];
        while (n && !this.nodes[n].next.has(c)) n = this.nodes[n].fail;
        n = this.nodes[n].next.get(c) ?? 0;
        const length = this.nodes[n].length;
        if (length) {
          coverage[i - length + 1]++;
          coverage[i + 1]--;
        }
      }
      let depth = 0,
        hidden = false,
        output = "";
      for (let i = 0; i < value.length; i++) {
        depth += coverage[i];
        if (depth > 0) {
          if (!hidden) output += "[private]";
          hidden = true;
        } else {
          output += value[i];
          hidden = false;
        }
      }
      // A fixed marker or joined fragments must never recreate a secret.
      n = 0;
      for (let i = 0; i < output.length; i++) {
        const c = output[i];
        while (n && !this.nodes[n].next.has(c)) n = this.nodes[n].fail;
        n = this.nodes[n].next.get(c) ?? 0;
        if (this.nodes[n].length) return "";
      }
      return output;
    } catch {
      throw Error("Private browser text unavailable; automation refused");
    }
  }
  url(value: string) {
    if (!this.enabled) return value;
    try {
      const u = new URL(value);
      return this.text(u.origin + u.pathname);
    } catch {
      return "";
    }
  }
}
