import fs from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const renderScript = path.resolve(here, "../scripts/render-ppt.ps1");

export async function renderPptPreview(pptxPath, outputDir, viewport) {
  if (process.platform !== "win32") {
    return { status: "BLOCKED", reason: "PowerPoint COM preview is currently implemented only on Windows." };
  }
  await fs.mkdir(outputDir, { recursive: true });
  const inspectionPath = path.join(outputDir, "layout-inspection.json");
  try {
    await run("powershell.exe", [
      "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", renderScript,
      "-InputPptx", path.resolve(pptxPath), "-OutputDirectory", path.resolve(outputDir),
      "-InspectionJson", inspectionPath,
      "-Width", String(viewport.width), "-Height", String(viewport.height),
    ]);
    const layoutInspection = JSON.parse((await fs.readFile(inspectionPath, "utf8")).replace(/^\uFEFF|^ï»¿/, ""));
    return { status: "COMPLETE", renderer: "Microsoft PowerPoint", layoutInspection };
  } catch (error) {
    return { status: "BLOCKED", reason: error.message };
  }
}

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { windowsHide: true });
    let stdout = "", stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", reject);
    child.on("close", (code) => code === 0 ? resolve(stdout) : reject(new Error(stderr || stdout || `${command} exited ${code}`)));
  });
}
