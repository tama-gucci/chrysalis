import { BrowserSecretGuard } from "./secret-guard.ts";
export function youtubeURL(input: string): string {
  const u = new URL(input);
  if (u.protocol !== "https:" || u.username || u.password || u.port)
    throw Error("Choose a public HTTPS YouTube URL");
  const id =
    u.hostname === "youtu.be"
      ? u.pathname.slice(1)
      : ["youtube.com", "www.youtube.com", "m.youtube.com"].includes(u.hostname)
        ? (u.searchParams.get("v") ??
          (/^\/(shorts|embed)\//.test(u.pathname)
            ? u.pathname.split("/")[2]
            : ""))
        : "";
  if (!/^[a-zA-Z0-9_-]{11}$/.test(id ?? ""))
    throw Error("Unsupported YouTube URL");
  return "https://www.youtube.com/watch?v=" + id;
}
/** Cookies remain inside the bridge/client closure. No API or other-provider fallback. */
export async function analyzeYouTube(
  url: string,
  question: string,
  ports: {
    cookies: () => Promise<Record<string, string>>;
    query: (
      question: string,
      cookies: Record<string, string>,
      options: any,
    ) => Promise<string>;
  },
  signal?: AbortSignal,
) {
  const canonical = youtubeURL(url);
  if (!question || question.length > 4000)
    throw Error("Use a bounded video question");
  try {
    const cookies = await ports.cookies();
    if (!cookies["__Secure-1PSID"])
      return {
        status: "unavailable",
        reason: "native_sign_in_required",
        verified: false,
      };
    const guard = new BrowserSecretGuard();
    guard.configure(Object.values(cookies));
    const answer = guard
      .text(
        await ports.query(question, cookies, {
          youtubeUrl: canonical,
          signal,
          timeoutMs: 60000,
        }),
      )
      .slice(0, 16000);
    return {
      status: "ok",
      answer,
      source: canonical,
      retrieved_at: Date.now(),
      verified: false,
      limitations:
        "Experimental Gemini Web response; video coverage and accuracy require review",
    };
  } catch {
    return {
      status: "unavailable",
      reason: signal?.aborted ? "cancelled" : "login_quota_or_protocol_failure",
      verified: false,
    };
  }
}
