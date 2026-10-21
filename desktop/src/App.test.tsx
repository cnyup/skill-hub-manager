import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./Dashboard";
import * as api from "./api/client";

vi.mock("./api/client", async () => {
  const actual = await vi.importActual<typeof import("./api/client")>("./api/client");
  return {
    ...actual,
    getVersion: vi.fn(),
    resolveWorkspaceRoot: vi.fn(),
    listAgentTargets: vi.fn(),
    dryRunSync: vi.fn(),
    applySync: vi.fn(),
    createProfile: vi.fn(),
    updateProfile: vi.fn(),
    listSkills: vi.fn(),
    listProfiles: vi.fn(),
    getProfile: vi.fn(),
    getSkillDetail: vi.fn(),
    getSkillSource: vi.fn(),
    findSkills: vi.fn(),
    validateProfiles: vi.fn(),
    auditAll: vi.fn(),
    registryDoctor: vi.fn(),
    doctor: vi.fn(),
    importSkill: vi.fn(),
    updateSkill: vi.fn(),
    removeSkill: vi.fn(),
    pickDirectory: vi.fn(),
    scanLocalAgents: vi.fn(),
    addAgent: vi.fn(),
    removeAgent: vi.fn(),
  };
});

const mocked = vi.mocked(api);

afterEach(cleanup);

beforeEach(() => {
  mocked.resolveWorkspaceRoot.mockResolvedValue("/Users/test/.skill-hub");
  mocked.listAgentTargets.mockResolvedValue([
    { agent: "codex", target: "/Users/test/.codex/skills" },
    { agent: "claude", target: "/Users/test/.claude/skills" },
  ]);
  mocked.dryRunSync.mockResolvedValue({
    mode: "dry-run", profile: "claude", agent: "claude",
    target: "/Users/test/.claude/skills", linked: ["k8s-finder"], missing: [], removed: [],
  });
  mocked.applySync.mockResolvedValue({
    mode: "apply", profile: "claude", agent: "claude",
    target: "/Users/test/.claude/skills", linked: ["k8s-finder"], missing: [], removed: [],
  });
  mocked.createProfile.mockResolvedValue({ written: "/Users/test/.skill-hub/profiles/claude.yaml" });
  mocked.updateProfile.mockResolvedValue({
    updated: "/Users/test/.skill-hub/profiles/default.yaml",
    profile: { name: "default", agent: "codex", skills: ["k8s-finder"], exclude: [], effective_skills: ["k8s-finder"] },
  });
  mocked.getVersion.mockResolvedValue("skill-hub 0.1.0");
  mocked.listSkills.mockResolvedValue([
    {
      name: "k8s-finder",
      path: "/vault/k8s-finder",
      description: "Find Kubernetes services",
      visibility: "team",
      agents: ["codex"],
      tags: ["infra", "kubernetes"],
    },
    { name: "release-notes", path: "/vault/release-notes", description: "Draft release notes" },
  ]);
  mocked.listProfiles.mockResolvedValue(["default"]);
  mocked.getProfile.mockResolvedValue({
    name: "default",
    agent: "codex",
    skills: ["k8s-finder"],
    exclude: ["experimental-*"],
    effective_skills: ["k8s-finder"],
  });
  mocked.getSkillDetail.mockResolvedValue({
    name: "k8s-finder",
    path: "/vault/k8s-finder",
    description: "Find Kubernetes services",
    visibility: "team",
    agents: ["codex"],
    tags: ["infra", "kubernetes"],
    content: "# Kubernetes Finder\n\nUse this skill to locate services.",
  });
  mocked.getSkillSource.mockResolvedValue({ skill: "k8s-finder", source: "https://example.test/skills.git" });
  mocked.findSkills.mockImplementation(async (_root, query) => query.toLowerCase().includes("release") ? [
    { name: "release-notes", path: "/vault/release-notes", description: "Draft release notes" },
  ] : []);
  mocked.validateProfiles.mockResolvedValue([
    { profile: "default", valid: false, issues: ["missing-skill: missing-skill"] },
  ]);
  mocked.auditAll.mockResolvedValue([
    {
      profile: "default",
      agent: "codex",
      effective_skills: ["k8s-finder", "missing-skill"],
      missing_skills: ["missing-skill"],
    },
  ]);
  mocked.registryDoctor.mockResolvedValue({ ok: false, issues: ["unregistered-skill: draft"] });
  mocked.doctor.mockResolvedValue({ broken: ["old-link"], expected_missing: [], hasIssues: true });
});

