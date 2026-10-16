import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./Dashboard";
import * as api from "./api/client";

vi.mock("./api/client", async () => {
  const actual = await vi.importActual<typeof import("./api/client")>("./api/client");
  return {
    ...actual,
    getVersion: vi.fn(),
    resolveWorkspaceRoot: vi.fn(),
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
  };
});

const mocked = vi.mocked(api);

afterEach(cleanup);

beforeEach(() => {
  mocked.resolveWorkspaceRoot.mockResolvedValue("/Users/test/.skill-hub");
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
