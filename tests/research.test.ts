import test from "node:test";
import assert from "node:assert/strict";
import { publicAddress, publicURL } from "../src/research/http.ts";
import { youtubeURL, analyzeYouTube } from "../src/research/gemini-web.ts";
test("public destinations reject local protocols, credentials and special address ranges", () => {
  for (const ip of [
    "127.0.0.1",
    "10.1.2.3",
    "100.75.1.2",
    "192.168.1.3",
    "169.254.169.254",
    "0.0.0.0",
    "::1",
    "::ffff:127.0.0.1",
    "fc00::1",
    "2001:db8::1","2002:0a00:0001::1","2001:2::1","3fff::1",
  ])
    assert(!publicAddress(ip), ip);
  assert(publicAddress("8.8.8.8"));
  for (const url of [
    "file:///secret",
    "http://example.com",
    "https://user:secret@example.com",
    "https://example.com:8080",
    "https://localhost",
  ])
    assert.throws(() => publicURL(url));
});
test("YouTube adapter uses web-only transport and never leaks synthetic cookies", async () => {
  assert.equal(
    youtubeURL("https://youtu.be/abcdefghijk"),
    "https://www.youtube.com/watch?v=abcdefghijk",
  );
  assert.throws(() => youtubeURL("https://example.com/watch?v=abcdefghijk"));
  let calls = 0;
  const ports = {
    cookies: async () => ({ "__Secure-1PSID": "synthetic-cookie-canary" }),
    query: async (_q: string, _c: any, o: any) => {
      calls++;
      assert.equal(o.youtubeUrl, "https://www.youtube.com/watch?v=abcdefghijk");
      return "Answer synthetic-cookie-canary";
    },
  };
  const result = await analyzeYouTube(
    "https://youtu.be/abcdefghijk",
    "Explain the topic",
    ports,
  );
  assert.equal(calls, 1);
  assert(!JSON.stringify(result).includes("synthetic-cookie-canary"));
  ports.query = async () => {
    calls++;
    throw Error("secret synthetic-cookie-canary");
  };
  const failed = await analyzeYouTube(
    "https://youtu.be/abcdefghijk",
    "Explain",
    ports,
  );
  assert.equal(failed.status, "unavailable");
  assert.equal(calls, 2);
  assert(!JSON.stringify(failed).includes("synthetic-cookie-canary"));
});