describe("Wave 3 desktop shell", () => {
  it("loads data from the resolved workspace root", async () => {
    mocked.resolveWorkspaceRoot.mockResolvedValue("/Users/test/skills-hub");
    render(<App />);

    expect(await screen.findByText("k8s-finder")).toBeInTheDocument();
    expect(screen.getByText("/Users/test/skills-hub")).toBeInTheDocument();
    expect(mocked.listSkills).toHaveBeenCalledWith("/Users/test/skills-hub");
  });

  it("switches between Library, Agents and Doctor data views", async () => {
    render(<App />);

    expect(await screen.findByText("k8s-finder")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Agents" }));
    expect(await screen.findByText("missing-skill")).toBeInTheDocument();
    expect(screen.getByText("experimental-*")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Doctor" }));
    expect(await screen.findByText("unregistered-skill: draft")).toBeInTheDocument();
    expect(screen.getByText("old-link")).toBeInTheDocument();
  });

  it("opens a skill detail panel and switches between preview, source and profile tabs", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));

    const details = screen.getByRole("complementary", { name: "Skill details" });
    await waitFor(() => expect(details).toHaveTextContent("Kubernetes Finder"));
    expect(details).not.toHaveTextContent("https://example.test/skills.git");

    fireEvent.click(screen.getByRole("tab", { name: "来源" }));
    expect(details).toHaveTextContent("/vault/k8s-finder");
    expect(details).toHaveTextContent("https://example.test/skills.git");

    fireEvent.click(screen.getByRole("tab", { name: "Profiles" }));
    expect(details).toHaveTextContent("default");
    expect(mocked.getSkillDetail).toHaveBeenCalledWith("/Users/test/.skill-hub", "k8s-finder");
  });

  it("clicks a sidebar profile to show only its configured and effective skills", async () => {
    mocked.listProfiles.mockResolvedValue(["codex", "cursor"]);
    mocked.getProfile.mockImplementation(async (_root, name) => ({
      name,
      agent: name,
      skills: name === "codex" ? ["k8s-finder", "experimental-k8s"] : ["release-notes"],
      exclude: name === "codex" ? ["experimental-*"] : [],
      effective_skills: name === "codex" ? ["k8s-finder"] : ["release-notes"],
    }));
    mocked.auditAll.mockResolvedValue([]);
    render(<App />);
    await screen.findByText("k8s-finder");

    fireEvent.click(screen.getByRole("button", { name: "打开 profile codex" }));

    // Agents 页按纳管 agent 渲染卡片；点击侧栏 profile 后只显示其所属 agent 的卡片
    const codexCard = await screen.findByRole("article", { name: "Agent codex" });
    expect(codexCard).toHaveTextContent("Configured skills");
    expect(codexCard).toHaveTextContent("experimental-k8s");
    expect(codexCard).toHaveTextContent("Effective skills");
    expect(screen.queryByRole("heading", { name: "cursor" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Agents" }));
    expect(await screen.findByRole("heading", { name: "cursor" })).toBeInTheDocument();
  });

  it("filters only the reserved all-agent profile from every desktop view", async () => {
    mocked.listProfiles.mockResolvedValue(["default", "all-agent", "all-agent-extra"]);
    mocked.getProfile.mockImplementation(async (_root, name) => ({
      name,
      agent: "codex",
      skills: ["k8s-finder"],
      exclude: [],
      effective_skills: ["k8s-finder"],
    }));
    mocked.auditAll.mockResolvedValue([
      { profile: "all-agent", agent: "all-agent", effective_skills: ["k8s-finder"], missing_skills: [] },
      { profile: "all-agent-extra", agent: "codex", effective_skills: ["k8s-finder"], missing_skills: [] },
    ]);
    render(<App />);
    await screen.findByText("k8s-finder");

    expect(screen.queryByRole("button", { name: "打开 profile all-agent" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "打开 profile all-agent-extra" })).toBeInTheDocument();
    expect(screen.queryByText("all-agent", { selector: ".badge" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Agents" }));
    expect(screen.queryByRole("heading", { name: "all-agent" })).not.toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "codex" })).toBeInTheDocument();
  });

  it("deduplicates claude-code into the canonical claude assignment target", async () => {
    mocked.listAgentTargets.mockResolvedValue([
      { agent: "claude", target: "/Users/test/.claude/skills" },
      { agent: "claude-code", target: "/Users/test/.claude/skills" },
    ]);
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));
    fireEvent.click(await screen.findByRole("button", { name: "分配给 Agent" }));

    expect(screen.getAllByRole("checkbox")).toHaveLength(1);
    expect(screen.getByRole("checkbox", { name: "claude" })).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "claude-code" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "claude" }));
    fireEvent.click(screen.getByRole("button", { name: "预览同步" }));
    await waitFor(() => expect(mocked.dryRunSync).toHaveBeenCalledTimes(1));
    expect(mocked.dryRunSync).toHaveBeenCalledWith(
      "/Users/test/.skill-hub",
      "/Users/test/.claude/skills",
      "claude",
      { addSkills: ["k8s-finder"], agent: "claude" },
    );
  });

  it("shows one badge per agent even when multiple profiles share it", async () => {
    mocked.listProfiles.mockResolvedValue(["default", "codex"]);
    mocked.getProfile.mockImplementation(async (_root, name) => name === "codex"
      ? { name: "codex", agent: "codex", skills: ["k8s-finder"], exclude: [], effective_skills: ["k8s-finder"] }
      : { name: "default", agent: "codex", skills: [], exclude: [], effective_skills: [] });
    mocked.auditAll.mockResolvedValue([
      { profile: "default", agent: "codex", effective_skills: [], missing_skills: [] },
      { profile: "codex", agent: "codex", effective_skills: ["k8s-finder"], missing_skills: [] },
    ]);

    render(<App />);
    await screen.findByText("k8s-finder");

    // default 与 codex 两个 profile 同属 codex agent → 每张 skill 卡只出一个徽章，且为 enabled
    const card = screen.getByRole("button", { name: "打开 k8s-finder" });
    const codexBadges = await within(card).findAllByText("codex", { selector: ".badge.agent" });
    expect(codexBadges).toHaveLength(1);
    expect(codexBadges[0]).toHaveClass("enabled");
  });

  it("previews the claude assignment against the on-disk claude-code profile", async () => {
    mocked.listProfiles.mockResolvedValue(["claude-code"]);
    mocked.getProfile.mockResolvedValue({
      name: "claude-code",
      agent: "claude-code",
      skills: ["billing-labeler"],
      exclude: [],
      effective_skills: ["billing-labeler"],
    });

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));
    fireEvent.click(await screen.findByRole("button", { name: "分配给 Agent" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "claude" }));
    fireEvent.click(screen.getByRole("button", { name: "预览同步" }));

    // 预览必须以磁盘 profile（claude-code）为基准，否则 CLI 找不到 profile 会回退成空
    // candidate，把已有的 billing-labeler 误报成「将移除」
    await waitFor(() => expect(mocked.dryRunSync).toHaveBeenCalledWith(
      "/Users/test/.skill-hub",
      "/Users/test/.claude/skills",
      "claude-code",
      { addSkills: ["k8s-finder"], agent: "claude" },
    ));
    expect(screen.queryByText(/将移除/)).not.toBeInTheDocument();
  });

  it("multi-selects agents and assigns to each selected target", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));
    fireEvent.click(await screen.findByRole("button", { name: "分配给 Agent" }));

    // 两个 agent 都勾选 → 多选分配
    fireEvent.click(screen.getByRole("checkbox", { name: /codex/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: /claude/ }));
    fireEvent.click(screen.getByRole("button", { name: "预览同步" }));

    await waitFor(() => expect(mocked.dryRunSync).toHaveBeenCalledTimes(2));
    // default profile（agent: codex）已持有 k8s-finder → 预览无需再加，且以磁盘名 default 为基准；
    // claude 无既有 profile → 以 agent 名为基准并待新增
    expect(mocked.dryRunSync).toHaveBeenCalledWith(
      "/Users/test/.skill-hub",
      "/Users/test/.codex/skills",
      "default",
      { addSkills: [], agent: "codex" },
    );
    expect(mocked.dryRunSync).toHaveBeenCalledWith(
      "/Users/test/.skill-hub",
      "/Users/test/.claude/skills",
      "claude",
      { addSkills: ["k8s-finder"], agent: "claude" },
    );

    fireEvent.click(screen.getByRole("button", { name: "确认分配并同步" }));
    await waitFor(() => expect(mocked.applySync).toHaveBeenCalledTimes(2));
    // codex 目标复用磁盘 profile default；claude 目标无既有 profile → 用 agent 名新建
    expect(mocked.applySync).toHaveBeenCalledWith(
      "/Users/test/.skill-hub", "/Users/test/.codex/skills", "default",
    );
    expect(mocked.applySync).toHaveBeenCalledWith(
      "/Users/test/.skill-hub", "/Users/test/.claude/skills", "claude",
    );
  });

  it("previews assignment without writing and persists only after confirmation", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));
    fireEvent.click(await screen.findByRole("button", { name: "分配给 Agent" }));

    fireEvent.click(screen.getByRole("checkbox", { name: /claude/ }));
    fireEvent.click(screen.getByRole("button", { name: "预览同步" }));

    expect(await screen.findByText("将链接 1 个 skill")).toBeInTheDocument();
    expect(mocked.dryRunSync).toHaveBeenCalledWith(
      "/Users/test/.skill-hub",
      "/Users/test/.claude/skills",
      "claude",
      { addSkills: ["k8s-finder"], agent: "claude" },
    );
    expect(mocked.createProfile).not.toHaveBeenCalled();
    expect(mocked.updateProfile).not.toHaveBeenCalled();
    expect(mocked.applySync).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "确认分配并同步" }));
    await waitFor(() => expect(mocked.createProfile).toHaveBeenCalledWith(
      "/Users/test/.skill-hub", "claude", "claude", ["k8s-finder"],
    ));
    expect(mocked.applySync).toHaveBeenCalledWith(
      "/Users/test/.skill-hub", "/Users/test/.claude/skills", "claude",
    );
  });

  it("closes assignment preview without persisting changes", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));
    fireEvent.click(await screen.findByRole("button", { name: "分配给 Agent" }));
    fireEvent.click(screen.getByRole("button", { name: "取消" }));

    expect(screen.queryByRole("dialog", { name: "分配给 Agent" })).not.toBeInTheDocument();
    expect(mocked.createProfile).not.toHaveBeenCalled();
    expect(mocked.updateProfile).not.toHaveBeenCalled();
    expect(mocked.applySync).not.toHaveBeenCalled();
  });

  it("opens command search with Meta+K, filters skills and navigates", async () => {
    render(<App />);
    await screen.findByText("k8s-finder");

    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const search = screen.getByRole("dialog", { name: "Command palette" });
    fireEvent.change(screen.getByPlaceholderText("搜索 skills 或输入命令…"), { target: { value: "release" } });

    await waitFor(() => {
      expect(search).toHaveTextContent("release-notes");
      expect(search).not.toHaveTextContent("k8s-finder");
    });
    expect(mocked.findSkills).toHaveBeenCalledWith("/Users/test/.skill-hub", "release");

    fireEvent.change(screen.getByPlaceholderText("搜索 skills 或输入命令…"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "前往 Doctor" }));
    expect(await screen.findByRole("heading", { name: "Doctor" })).toBeInTheDocument();
  });
});

