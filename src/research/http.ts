import { lookup } from "node:dns/promises";
import { isIP } from "node:net";
import https from "node:https";
export function publicAddress(ip: string) {
  if(isIP(ip)===6){const fields=ip.toLowerCase().split(":");return /^[23][0-9a-f]{3}:/i.test(ip)&&fields[0]!=="2002"&&fields[0]!=="3fff"&&!(fields[0]==="2001"&&(parseInt(fields[1]||"0",16)<0x200||parseInt(fields[1]||"0",16)===0xdb8));}
  if (isIP(ip) !== 4) return false;
  const [a, b, c] = ip.split(".").map(Number);
  return !(
    a === 0 ||
    a === 10 ||
    a === 127 ||
    a >= 224 ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && (b === 168 || b === 0 || (b === 88 && c === 99))) ||
    (a === 100 && b >= 64 && b <= 127) ||
    (a === 198 && (b === 18 || b === 19 || (b === 51 && c === 100))) ||
    (a === 203 && b === 0 && c === 113)
  );
}
export function publicURL(input: string) {
  if(typeof input!=="string"||input.length>2000)throw Error("Public URL limit");
  const url = new URL(input);
  if (
    url.protocol !== "https:" ||
    url.username ||
    url.password ||
    (url.port && url.port !== "443") ||
    /(^localhost$|\.localhost$|\.local$)/i.test(url.hostname)
  )
    throw Error("Only public HTTPS destinations are allowed");
  const h = url.hostname.toLowerCase(),
    p = url.pathname;
  if (
    /(^|\.)(fitbit\.com|health\.google|health\.google\.com|maps\.google\.com|tasks\.google\.com|calendar\.google\.com)$/.test(
      h,
    ) ||
    /(^|\.)(maps|routes|fitness|health|tasks|calendar)\.googleapis\.com$/.test(
      h,
    ) ||
    (h === "www.googleapis.com" &&
      /^\/(fitness|tasks|calendar|health)\//.test(p)) ||
    (["google.com", "www.google.com"].includes(h) && /^\/maps(?:\/|$)/.test(p))
  )
    throw Error(
      "Use the native reviewed integration for this protected provider",
    );
  return url;
}
/** Pinned DNS lookup prevents a validation/fetch DNS-rebinding gap. Redirects are callers' work. */
export async function publicRequest(
  input: string,
  options: {
    method?: string;
    headers?: Record<string, string>;
    body?: Buffer;
    signal?: AbortSignal;
  } = {},
) {
  const url = publicURL(input),
    hosts = await lookup(url.hostname, { all: true });
  if (!hosts.length || hosts.some((h) => !publicAddress(h.address)))
    throw Error("Private destination blocked");
  const selected = hosts[0];
  return new Promise<{
    status: number;
    headers: Record<string, string>;
    body: Buffer;
  }>((resolve, reject) => {
    const req = https.request(
      url,
      {
        method: options.method ?? "GET",
        headers: { ...options.headers, "accept-encoding": "identity" },
        signal: options.signal,
        lookup: ((_h: any, o: any, cb: any) =>
          o?.all
            ? cb(null, [selected])
            : cb(null, selected.address, selected.family)) as any,
      },
      (response) => {
        const chunks: Buffer[] = [];
        let total = 0;
        response.on("error", () =>
          reject(Error("Public response unavailable")),
        );
        response.on("data", (b) => {
          if ((total += b.length) > 2 * 1024 * 1024) {
            req.destroy();
            reject(Error("Research response limit"));
          } else chunks.push(b);
        });
        response.on("end", () => {
          const headers: Record<string, string> = {};
          for (const [k, v] of Object.entries(response.headers))
            if (v !== undefined)
              headers[k] = Array.isArray(v) ? v.join("\n") : String(v);
          resolve({
            status: response.statusCode ?? 502,
            headers,
            body: Buffer.concat(chunks),
          });
        });
      },
    );
    req.setTimeout(15000, () => req.destroy());
    req.on("error", () => reject(Error("Public request unavailable")));
    req.end(options.body);
  });
}
