import path from "node:path";
import { createRequire, registerHooks } from "node:module";
import { pathToFileURL } from "node:url";
/** Optional managed live-checkout resolver. Installed npm packages use ordinary resolution. */
const roots = [
  process.env.CHRYSALIS_DEPENDENCIES_ROOT,
  process.env.CHRYSALIS_PI_ROOT,
].filter(Boolean);
if (roots.length)
  registerHooks({
    resolve(specifier, context, nextResolve) {
      try {
        return nextResolve(specifier, context);
      } catch (error) {
        if (
          specifier.startsWith(".") ||
          specifier.startsWith("/") ||
          specifier.includes(":") ||
          (error.code !== "ERR_MODULE_NOT_FOUND" &&
            error.code !== "MODULE_NOT_FOUND")
        )
          throw error;
        for (const root of roots)
          try {
            return nextResolve(specifier, {
              ...context,
              parentURL: pathToFileURL(path.join(root, "package.json")).href,
            });
          } catch {}
        throw error;
      }
    },
  });
