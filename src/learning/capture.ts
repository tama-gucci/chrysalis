import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { assistantRoot, loadProfile } from "../assistant/profile.ts";
import {
  withSyncLock,
  atomicJSON,
  confined,
  sha256,
  raw,
} from "../platforms/filesystem.ts";
export function captureLesson(
  state: string,
  lesson: { topic: string; entries: unknown[] },
) {
  return withSyncLock(assistantRoot(state), "private-output-retention", () => {
    if (!loadProfile(state).features.lessonCapture)
      return { status: "disabled" };
    if (
      !lesson.topic ||
      lesson.topic.length > 500 ||
      lesson.entries.length > 100
    )
      throw Error("Lesson capture limit");
    const data = JSON.stringify({
      version: 1,
      ...lesson,
      authority: "unreviewed_private_lesson",
    });
    if (Buffer.byteLength(data) > 256 * 1024)
      throw Error("Lesson capture limit");
    const root = path.join(assistantRoot(state), "lessons");
    fs.mkdirSync(root, { recursive: true, mode: 0o700 });
    if (fs.readdirSync(root).length >= 100)
      throw Error("Lesson retention limit; review private captures");
    const id = randomUUID();
    atomicJSON(confined(root, id + ".json"), JSON.parse(data));
    return {
      status: "captured",
      handle: id,
      sha256: sha256(raw(confined(root, id + ".json"))),
      authority: "unreviewed_private_lesson",
    };
  });
}
