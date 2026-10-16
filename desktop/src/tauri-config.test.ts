import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const desktop = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const tauri = JSON.parse(readFileSync(resolve(desktop, "src-tauri/tauri.conf.json"), "utf8"));
const capability = JSON.parse(
  readFileSync(resolve(desktop, "src-tauri/capabilities/default.json"), "utf8"),
);

function allowedShellCommands() {
  return capability.permissions
    .filter((permission: { identifier?: string }) => permission.identifier?.startsWith("shell:allow-"))
    .flatMap((permission: { allow?: Array<{ name: string; cmd: string }> }) => permission.allow ?? []);
}

describe("Tauri desktop packaging", () => {
  it("registers the packaged skill-hub wrapper for shell execution", () => {
    const commands = allowedShellCommands();
    expect(commands).toHaveLength(2);
    expect(commands.map((command: { name: string }) => command.name)).toEqual(["skill-hub", "skill-hub"]);
    expect(commands.map((command: { cmd: string }) => command.cmd)).toEqual(["$RESOURCE/bin/skill-hub", "$RESOURCE/bin/skill-hub"]);
    expect(tauri.bundle.resources).toEqual({
      "../../bin/skill-hub": "bin/skill-hub",
      "../../src": "src",
    });
  });

  it("ships non-empty PNG icon assets instead of the placeholder", () => {
    for (const icon of ["icon.png", "icon-32.png", "icon-128.png", "icon-128@2x.png"]) {
      const path = resolve(desktop, "src-tauri/icons", icon);
      expect(existsSync(path)).toBe(true);
      expect(statSync(path).size).toBeGreaterThan(500);
    }
  });
});
