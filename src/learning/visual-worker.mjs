import { parentPort, workerData } from "node:worker_threads";
const { render } = await import(workerData.module);
const art = render(workerData.code);
parentPort.postMessage(
  art ? { plain: art.plain, width: art.width, warnings: art.warnings } : null,
);