describe("Wave 5 skill lifecycle", () => {
  beforeEach(() => {
    mocked.importSkill.mockResolvedValue({
      skill: "web-access",
      source: "/Users/test/incoming/web-access",
      target: "/Users/test/.skill-hub/skills/web-access",
      replaced: false,
      state_file: "/Users/test/.skill-hub/state/skill-sources.json",
    });
    mocked.updateSkill.mockResolvedValue({
      skill: "k8s-finder",
      source: "/Users/test/cache/k8s-finder",
      target: "/Users/test/.skill-hub/skills/k8s-finder",
      replaced: true,
    });
    mocked.removeSkill.mockResolvedValue({
      skill: "k8s-finder",
      target: "/Users/test/.skill-hub/skills/k8s-finder",
      removed: true,
      purged_source: false,
      updated_profiles: ["default"],
    });
  });

  it("imports a local skill directory through the import dialog", async () => {
    render(<App />);
    await screen.findByText("k8s-finder");

    fireEvent.click(screen.getByRole("button", { name: "导入 skill" }));
    const dialog = screen.getByRole("dialog", { name: "导入 skill" });
    fireEvent.change(screen.getByLabelText("来源目录"), { target: { value: "/Users/test/incoming/web-access" } });

    fireEvent.click(screen.getByRole("button", { name: "导入" }));
    await waitFor(() => expect(mocked.importSkill).toHaveBeenCalledWith(
      "/Users/test/.skill-hub",
      { source: "/Users/test/incoming/web-access" },
    ));
    expect(dialog).not.toBeInTheDocument();
    await waitFor(() => expect(mocked.listSkills).toHaveBeenCalledTimes(2));
  });

  it("fills the source field from the directory picker and imports", async () => {
    mocked.pickDirectory.mockResolvedValue("/Users/test/incoming/web-access");
    render(<App />);
    await screen.findByText("k8s-finder");

    fireEvent.click(screen.getByRole("button", { name: "导入 skill" }));
    const dialog = screen.getByRole("dialog", { name: "导入 skill" });

    fireEvent.click(screen.getByRole("button", { name: "浏览…" }));

    await waitFor(() => expect(screen.getByLabelText("来源目录")).toHaveValue("/Users/test/incoming/web-access"));
    expect(dialog).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "导入" }));
    await waitFor(() => expect(mocked.importSkill).toHaveBeenCalledWith(
      "/Users/test/.skill-hub",
      { source: "/Users/test/incoming/web-access" },
    ));
    await waitFor(() => expect(mocked.listSkills).toHaveBeenCalledTimes(2));
  });

  it("keeps the source field untouched when the directory picker is cancelled", async () => {
    mocked.pickDirectory.mockResolvedValue(null);
    render(<App />);
    await screen.findByText("k8s-finder");

    fireEvent.click(screen.getByRole("button", { name: "导入 skill" }));
    fireEvent.click(screen.getByRole("button", { name: "浏览…" }));

    await waitFor(() => expect(mocked.pickDirectory).toHaveBeenCalledTimes(1));
    expect(screen.getByLabelText("来源目录")).toHaveValue("");
    expect(screen.getByRole("dialog", { name: "导入 skill" })).toBeInTheDocument();
  });

  it("imports with force and a custom name when overwriting", async () => {
    render(<App />);
    await screen.findByText("k8s-finder");

    fireEvent.click(screen.getByRole("button", { name: "导入 skill" }));
    fireEvent.change(screen.getByLabelText("来源目录"), { target: { value: "/Users/test/incoming/web-access" } });
    fireEvent.change(screen.getByLabelText("Skill 名称（可选）"), { target: { value: "web-access-v2" } });
    fireEvent.click(screen.getByRole("checkbox", { name: "覆盖已有同名 skill" }));
    fireEvent.click(screen.getByRole("button", { name: "导入" }));

    await waitFor(() => expect(mocked.importSkill).toHaveBeenLastCalledWith(
      "/Users/test/.skill-hub",
      { source: "/Users/test/incoming/web-access", name: "web-access-v2", force: true },
    ));
  });

  it("shows an import error and keeps the dialog open", async () => {
    mocked.importSkill.mockRejectedValue(new Error("skill.md not found under source directory"));
    render(<App />);
    await screen.findByText("k8s-finder");

    fireEvent.click(screen.getByRole("button", { name: "导入 skill" }));
    fireEvent.change(screen.getByLabelText("来源目录"), { target: { value: "/Users/test/incoming/broken" } });
    fireEvent.click(screen.getByRole("button", { name: "导入" }));

    expect(await screen.findByText(/导入失败/)).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "导入 skill" })).toBeInTheDocument();
    expect(mocked.listSkills).toHaveBeenCalledTimes(1);
  });

  it("updates a skill from its cached source via the detail panel", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));

    fireEvent.click(await screen.findByRole("button", { name: "从来源更新" }));
    await waitFor(() => expect(mocked.updateSkill).toHaveBeenCalledWith("/Users/test/.skill-hub", "k8s-finder"));
    await waitFor(() => expect(mocked.listSkills).toHaveBeenCalledTimes(2));
  });

  it("hides the update action when the skill has no source record", async () => {
    mocked.getSkillSource.mockResolvedValue(null);
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));

    await waitFor(() => expect(mocked.getSkillSource).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "从来源更新" })).not.toBeInTheDocument();
  });

  it("confirms removal with profile impact and purge option", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));

    fireEvent.click(screen.getByRole("button", { name: "删除" }));
    const dialog = screen.getByRole("dialog", { name: "删除 skill" });
    expect(dialog).toHaveTextContent("default");
    expect(mocked.removeSkill).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("checkbox", { name: "同时清除来源记录" }));
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => expect(mocked.removeSkill).toHaveBeenCalledWith("/Users/test/.skill-hub", "k8s-finder", { purgeSource: true }));
    await waitFor(() => expect(mocked.listSkills).toHaveBeenCalledTimes(2));
  });

  it("closes the remove dialog without removing", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));

    fireEvent.click(screen.getByRole("button", { name: "删除" }));
    fireEvent.click(screen.getByRole("button", { name: "取消" }));

    expect(screen.queryByRole("dialog", { name: "删除 skill" })).not.toBeInTheDocument();
    expect(mocked.removeSkill).not.toHaveBeenCalled();
  });
});

