import fs from "node:fs";
export function serviceEnvironment() {
  if (!process.getuid) throw Error("Linux user service manager required");
  const runtime = "/run/user/" + process.getuid();
  return {
    PATH: "/usr/bin:/bin",
    XDG_RUNTIME_DIR: runtime,
    DBUS_SESSION_BUS_ADDRESS: "unix:path=" + runtime + "/bus",
  };
}
export function delegationReady() {
  try {
    return fs.statSync("/run/user/" + process.getuid!() + "/bus").isSocket();
  } catch {
    return false;
  }
}
