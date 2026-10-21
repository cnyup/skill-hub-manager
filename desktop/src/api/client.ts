/**
 * desktop/src/api/client.ts — 唯一的 CLI 出口（收敛层）。
 *
 * 架构契约（计划书 Wave 2）：
 * - 所有对 skill-hub CLI 的调用必须经过本文件；
 * - 接口形状对齐 HTTP API 语义，将来升级 sidecar/重写只换本目录；
 * - Rust 侧 tauri-plugin-shell scope 白名单仅放行 skill-hub 包装器。
 */
import { homeDir } from "@tauri-apps/api/path";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
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

export interface SkillDetail extends RegistryEntry {
  content: string;
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

export interface ProfileValidation {
  profile: string;
  valid: boolean;
  issues: string[];
}

export interface AgentTarget {
  agent: string;
  target: string;
}

export interface ScanCandidate {
  agent: string;
  target: string;
  exists: boolean;
  skill_count: number;
  managed: boolean;
}

export type SkillSourceRecord = Record<string, string>;

const RESERVED_PROFILE_NAMES = new Set(["all-agent"]);

function canonicalAgentName(agent: string): string {
  return agent === "claude-code" ? "claude" : agent;
}

function normalizeAgentTargets(targets: AgentTarget[]): AgentTarget[] {
  const normalized = new Map<string, AgentTarget>();
  for (const target of targets) {
    const agent = canonicalAgentName(target.agent);
    if (!normalized.has(agent) || target.agent === agent) {
      normalized.set(agent, { ...target, agent });
    }
  }
  return [...normalized.values()];
}

/** Resolve the active workspace, keeping compatibility with the pre-standard ~/skills-hub location. */
export async function resolveWorkspaceRoot(): Promise<string> {
  const home = (await homeDir()).replace(/\/$/, "");
  const standard = `${home}/.skill-hub`;
  const legacy = `${home}/skills-hub`;

  const [standardSkills, legacySkills] = await Promise.all([
    listSkills(standard).catch(() => []),
    listSkills(legacy).catch(() => []),
  ]);
  if (standardSkills.length === 0 && legacySkills.length > 0) return legacy;
  return standard;
}

// ---------- 只读 API ----------

export async function listAgentTargets(root: string): Promise<AgentTarget[]> {
  const { data } = await runCliJson<{ agents: AgentTarget[] }>([
    "agent", "list", "--root", root, "--json",
  ]);
  return normalizeAgentTargets(data.agents);
}

/** Wave 6：扫描本机常见 agent 的 skills 目录，返回全部候选（含 exists/managed 状态）。 */
export async function scanLocalAgents(root: string): Promise<ScanCandidate[]> {
  const { data } = await runCliJson<{ candidates: ScanCandidate[] }>([
    "agent", "scan", "--root", root, "--json",
  ]);
  return data.candidates.map((item) => ({ ...item, agent: canonicalAgentName(item.agent) }));
}

/** Wave 6：纳管一个本机 agent（写 workspace agents.yaml）。 */
export async function addAgent(
  root: string,
  agent: string,
  target: string,
): Promise<{ agent: string; target: string; config: string }> {
  const { data } = await runCliJson<{ agent: string; target: string; config: string }>([
    "agent", "add", "--root", root, "--agent", agent, "--target", target, "--json",
  ]);
  return data;
}

/** Wave 6：移除纳管（删 agents.yaml 条目；内置 agent 不可移除，removed=false）。 */
export async function removeAgent(root: string, agent: string): Promise<{ agent: string; removed: boolean }> {
  const { data } = await runCliJson<{ agent: string; removed: boolean }>([
    "agent", "remove", "--root", root, "--agent", agent, "--json",
  ]);
  return data;
}

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

export async function getSkillDetail(root: string, name: string): Promise<SkillDetail> {
  const { data } = await runCliJson<{ skill: SkillDetail }>([
    "skill", "show", "--root", root, "--name", name, "--json",
  ]);
  return data.skill;
}

export async function getProfile(root: string, name: string): Promise<ProfilePayload> {
  const { data } = await runCliJson<{ profile: ProfilePayload }>([
    "profile", "show", "--root", root, "--name", name, "--json",
  ]);
  return data.profile;
}

export async function getSkillSource(root: string, name: string): Promise<SkillSourceRecord | null> {
  const { data } = await runCliJson<{ record: SkillSourceRecord | null }>([
    "skill", "source", "show", "--root", root, "--name", name, "--json",
  ]);
  return data.record;
}

export async function validateProfiles(root: string): Promise<ProfileValidation[]> {
  const { data } = await runCliJson<{ profiles: ProfileValidation[] }>([
    "profile", "validate", "--root", root, "--json",
  ]);
  return data.profiles;
}

export async function listProfiles(root: string): Promise<string[]> {
  const { data } = await runCliJson<{ profiles: string[] }>([
    "profile", "list", "--root", root, "--json",
  ]);
  return data.profiles.filter((profile) => !RESERVED_PROFILE_NAMES.has(profile));
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

/** 打开系统目录选择弹窗；用户取消时返回 null。仅桌面端可用（jsdom 测试中 mock）。 */
export async function pickDirectory(): Promise<string | null> {
  return openDialog({ directory: true, multiple: false, title: "选择 skill 来源目录" });
}

export async function createProfile(
  root: string,
  name: string,
  agent: string,
  skills: string[],
): Promise<{ written: string }> {
  const args = ["profile", "add", "--root", root, "--name", name, "--agent", agent];
  for (const skill of skills) args.push("--skill", skill);
  args.push("--json");
  const { data } = await runCliJson<{ written: string }>(args);
  return data;
}

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
  profileName?: string,
  candidate?: { addSkills?: string[]; removeSkills?: string[]; agent?: string },
): Promise<SyncResultPayload> {
  const args = ["sync", "--root", root, "--target", target, "--dry-run", "--json"];
  if (profileName) args.push("--profile-name", profileName);
  if (candidate?.agent) args.push("--candidate-agent", candidate.agent);
  for (const skill of candidate?.addSkills ?? []) args.push("--add-skill", skill);
  for (const skill of candidate?.removeSkills ?? []) args.push("--remove-skill", skill);
  const { data } = await runCliJson<SyncResultPayload>(args);
  return data;
}

export async function applySync(
  root: string,
  target: string,
  profileName?: string,
): Promise<SyncResultPayload> {
  const args = ["sync", "--root", root, "--target", target, "--json"];
  if (profileName) args.push("--profile-name", profileName);
  const { data } = await runCliJson<SyncResultPayload>(args);
  return data;
}

// ---------- Skill 生命周期（对齐 CLI skill import/remove/update --json 契约） ----------

export interface SkillImportResult {
  skill: string;
  source: string;
  target: string;
  replaced: boolean;
  state_file: string;
}

export interface SkillUpdateResult {
  skill: string;
  source: string;
  target: string;
  replaced: boolean;
}

export interface SkillRemoveResult {
  skill: string;
  target: string;
  removed: boolean;
  purged_source: boolean;
  updated_profiles: string[];
}

/** 生命周期命令约定：非零退出码时 stdout 仍带 JSON（含 error 字段），此时抛错并携带 error 文本。 */
async function runLifecycleCommand<T>(args: string[]): Promise<T> {
  const { data, exitCode } = await runCliJson<T & { error?: string }>(args);
  if (exitCode !== 0) {
    const detail = data?.error ?? `exit ${exitCode}`;
    throw new CliError(exitCode, detail, `skill-hub ${args.slice(0, 4).join(" ")} 失败：${detail}`);
  }
  return data;
}

export async function importSkill(
  root: string,
  options: { source: string; name?: string; force?: boolean },
): Promise<SkillImportResult> {
  const args = ["skill", "import", "--root", root, "--source", options.source];
  if (options.name) args.push("--name", options.name);
  if (options.force) args.push("--force");
  args.push("--json");
  return runLifecycleCommand<SkillImportResult>(args);
}

export async function updateSkill(root: string, name: string): Promise<SkillUpdateResult> {
  return runLifecycleCommand<SkillUpdateResult>([
    "skill", "update", "--root", root, "--name", name, "--json",
  ]);
}

export async function removeSkill(
  root: string,
  name: string,
  options?: { purgeSource?: boolean },
): Promise<SkillRemoveResult> {
  const args = ["skill", "remove", "--root", root, "--name", name];
  if (options?.purgeSource) args.push("--purge-source");
  args.push("--json");
  return runLifecycleCommand<SkillRemoveResult>(args);
}