describe("Wave 6 scan local agents", () => {
  it("scans, lists found unmanaged candidates and registers the selected one", async () => {
    mocked.scanLocalAgents.mockResolvedValue([
      { agent: "codex", target: "/Users/test/.codex/skills", exists: true, skill_count: 3, managed: true },
      { agent: "zcode", target: "/Users/test/.zcode/skills", exists: true, skill_count: 5, managed: false },
      { agent: "qoder", target: "/Users/test/.qoder/skills", exists: false, skill_count: 0, managed: false },
    ]);
    mocked.addAgent.mockResolvedValue({ agent: "zcode", target: "/Users/test/.zcode/skills", config: "/Users/test/.skill-hub/agents.yaml" });

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Agents" }));
    fireEvent.click(await screen.findByRole("button", { name: "扫描本机 Agent" }));

    const dialog = screen.getByRole("dialog", { name: "扫描本机 Agent" });
    // 存在且未纳管的候选才出现；已纳管/不存在的被过滤
    expect(await within(dialog).findByRole("checkbox", { name: "zcode" })).toBeInTheDocument();
    expect(within(dialog).queryByRole("checkbox", { name: "codex" })).not.toBeInTheDocument();
    expect(within(dialog).queryByRole("checkbox", { name: "qoder" })).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("checkbox", { name: "zcode" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "确认纳管" }));

    await waitFor(() => expect(mocked.addAgent).toHaveBeenCalledWith("/Users/test/.skill-hub", "zcode", "/Users/test/.zcode/skills"));
    await waitFor(() => expect(mocked.listAgentTargets).toHaveBeenCalledTimes(2)); // 初始 + 纳管后刷新
  });

  it("adds a custom agent via the manual fallback form", async () => {
    mocked.scanLocalAgents.mockResolvedValue([
      { agent: "codex", target: "/Users/test/.codex/skills", exists: true, skill_count: 3, managed: true },
    ]);
    mocked.addAgent.mockResolvedValue({ agent: "my-agent", target: "/Users/test/my-skills", config: "/Users/test/.skill-hub/agents.yaml" });

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Agents" }));
    fireEvent.click(await screen.findByRole("button", { name: "扫描本机 Agent" }));

    const dialog = await screen.findByRole("dialog", { name: "扫描本机 Agent" });
    // 兜底表单：自定义名字 + 路径
    fireEvent.change(await within(dialog).findByLabelText("Agent 名称"), { target: { value: "my-agent" } });
    fireEvent.change(within(dialog).getByLabelText("Skills 目录"), { target: { value: "/Users/test/my-skills" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "手动添加" }));

    await waitFor(() => expect(mocked.addAgent).toHaveBeenCalledWith("/Users/test/.skill-hub", "my-agent", "/Users/test/my-skills"));
    await waitFor(() => expect(mocked.listAgentTargets).toHaveBeenCalledTimes(2));
  });

  it("renders one card per managed agent with the … remove menu on the card", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Agents" }));

    // 顶部不再有「已纳管 Agent」列表区块——卡片本身就是纳管 agent
    expect(screen.queryByRole("group", { name: "已纳管 Agent" })).not.toBeInTheDocument();

    // 每个纳管 agent 一张卡片，… 菜单在卡片右上角，移除作用于该 agent
    const codexCard = await screen.findByRole("article", { name: "Agent codex" });
    mocked.removeAgent.mockResolvedValue({ agent: "codex", removed: true });
    fireEvent.click(within(codexCard).getByRole("button", { name: "更多操作 codex" }));
    fireEvent.click(within(codexCard).getByRole("menuitem", { name: "移除纳管 codex" }));

    await waitFor(() => expect(mocked.removeAgent).toHaveBeenCalledWith("/Users/test/.skill-hub", "codex"));
    await waitFor(() => expect(mocked.listAgentTargets).toHaveBeenCalledTimes(2)); // 初始 + 移除后刷新
  });

  it("shows a card for managed agents that have no profiles yet", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Agents" }));

    // claude 已纳管但无关联 profile → 仍须出现卡片（空态），不能只按 profile 渲染
    const claudeCard = await screen.findByRole("article", { name: "Agent claude" });
    expect(claudeCard).toHaveTextContent("无关联 profile");
  });

  it("shows an empty state when no unmanaged candidates exist", async () => {
    mocked.scanLocalAgents.mockResolvedValue([
      { agent: "codex", target: "/Users/test/.codex/skills", exists: true, skill_count: 3, managed: true },
      { agent: "qoder", target: "/Users/test/.qoder/skills", exists: false, skill_count: 0, managed: false },
    ]);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Agents" }));
    fireEvent.click(await screen.findByRole("button", { name: "扫描本机 Agent" }));

    expect(await screen.findByText("未发现可纳管的本机 Agent")).toBeInTheDocument();
    expect(mocked.addAgent).not.toHaveBeenCalled();
  });
});

