import { OAuth2Client } from "google-auth-library";
import { createServer } from "node:http";
import { randomBytes } from "node:crypto";
import { spawn } from "node:child_process";
import { confined } from "../../platforms/filesystem.ts";
import { vaultState } from "../../storage/context.ts";
import type { RuntimeContext } from "../../contracts/types.ts";
import type { Credentials, Instance, SecretStore } from "../contracts.ts";
import { providerLock } from "../locks.ts";

export function openBrowser(url: string) {
  if (!url.startsWith("https://accounts.google.com/"))
    throw Error("invalid_authorization_endpoint");
  const [cmd, args]: [string, string[]] =
    process.platform === "win32"
      ? ["rundll32.exe", ["url.dll,FileProtocolHandler", url]]
      : process.platform === "darwin"
        ? ["open", [url]]
        : ["xdg-open", [url]];
  const child = spawn(cmd, args, {
    windowsHide: true,
    shell: false,
    stdio: "ignore",
  });
  child.on("error", () => {});
}
/** Invoked only by the native operator walkthrough. Never returns an authorization code to Pi. */
export async function authorize(
  credentials: Credentials,
  scopes: string[],
  showURL: (url: string) => void,
  signal?: AbortSignal,
  registeredRedirect?: string,
  launch = openBrowser,
): Promise<Credentials> {
  if (!credentials.client_id || !credentials.client_secret)
    throw Error("invalid_oauth_client");
  const state = randomBytes(32).toString("hex"),
    client = new OAuth2Client({
      clientId: credentials.client_id,
      clientSecret: credentials.client_secret,
      transporterOptions: { timeout: 10000, retry: false, signal },
    });
  const server = createServer();
  if (
    registeredRedirect &&
    !/^http:\/\/127\.0\.0\.1:\d+\/callback$/.test(registeredRedirect)
  )
    throw Error("invalid_registered_callback");
  const port = registeredRedirect
    ? Number(new URL(registeredRedirect).port)
    : 0;
  if (
    !Number.isInteger(port) ||
    port < 0 ||
    port > 65535 ||
    (registeredRedirect && !port)
  )
    throw Error("invalid_registered_callback");
  await new Promise<void>((resolve, reject) => {
    server.once("error", () => reject(Error("oauth_callback_unavailable")));
    server.listen(port, "127.0.0.1", () => resolve());
  });
  const address = server.address();
  if (!address || typeof address === "string") {
    server.close();
    throw Error("oauth_callback_unavailable");
  }
  const redirect_uri = `http://127.0.0.1:${address.port}/callback`;
  const { codeVerifier, codeChallenge } =
    await client.generateCodeVerifierAsync();
  try {
    const code = await new Promise<string>((resolve, reject) => {
      const timer = setTimeout(() => finish(undefined), 180000);
      const abort = () => finish(undefined);
      let done = false;
      const finish = (code: string | undefined) => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        signal?.removeEventListener("abort", abort);
        code ? resolve(code) : reject(Error("oauth_canceled_or_expired"));
      };
      signal?.addEventListener("abort", abort, { once: true });
      server.on("request", (req, res) => {
        const url = new URL(req.url ?? "/", redirect_uri);
        if (
          req.method !== "GET" ||
          url.pathname !== "/callback" ||
          url.searchParams.get("state") !== state
        ) {
          res.writeHead(400).end("Invalid callback");
          return;
        }
        res
          .writeHead(200, {
            "Content-Type": "text/plain",
            "Cache-Control": "no-store",
          })
          .end("Return to chrysalis. You may close this tab.");
        finish(url.searchParams.get("code") ?? undefined);
      });
      if (signal?.aborted) {
        finish(undefined);
        return;
      }
      const url = client.generateAuthUrl({
        redirect_uri,
        access_type: "offline",
        scope: ["openid", ...scopes],
        state,
        code_challenge: codeChallenge,
        code_challenge_method: "S256" as any,
        prompt: "consent",
      });
      showURL(url);
      launch(url);
    });
    const { tokens } = await client.getToken({
      code,
      codeVerifier,
      redirect_uri,
    });
    if (
      !tokens.refresh_token ||
      !tokens.access_token ||
      scopes.some((s) => !tokens.scope?.split(" ").includes(s))
    )
      throw Error("oauth_missing_scope_or_refresh_token");
    if (!tokens.id_token) throw Error("oauth_identity_missing");
    const identity = await client.verifyIdToken({
      idToken: tokens.id_token,
      audience: credentials.client_id,
    });
    const subject = identity.getPayload()?.sub;
    if (!subject) throw Error("oauth_identity_missing");
    return {
      ...credentials,
      google_subject: subject,
      refresh_token: tokens.refresh_token,
      access_token: tokens.access_token,
      expiry_date: tokens.expiry_date ?? undefined,
    };
  } catch {
    throw Error("oauth_authorization_incomplete");
  } finally {
    server.closeAllConnections();
    server.close();
  }
}
const refreshes = new Map<string, Promise<unknown>>();
/** Refresh and native disposal must use the same cross-process credential lock. */
export function credentialLock<T>(
  ctx: RuntimeContext,
  secretId: string,
  action: () => T | Promise<T>,
) {
  return providerLock(
    ctx,
    confined(vaultState(ctx), "provider-locks"),
    secretId,
    action,
  );
}
export async function accessToken(
  ctx: RuntimeContext,
  instance: Instance,
  secrets: SecretStore,
): Promise<string> {
  if (ctx.signal?.aborted) throw Error("provider_canceled_or_timeout");
  const cached = await secrets.get(instance.secret_id);
  if (
    cached?.client_id &&
    cached.client_secret &&
    cached.refresh_token &&
    cached.access_token &&
    (cached.expiry_date ?? 0) > Date.now() + 60000
  )
    return cached.access_token;
  const root = confined(vaultState(ctx), "provider-locks"),
    key = root + "/" + instance.secret_id;
  const next = (refreshes.get(key) ?? Promise.resolve())
    .catch(() => {})
    .then(() =>
      credentialLock(ctx, instance.secret_id, async () => {
        if (ctx.signal?.aborted) throw Error("provider_canceled_or_timeout");
        const c = await secrets.get(instance.secret_id);
        if (!c?.client_id || !c.client_secret || !c.refresh_token)
          throw Error("provider_reconnect_required");
        if (c.access_token && (c.expiry_date ?? 0) > Date.now() + 60000)
          return c.access_token;
        try {
          const client = new OAuth2Client({
            clientId: c.client_id,
            clientSecret: c.client_secret,
            transporterOptions: {
              timeout: 10000,
              retry: false,
              signal: ctx.signal,
            },
          });
          client.setCredentials({ refresh_token: c.refresh_token });
          const { credentials: fresh } = await client.refreshAccessToken();
          if (!fresh.access_token) throw Error("missing_token");
          await secrets.put(instance.secret_id, {
            ...c,
            access_token: fresh.access_token,
            refresh_token: fresh.refresh_token ?? c.refresh_token,
            expiry_date: fresh.expiry_date ?? undefined,
          });
          return fresh.access_token;
        } catch {
          throw Error("provider_reconnect_required");
        }
      }),
    );
  refreshes.set(key, next);
  try {
    return await next;
  } finally {
    if (refreshes.get(key) === next) refreshes.delete(key);
  }
}
