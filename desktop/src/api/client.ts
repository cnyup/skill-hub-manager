/**
 * desktop/src/api/client.ts — 唯一的 CLI 出口（收敛层）。
 *
 * 架构契约（计划书 Wave 2）：
 * - 所有对 skill-hub CLI 的调用必须经过本文件；
 * - 接口形状对齐 HTTP API 语义，将来升级 sidecar/重写只换本目录；
 * - Rust 侧 tauri-plugin-shell scope 白名单仅放行 skill-hub 包装器。
 */
import { Command } from "@tauri-apps/plugin-shell";

export class CliError extends Error {
  constructor(
    public exitCode: number,
    public stderr: string,
    message: string,
  ) {
    super(message);
    this.name = "CliError";
  }
}

/** CLI JSON 命令的通用执行器。非零退出码但 stdout 有 JSON 时也会解析（约定：错误也带 JSON）。 */
async function runCliJson<T>(args: string[]): Promise<{ data: T; exitCode: number }> {
  const cmd = Command.create("skill-hub", args);
  const output = await cmd.execute();
  const exitCode = output.code ?? -1;
  let data: T | null = null;
  if (output.stdout.trim()) {
    try {
      data = JSON.parse(output.stdout) as T;
    } catch {
      // stdout 非 JSON（如 --version 文本），由调用方兜底
    }
  }
  if (data === null && exitCode !== 0) {
    throw new CliError(
      exitCode,
      output.stderr,
      `skill-hub ${args.join(" ")} failed (exit ${exitCode}): ${output.stderr.trim()}`,
    );
  }
  return { data: data as T, exitCode };
}

/** 启动握手：返回 CLI 版本字符串（如 "skill-hub 0.1.0"）。 */
export async function getVersion(): Promise<string> {
  const cmd = Command.create("skill-hub", ["--version"]);
  const output = await cmd.execute();
  const exitCode = output.code ?? -1;
  if (exitCode !== 0) {
    throw new CliError(exitCode, output.stderr, "skill-hub --version failed");
  }
  return output.stdout.trim();
}

// ---------- 类型（对齐 docs/schema/json-output.md 契约） ----------

export interface RegistryEntry {
  name: string;
  path: string;
  visibility?: string;
  description?: string;
  agents?: string[];
  tags?: string[];
}

export interface ProfilePayload {
  name: string;
  agent: string;
  skills: string[];
  exclude: string[];
  effective_skills: string[];
}

export interface AuditReport {
  profile: string;
  agent: string;
  effective_skills: string[];
  missing_skills: string[];
}

export interface SyncResultPayload {
  mode: "apply" | "dry-run";
  profile: string;
  agent: string;
  target: string;
  linked: string[];
  missing: string[];
  removed: string[];
}

// ---------- 只读 API ----------

export async function listSkills(root: string): Promise<RegistryEntry[]> {
  const { data } = await runCliJson<{ skills: RegistryEntry[] }>([
    "ls", "--root", root, "--json",
  ]);
  return data.skills;
}

export async function findSkills(root: string, query: string): Promise<RegistryEntry[]> {
  const { data } = await runCliJson<{ skills: RegistryEntry[] }>([
    "find", "--root", root, "--query", query, "--json",
  ]);
  return data.skills;
}

export async function getProfile(root: string, name: string): Promise<ProfilePayload> {
  const { data } = await runCliJson<{ profile: ProfilePayload }>([
    "profile", "show", "--root", root, "--name", name, "--json",
  ]);
  return data.profile;
}

export async function listProfiles(root: string): Promise<string[]> {
  const { data } = await runCliJson<{ profiles: string[] }>([
    "profile", "list", "--root", root, "--json",
  ]);
  return data.profiles;
}

export async function auditAll(root: string): Promise<AuditReport[]> {
  const { data } = await runCliJson<{ profiles: AuditReport[] }>([
    "audit", "--root", root, "--json",
  ]);
  return data.profiles;
}

export async function registryDoctor(root: string): Promise<{ ok: boolean; issues: string[] }> {
  const { data, exitCode } = await runCliJson<{ ok: boolean; issues: string[] }>([
    "registry", "doctor", "--root", root, "--json",
  ]);
  // 退出码 1 = 有 issues（约定：数据已解析，不是错误）
  void exitCode;
  return data;
}

export async function doctor(
  root: string,
  target?: string,
): Promise<{ broken: string[]; expected_missing: string[]; hasIssues: boolean }> {
  const args = ["doctor", "--root", root];
  if (target) args.push("--target", target);
  args.push("--json");
  const { data, exitCode } = await runCliJson<{ broken: string[]; expected_missing: string[] }>(args);
  return { ...data, hasIssues: exitCode !== 0 };
}

// ---------- 写 API ----------

export async function updateProfile(
  root: string,
  name: string,
  ops: { addSkills?: string[]; removeSkills?: string[] },
): Promise<{ updated: string; profile: ProfilePayload }> {
  const args = ["profile", "update", "--root", root, "--name", name];
  for (const s of ops.addSkills ?? []) args.push("--add-skill", s);
  for (const s of ops.removeSkills ?? []) args.push("--remove-skill", s);
  args.push("--json");
  const { data } = await runCliJson<{ updated: string; profile: ProfilePayload }>(args);
  return data;
}

export async function dryRunSync(
  root: string,
  target: string,
  profile?: string,
): Promise<SyncResultPayload> {
  const args = ["sync", "--root", root, "--target", target, "--dry-run", "--json"];
  if (profile) args.push("--profile", profile);
  const { data } = await runCliJson<SyncResultPayload>(args);
  return data;
}

export async function applySync(
  root: string,
  target: string,
  profile?: string,
): Promise<SyncResultPayload> {
  const args = ["sync", "--root", root, "--target", target, "--json"];
  if (profile) args.push("--profile", profile);
  const { data } = await runCliJson<SyncResultPayload>(args);
  return data;
}