describe("Wave 5 remove vs delete split", () => {
  it("unassigns a skill from selected agents without deleting the vault entry", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));

    fireEvent.click(screen.getByRole("button", { name: "从 Agent 移除" }));
    // profile 数据异步加载，等待 holder agent 的 checkbox 出现
    expect(await screen.findByRole("checkbox", { name: "codex" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "codex" }));
    fireEvent.click(screen.getByRole("button", { name: "确认移除" }));

    // 磁盘 profile 名是 default（agent: codex），写操作必须用 profile 名定位
    await waitFor(() => expect(mocked.updateProfile).toHaveBeenCalledWith(
      "/Users/test/.skill-hub", "default", { removeSkills: ["k8s-finder"] },
    ));
    await waitFor(() => expect(mocked.applySync).toHaveBeenCalledWith(
      "/Users/test/.skill-hub", "/Users/test/.codex/skills", "default",
    ));
    expect(mocked.removeSkill).not.toHaveBeenCalled();
    await waitFor(() => expect(mocked.listSkills).toHaveBeenCalledTimes(2));
  });

  it("unassigns from a legacy claude-code profile via the canonical claude target", async () => {
    mocked.listProfiles.mockResolvedValue(["default", "claude-code"]);
    mocked.getProfile.mockImplementation(async (_root, name) => name === "claude-code"
      ? { name: "claude-code", agent: "claude-code", skills: ["k8s-finder"], exclude: [], effective_skills: ["k8s-finder"] }
      : { name: "default", agent: "codex", skills: ["k8s-finder"], exclude: [], effective_skills: ["k8s-finder"] });

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));
    fireEvent.click(screen.getByRole("button", { name: "从 Agent 移除" }));

    // claude-code profile 应映射到 canonical claude target 并出现在列表中
    expect(await screen.findByRole("checkbox", { name: "claude" })).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "claude-code" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "claude" }));
    fireEvent.click(screen.getByRole("button", { name: "确认移除" }));

    // 写操作必须用磁盘 profile 名（claude-code），不是 canonical agent 名
    await waitFor(() => expect(mocked.updateProfile).toHaveBeenCalledWith(
      "/Users/test/.skill-hub", "claude-code", { removeSkills: ["k8s-finder"] },
    ));
    await waitFor(() => expect(mocked.applySync).toHaveBeenCalledWith(
      "/Users/test/.skill-hub", "/Users/test/.claude/skills", "claude-code",
    ));
    expect(mocked.removeSkill).not.toHaveBeenCalled();
  });

  it("requires explicit deletion confirmation to actually remove the vault skill", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /k8s-finder/i }));

    fireEvent.click(await screen.findByRole("button", { name: "删除" }));
    const dialog = screen.getByRole("dialog", { name: "删除 skill" });
    expect(dialog).toHaveTextContent("default");
    expect(mocked.removeSkill).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("checkbox", { name: "同时清除来源记录" }));
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => expect(mocked.removeSkill).toHaveBeenCalledWith("/Users/test/.skill-hub", "k8s-finder", { purgeSource: true }));
    await waitFor(() => expect(mocked.listSkills).toHaveBeenCalledTimes(2));
  });
});

describe("view-scoped topbar actions and agent badge consistency", () => {
  it("shows the import button only on Library, not on Agents or Doctor", async () => {
    render(<App />);
    expect(await screen.findByRole("button", { name: "导入 skill" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Agents" }));
    await screen.findByRole("button", { name: "扫描本机 Agent" });
    expect(screen.queryByRole("button", { name: "导入 skill" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Doctor" }));
    await screen.findByText("old-link");
    expect(screen.queryByRole("button", { name: "导入 skill" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Library" }));
    expect(await screen.findByRole("button", { name: "导入 skill" })).toBeInTheDocument();
  });

  it("renders one badge per managed agent even without a matching profile audit", async () => {
    // audit 只覆盖 codex；claude 无 profile/audit → 徽章仍应按 agentTargets 全集出现
    render(<App />);
    await screen.findByText("k8s-finder");

    const card = screen.getByRole("button", { name: "打开 k8s-finder" });
    expect(within(card).getByText("codex", { selector: ".badge.agent" })).toBeInTheDocument();
    expect(within(card).getByText("claude", { selector: ".badge.agent" })).toBeInTheDocument();
    // 无 audit 报告的 agent 徽章为 disabled（未启用该 skill）
    expect(within(card).getByText("claude", { selector: ".badge.agent" })).toHaveClass("disabled");
  });

  it("normalizes audit agent names to canonical labels when rendering badges", async () => {
    mocked.auditAll.mockResolvedValue([
      { profile: "claude-code", agent: "claude-code", effective_skills: ["k8s-finder"], missing_skills: [] },
    ]);
    mocked.listProfiles.mockResolvedValue(["claude-code"]);
    mocked.getProfile.mockImplementation(async () => ({ name: "claude-code", agent: "claude-code", skills: ["k8s-finder"], exclude: [], effective_skills: ["k8s-finder"] }));

    render(<App />);
    await screen.findByText("k8s-finder");

    // audit 的 claude-code 归一化成 claude 徽章，不出现两个 claude 变体
    const card = screen.getByRole("button", { name: "打开 k8s-finder" });
    expect(within(card).getByText("claude", { selector: ".badge.agent" })).toBeInTheDocument();
    expect(within(card).queryByText("claude-code", { selector: ".badge.agent" })).not.toBeInTheDocument();
    expect(within(card).getByText("claude", { selector: ".badge.agent" })).toHaveClass("enabled");
  });
});
