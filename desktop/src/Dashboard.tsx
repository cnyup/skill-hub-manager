import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertCircle,
  CheckCircle2,
  Command as CommandIcon,
  Library,
  Search,
  Stethoscope,
  Users,
  X,
} from "lucide-react";
import {
  applySync,
  auditAll,
  createProfile,
  doctor,
  dryRunSync,
  findSkills,
  getProfile,
  getSkillDetail,
  getSkillSource,
  getVersion,
  importSkill,
  listAgentTargets,
  listProfiles,
  listSkills,
  pickDirectory,
  registryDoctor,
  removeAgent,
  removeSkill,
  resolveWorkspaceRoot,
  scanLocalAgents,
  addAgent,
  updateProfile,
  updateSkill,
  validateProfiles,
} from "./api/client";
import type {
  AgentTarget,
  AuditReport,
  ProfilePayload,
  ProfileValidation,
  RegistryEntry,
  ScanCandidate,
  SkillDetail,
  SkillSourceRecord,
  SyncResultPayload,
} from "./api/client";

type View = "library" | "agents" | "doctor";
type DetailTab = "preview" | "source" | "profiles";

interface HealthState {
  registry: { ok: boolean; issues: string[] };
  links: { broken: string[]; expected_missing: string[]; hasIssues: boolean };
  profiles: ProfileValidation[];
}

const RESERVED_PROFILE_NAMES = new Set(["all-agent"]);

function visibleProfileName(name: string): boolean {
  return !RESERVED_PROFILE_NAMES.has(name);
}

function normalizeAgentTargets(targets: AgentTarget[]): AgentTarget[] {
  const normalized = new Map<string, AgentTarget>();
  for (const target of targets) {
    const agent = target.agent === "claude-code" ? "claude" : target.agent;
    if (!normalized.has(agent) || target.agent === agent) normalized.set(agent, { ...target, agent });
  }
  return [...normalized.values()];
}

const EMPTY_HEALTH: HealthState = {
  registry: { ok: true, issues: [] },
  links: { broken: [], expected_missing: [], hasIssues: false },
  profiles: [],
};

export default function App() {
  const [root, setRoot] = useState<string | null>(null);
  const [version, setVersion] = useState("(连接中…)");
  const [fatalError, setFatalError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<View>("library");
  const [skills, setSkills] = useState<RegistryEntry[]>([]);
  const [profileNames, setProfileNames] = useState<string[]>([]);
  const [profiles, setProfiles] = useState<ProfilePayload[]>([]);
  const [audit, setAudit] = useState<AuditReport[]>([]);
  const [health, setHealth] = useState<HealthState>(EMPTY_HEALTH);
  const [agentTargets, setAgentTargets] = useState<AgentTarget[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<RegistryEntry | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<SkillDetail | null>(null);
  const [selectedSource, setSelectedSource] = useState<SkillSourceRecord | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailWarning, setDetailWarning] = useState<string | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [highlightedProfile, setHighlightedProfile] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [assignOpen, setAssignOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<RegistryEntry | null>(null);
  const [unassignTarget, setUnassignTarget] = useState<RegistryEntry | null>(null);
  const [scanOpen, setScanOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const refresh = (message?: string) => {
    setReloadToken((token) => token + 1);
    if (message) setToast(message);
  };

  useEffect(() => {
    void resolveWorkspaceRoot().then(setRoot).catch((error) => setFatalError(String(error)));
  }, []);

  useEffect(() => {
    if (!root) return;
    let alive = true;
    void (async () => {
      try {
        const nextVersion = await getVersion();
        if (!alive) return;
        setVersion(nextVersion);

        const nextWarnings: string[] = [];
        const [nextSkills, nextProfileNames, nextAudit, nextRegistry, nextLinks, nextValidation, nextAgents] = await Promise.all([
          listSkills(root).catch((error) => { nextWarnings.push(`Library: ${String(error)}`); return []; }),
          listProfiles(root).catch((error) => { nextWarnings.push(`Profiles: ${String(error)}`); return []; }),
          auditAll(root).catch((error) => { nextWarnings.push(`Audit: ${String(error)}`); return []; }),
          registryDoctor(root).catch((error) => { nextWarnings.push(`Registry doctor: ${String(error)}`); return EMPTY_HEALTH.registry; }),
          doctor(root).catch((error) => { nextWarnings.push(`Link doctor: ${String(error)}`); return EMPTY_HEALTH.links; }),
          validateProfiles(root).catch((error) => { nextWarnings.push(`Profile validate: ${String(error)}`); return []; }),
          listAgentTargets(root).catch((error) => { nextWarnings.push(`Agent targets: ${String(error)}`); return []; }),
        ]);
        const visibleNames = nextProfileNames.filter(visibleProfileName);
        const visibleAudit = nextAudit.filter((report) => visibleProfileName(report.profile));
        const visibleValidation = nextValidation.filter((profile) => visibleProfileName(profile.profile));
        const nextProfiles = await Promise.all(
          visibleNames.map((name) => getProfile(root, name).catch((error) => {
            nextWarnings.push(`Profile ${name}: ${String(error)}`);
            return null;
          })),
        );
        if (!alive) return;
        setSkills(nextSkills);
        setProfileNames(visibleNames);
        setAudit(visibleAudit);
        setAgentTargets(normalizeAgentTargets(nextAgents));
        // canonical agent 名（claude-code → claude）作 join key；profile.name 保留磁盘原值供写操作定位
        setProfiles(nextProfiles
          .filter((profile): profile is ProfilePayload => profile !== null && visibleProfileName(profile.name))
          .map((profile) => ({ ...profile, agent: profile.agent === "claude-code" ? "claude" : profile.agent })));
        setHighlightedProfile((current) => current && visibleNames.includes(current) ? current : null);
        setHealth({ registry: nextRegistry, links: nextLinks, profiles: visibleValidation });
        setWarnings(nextWarnings);
      } catch (error) {
        if (alive) setFatalError(String(error));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [root, reloadToken]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
      if (event.key === "Escape") setPaletteOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const openSkill = async (skill: RegistryEntry) => {
    setSelectedSkill(skill);
    setSelectedDetail(null);
    setSelectedSource(null);
    setDetailWarning(null);
    if (!root) return;
    setDetailLoading(true);
    const [detailResult, sourceResult] = await Promise.allSettled([
      getSkillDetail(root, skill.name),
      getSkillSource(root, skill.name),
    ]);
    if (detailResult.status === "fulfilled") setSelectedDetail(detailResult.value);
    else setDetailWarning(`SKILL.md 加载失败：${String(detailResult.reason)}`);
    if (sourceResult.status === "fulfilled") setSelectedSource(sourceResult.value);
    else setDetailWarning((current) => [current, `来源加载失败：${String(sourceResult.reason)}`].filter(Boolean).join("；"));
    setDetailLoading(false);
  };

  const navigate = (nextView: View) => {
    setView(nextView);
    setPaletteOpen(false);
    setQuery("");
    setHighlightedProfile(null);
  };

  const openProfile = (profile: string) => {
    setView("agents");
    setPaletteOpen(false);
    setHighlightedProfile(profile);
  };

  if (fatalError) {
    return (
      <main className="fatal-state">
        <h1>CLI 连接失败</h1>
        <p className="mono">{fatalError}</p>
        <p>请确认 skill-hub 包装器已注册到 Tauri shell 白名单。</p>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar view={view} profiles={profileNames} version={version} onNavigate={navigate} onOpenProfile={openProfile} />
      <main className="content">
        <header className="topbar">
          <div>
            <h1>{view === "library" ? "Library" : view === "agents" ? "Agents" : "Doctor"}</h1>
            <p>
              {view === "library" && `${skills.length} skills · ${profileNames.length} profiles`}
              {view === "agents" && `${profiles.length} profiles · ${audit.length} audit reports`}
              {view === "doctor" && "Registry、links 与 profiles 健康状态"}
            </p>
            {root && <span className="workspace-path mono" title={root}>{root}</span>}
          </div>
          <div className="topbar-actions">
            <button className="command-trigger" onClick={() => setPaletteOpen(true)}>
              <Search size={14} /> 搜索或执行命令 <kbd>⌘K</kbd>
            </button>
            {view === "library" && (
              <button className="import-trigger" onClick={() => setImportOpen(true)}>
                <Library size={14} /> 导入 skill
              </button>
            )}
            {view === "agents" && (
              <button className="import-trigger" aria-label="扫描本机 Agent" onClick={() => setScanOpen(true)}>
                <Search size={14} /> 扫描本机 Agent
              </button>
            )}
          </div>
        </header>

        {toast && (
          <div className="toast-banner" role="status" onMouseDown={() => setToast(null)}>{toast}</div>
        )}

        {warnings.length > 0 && (
          <div className="warning-banner" role="status">
            <AlertCircle size={15} /> 部分数据加载失败：{warnings.join("；")}
          </div>
        )}

        {loading ? (
          <div className="empty-state">正在读取 workspace…</div>
        ) : view === "library" ? (
          <LibraryView skills={skills} audit={audit} agentTargets={agentTargets} onOpenSkill={openSkill} />
        ) : view === "agents" && root ? (
          <AgentsView
            profiles={highlightedProfile ? profiles.filter((profile) => profile.name === highlightedProfile) : profiles}
            audit={audit}
            selectedProfile={highlightedProfile}
            agentTargets={agentTargets}
            root={root}
            onChanged={refresh}
          />
        ) : (
          <DoctorView health={health} />
        )}
      </main>

      {selectedSkill && (
        <SkillDetails
          skill={selectedDetail ?? selectedSkill}
          content={selectedDetail?.content ?? ""}
          source={selectedSource}
          profiles={profiles}
          loading={detailLoading}
          warning={detailWarning}
          onClose={() => setSelectedSkill(null)}
          onAssign={() => setAssignOpen(true)}
          onUpdate={async () => {
            if (!root) return;
            try {
              await updateSkill(root, selectedSkill.name);
              setSelectedSkill(null);
              refresh(`已更新 ${selectedSkill.name}`);
            } catch (error) {
              setDetailWarning(`更新失败：${String(error)}`);
            }
          }}
          onUnassign={() => setUnassignTarget(selectedSkill)}
          onDelete={() => setRemoveTarget(selectedSkill)}
        />
      )}

      {scanOpen && root && (
        <ScanAgentsDialog
          root={root}
          onClose={() => setScanOpen(false)}
          onApplied={(message) => {
            setScanOpen(false);
            refresh(message);
          }}
        />
      )}

      {unassignTarget && root && (
        <UnassignDialog
          root={root}
          skill={unassignTarget}
          profiles={profiles}
          agentTargets={agentTargets}
          onClose={() => setUnassignTarget(null)}
          onUnassigned={(message) => {
            setUnassignTarget(null);
            setSelectedSkill(null);
            refresh(message);
          }}
        />
      )}

      {removeTarget && root && (
        <RemoveSkillDialog
          root={root}
          skill={removeTarget}
          profiles={profiles}
          onClose={() => setRemoveTarget(null)}
          onRemoved={(message) => {
            setRemoveTarget(null);
            setSelectedSkill(null);
            refresh(message);
          }}
        />
      )}

      {importOpen && root && (
        <ImportSkillDialog
          root={root}
          onClose={() => setImportOpen(false)}
          onImported={(message) => {
            setImportOpen(false);
            refresh(message);
          }}
        />
      )}

      {assignOpen && selectedSkill && root && (
        <AssignDialog
          root={root}
          skill={selectedDetail ?? selectedSkill}
          agentTargets={agentTargets}
          existingProfiles={profiles}
          onClose={() => setAssignOpen(false)}
          onApplied={() => {
            setAssignOpen(false);
            setReloadToken((token) => token + 1);
          }}
        />
      )}

      {paletteOpen && root && (
        <CommandPalette
          root={root}
          initialSkills={skills}
          query={query}
          onQuery={setQuery}
          onNavigate={navigate}
          onOpenSkill={(skill) => { void openSkill(skill); setPaletteOpen(false); setQuery(""); }}
          onClose={() => setPaletteOpen(false)}
        />
      )}
    </div>
  );
}

function Sidebar({ view, profiles, version, onNavigate, onOpenProfile }: {
  view: View;
  profiles: string[];
  version: string;
  onNavigate: (view: View) => void;
  onOpenProfile: (profile: string) => void;
}) {
  return (
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">S</span> skill-hub</div>
      <nav aria-label="Main navigation">
        <NavButton active={view === "library"} icon={<Library size={15} />} label="Library" onClick={() => onNavigate("library")} />
        <NavButton active={view === "agents"} icon={<Users size={15} />} label="Agents" onClick={() => onNavigate("agents")} />
        <NavButton active={view === "doctor"} icon={<Stethoscope size={15} />} label="Doctor" onClick={() => onNavigate("doctor")} />
      </nav>
      <div className="sidebar-heading">Profiles</div>
      <div className="profile-list">
        {profiles.map((profile) => <button key={profile} className="profile-link" aria-label={`打开 profile ${profile}`} onClick={() => onOpenProfile(profile)}>{profile}</button>)}
        {profiles.length === 0 && <span className="profile-link muted">暂无 profile</span>}
      </div>
      <div className="sidebar-footer mono">{version}</div>
    </aside>
  );
}

function NavButton({ active, icon, label, onClick }: { active: boolean; icon: React.ReactNode; label: string; onClick: () => void }) {
  return <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}>{icon}{label}</button>;
}

function LibraryView({ skills, audit, agentTargets, onOpenSkill }: {
  skills: RegistryEntry[];
  audit: AuditReport[];
  agentTargets: AgentTarget[];
  onOpenSkill: (skill: RegistryEntry) => void;
}) {
  if (skills.length === 0) return <div className="empty-state">vault 为空——用 CLI 导入第一个 skill 试试</div>;
  // audit 的原始 agent 名（如 claude-code）归一化到 canonical（claude），与 agentTargets 同一 join key
  const canonicalAgent = (agent: string) => agent === "claude-code" ? "claude" : agent;
  return (
    <section className="card-grid" aria-label="Skill library">
      {skills.map((skill) => {
        const enabledByAgent = new Map<string, boolean>();
        for (const report of audit) {
          const canonical = canonicalAgent(report.agent);
          enabledByAgent.set(canonical, (enabledByAgent.get(canonical) ?? false) || report.effective_skills.includes(skill.name));
        }
        return (
          <button key={skill.name} className="skill-card" aria-label={`打开 ${skill.name}`} onClick={() => onOpenSkill(skill)}>
            <div className="card-title mono">{skill.name}</div>
            <p>{skill.description ?? "（无描述）"}</p>
            <div className="badge-row">
              {agentTargets.map((target) => (
                <span key={target.agent} className={`badge agent ${enabledByAgent.get(target.agent) ? "enabled" : "disabled"}`}>{target.agent}</span>
              ))}
              {(skill.tags ?? []).slice(0, 2).map((tag) => <span key={tag} className="badge">{tag}</span>)}
            </div>
          </button>
        );
      })}
    </section>
  );
}

function AgentsView({ profiles, audit, selectedProfile, agentTargets, root, onChanged }: {
  profiles: ProfilePayload[];
  audit: AuditReport[];
  selectedProfile: string | null;
  agentTargets: AgentTarget[];
  root: string;
  onChanged: (message: string) => void;
}) {
  const [removing, setRemoving] = useState<string | null>(null);
  const [menuAgent, setMenuAgent] = useState<string | null>(null);
  const [removeError, setRemoveError] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuAgent) return;
    const onPointerDown = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuAgent(null);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuAgent(null);
    };
    window.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [menuAgent]);

  const unregister = async (agent: string) => {
    setRemoving(agent);
    setRemoveError(null);
    setMenuAgent(null);
    try {
      const { removed } = await removeAgent(root, agent);
      onChanged(removed ? `已移除纳管 ${agent}` : `${agent} 是内置 Agent，无需移除`);
    } catch (err) {
      setRemoveError(`${agent} 移除失败：${String(err)}`);
    } finally {
      setRemoving(null);
    }
  };

  if (agentTargets.length === 0 && profiles.length === 0) return <div className="empty-state">尚未纳管 Agent——点击顶栏「扫描本机 Agent」添加</div>;
  const dedupe = (values: string[]) => [...new Set(values)];
  // 每个纳管 agent 一张卡片；profile 指向未纳管 agent 时也合成卡片，保证 profile 不消失
  const agentCards = (() => {
    const byAgent = new Map<string, { agent: string; target: string | null; managed: boolean; profiles: ProfilePayload[] }>();
    for (const target of agentTargets) {
      byAgent.set(target.agent, { agent: target.agent, target: target.target, managed: true, profiles: [] });
    }
    for (const profile of profiles) {
      let card = byAgent.get(profile.agent);
      if (!card) {
        card = { agent: profile.agent, target: null, managed: false, profiles: [] };
        byAgent.set(profile.agent, card);
      }
      card.profiles.push(profile);
    }
    const cards = [...byAgent.values()];
    return selectedProfile ? cards.filter((card) => card.profiles.some((profile) => profile.name === selectedProfile)) : cards;
  })();
  return (
    <section className="stack-list">
      {agentCards.map((card) => {
        const configured = dedupe(card.profiles.flatMap((profile) => profile.skills));
        const effective = dedupe(card.profiles.flatMap((profile) => profile.effective_skills));
        const excludes = dedupe(card.profiles.flatMap((profile) => profile.exclude));
        const missing = dedupe(card.profiles.flatMap((profile) => audit.find((item) => item.profile === profile.name)?.missing_skills ?? []));
        const highlighted = selectedProfile != null && card.profiles.some((profile) => profile.name === selectedProfile);
        return (
          <article
            aria-label={`Agent ${card.agent}`}
            className={`panel${highlighted ? " highlighted" : ""}`}
            data-highlighted={highlighted ? "true" : "false"}
            key={card.agent}
          >
            <div className="panel-heading">
              <div><h2>{card.agent}</h2>{card.target && <span className="mono muted agent-target">{card.target}</span>}{!card.managed && <span className="badge">未纳管</span>}</div>
              <div className="panel-heading-side">
                <span>{effective.length} effective</span>
                {card.managed && (
                  <div className="agent-row-menu" ref={menuAgent === card.agent ? menuRef : null}>
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={`更多操作 ${card.agent}`}
                      aria-expanded={menuAgent === card.agent}
                      onClick={() => setMenuAgent((current) => current === card.agent ? null : card.agent)}
                    >
                      …
                    </button>
                    {menuAgent === card.agent && (
                      <div className="agent-menu-popover" role="menu">
                        <button
                          type="button"
                          role="menuitem"
                          className="danger"
                          aria-label={`移除纳管 ${card.agent}`}
                          disabled={removing === card.agent}
                          onClick={() => { void unregister(card.agent); }}
                        >
                          {removing === card.agent ? "移除中…" : "移除纳管"}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
            <div className="detail-section"><h3>Profiles</h3><div className="badge-row">{card.profiles.length ? card.profiles.map((profile) => <span className="badge mono" key={profile.name}>{profile.name}</span>) : <span className="muted">无关联 profile</span>}</div></div>
            <div className="detail-section"><h3>Configured skills</h3><div className="badge-row">{configured.length ? configured.map((skill) => <span className="badge mono" key={skill}>{skill}</span>) : <span className="muted">无</span>}</div></div>
            <div className="detail-section"><h3>Effective skills</h3><div className="badge-row">{effective.length ? effective.map((skill) => <span className="badge mono" key={skill}>{skill}</span>) : <span className="muted">无</span>}</div></div>
            <div className="detail-section"><h3>Exclude patterns</h3><div className="badge-row">{excludes.length ? excludes.map((item) => <span className="badge mono" key={item}>{item}</span>) : <span className="muted">无</span>}</div></div>
            {missing.length > 0 && <div className="issue-list">{missing.map((item) => <span key={item}><AlertCircle size={14} />{item}</span>)}</div>}
          </article>
        );
      })}
      {removeError && <div className="detail-warning"><AlertCircle size={14} />{removeError}</div>}
    </section>
  );
}

function DoctorView({ health }: { health: HealthState }) {
  const sections = [
    { title: "Registry", ok: health.registry.ok, issues: health.registry.issues },
    { title: "Symbolic links", ok: !health.links.hasIssues, issues: [...health.links.broken, ...health.links.expected_missing] },
    ...health.profiles.map((profile) => ({ title: `Profile · ${profile.profile}`, ok: profile.valid, issues: profile.issues })),
  ];
  return (
    <section className="health-grid">
      {sections.map((section) => (
        <article className="panel health-card" key={section.title}>
          <div className={`health-icon ${section.ok ? "ok" : "bad"}`}>{section.ok ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}</div>
          <div><h2>{section.title}</h2><p className={section.ok ? "status-ok" : "status-bad"}>{section.ok ? "正常" : `${section.issues.length} 个问题`}</p></div>
          {section.issues.length > 0 && <ul>{section.issues.map((issue) => <li key={issue} className="mono">{issue}</li>)}</ul>}
        </article>
      ))}
    </section>
  );
}

function SkillDetails({ skill, content, source, profiles, loading, warning, onClose, onAssign, onUpdate, onUnassign, onDelete }: {
  skill: RegistryEntry;
  content: string;
  source: SkillSourceRecord | null;
  profiles: ProfilePayload[];
  loading: boolean;
  warning: string | null;
  onClose: () => void;
  onAssign: () => void;
  onUpdate: () => void;
  onUnassign: () => void;
  onDelete: () => void;
}) {
  const [tab, setTab] = useState<DetailTab>("preview");
  const memberships = profiles.filter((profile) => profile.effective_skills.includes(skill.name));
  return (
    <aside className="details-panel" aria-label="Skill details">
      <div className="details-header"><div><span className="eyebrow">Skill details</span><h2 className="mono">{skill.name}</h2></div><button className="icon-button" aria-label="关闭详情" onClick={onClose}><X size={17} /></button></div>
      <p className="detail-description">{skill.description ?? "（无描述）"}</p>
      <div className="detail-actions">
        <button className="assign-trigger" onClick={onAssign}><Users size={14} /> 分配给 Agent</button>
        {memberships.length > 0 && <button className="lifecycle-trigger" onClick={onUnassign}>从 Agent 移除</button>}
        {source && <button className="lifecycle-trigger" onClick={onUpdate}>从来源更新</button>}
        <button className="lifecycle-trigger danger" onClick={onDelete}>删除</button>
      </div>
      <div className="detail-tabs" role="tablist" aria-label="Skill detail sections">
        <button role="tab" aria-selected={tab === "preview"} onClick={() => setTab("preview")}>预览</button>
        <button role="tab" aria-selected={tab === "source"} onClick={() => setTab("source")}>来源</button>
        <button role="tab" aria-selected={tab === "profiles"} onClick={() => setTab("profiles")}>Profiles</button>
      </div>
      {warning && <div className="detail-warning"><AlertCircle size={14} />{warning}</div>}
      {tab === "preview" && (
        <section className="markdown-preview" role="tabpanel">
          {loading ? <p className="muted">正在读取 SKILL.md…</p> : content ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown> : <p className="muted">暂无可预览内容</p>}
        </section>
      )}
      {tab === "source" && (
        <section role="tabpanel">
          <div className="detail-section"><h3>来源元数据</h3><dl><dt>Vault path</dt><dd className="mono">{skill.path}</dd>{source ? Object.entries(source).map(([key, value]) => <div key={key}><dt>{key}</dt><dd className="mono">{value}</dd></div>) : <div><dt>记录</dt><dd className="muted">无来源记录</dd></div>}</dl></div>
          <div className="detail-section"><h3>Tags</h3><div className="badge-row">{(skill.tags ?? []).length ? skill.tags?.map((tag) => <span className="badge" key={tag}>{tag}</span>) : <span className="muted">无</span>}</div></div>
        </section>
      )}
      {tab === "profiles" && (
        <section role="tabpanel" className="detail-section"><h3>所属 Profiles</h3><div className="badge-row">{memberships.length ? memberships.map((profile) => <span className="badge agent enabled" key={profile.name}>{profile.name}</span>) : <span className="muted">未加入 profile</span>}</div></section>
      )}
    </aside>
  );
}

function CommandPalette({ root, initialSkills, query, onQuery, onNavigate, onOpenSkill, onClose }: {
  root: string;
  initialSkills: RegistryEntry[];
  query: string;
  onQuery: (query: string) => void;
  onNavigate: (view: View) => void;
  onOpenSkill: (skill: RegistryEntry) => void;
  onClose: () => void;
}) {
  const [matches, setMatches] = useState(initialSkills.slice(0, 6));
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    const normalized = query.trim();
    if (!normalized) {
      requestId.current += 1;
      setMatches(initialSkills.slice(0, 6));
      setSearching(false);
      setSearchError(null);
      return;
    }
    const id = ++requestId.current;
    setSearching(true);
    setSearchError(null);
    const timer = window.setTimeout(() => {
      void findSkills(root, normalized)
        .then((results) => {
          if (requestId.current === id) setMatches(results);
        })
        .catch((error) => {
          if (requestId.current === id) {
            setMatches([]);
            setSearchError(String(error));
          }
        })
        .finally(() => {
          if (requestId.current === id) setSearching(false);
        });
    }, 120);
    return () => window.clearTimeout(timer);
  }, [initialSkills, query, root]);

  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <section className="command-palette" role="dialog" aria-label="Command palette" onMouseDown={(event) => event.stopPropagation()}>
        <div className="palette-input"><Search size={16} /><input autoFocus value={query} onChange={(event) => onQuery(event.target.value)} placeholder="搜索 skills 或输入命令…" /><kbd>esc</kbd></div>
        <div className="palette-group"><h3>导航</h3>{(["library", "agents", "doctor"] as View[]).map((item) => <button key={item} aria-label={`前往 ${item[0].toUpperCase()}${item.slice(1)}`} onClick={() => onNavigate(item)}><CommandIcon size={14} />前往 {item[0].toUpperCase()}{item.slice(1)}</button>)}</div>
        <div className="palette-group"><h3>Skills</h3>{matches.map((skill) => <button key={skill.name} onClick={() => onOpenSkill(skill)}><Library size={14} /><span><strong className="mono">{skill.name}</strong><small>{skill.description}</small></span></button>)}{searching && <p className="palette-empty">正在搜索…</p>}{!searching && searchError && <p className="palette-empty error">搜索失败：{searchError}</p>}{!searching && !searchError && matches.length === 0 && <p className="palette-empty">没有匹配的 skill</p>}</div>
      </section>
    </div>
  );
}

function ScanAgentsDialog({ root, onClose, onApplied }: {
  root: string;
  onClose: () => void;
  onApplied: (message: string) => void;
}) {
  const [candidates, setCandidates] = useState<ScanCandidate[] | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manualName, setManualName] = useState("");
  const [manualTarget, setManualTarget] = useState("");

  useEffect(() => {
    let alive = true;
    scanLocalAgents(root)
      .then((items) => { if (alive) setCandidates(items); })
      .catch((err) => { if (alive) { setWarning(String(err)); setCandidates([]); } });
    return () => { alive = false; };
  }, [root]);

  // 只列出存在且未纳管的候选
  const available = (candidates ?? []).filter((item) => item.exists && !item.managed);

  const toggle = (agent: string) => {
    setSelected((current) => current.includes(agent) ? current.filter((item) => item !== agent) : [...current, agent]);
  };

  const confirmAdd = async () => {
    setApplying(true);
    setError(null);
    try {
      for (const agent of selected) {
        const item = available.find((entry) => entry.agent === agent);
        if (!item) continue;
        await addAgent(root, item.agent, item.target);
      }
      onApplied(`已纳管 ${selected.length} 个 Agent`);
    } catch (err) {
      setError(String(err));
    } finally {
      setApplying(false);
    }
  };

  const addManual = async () => {
    const name = manualName.trim();
    const target = manualTarget.trim();
    if (!name || !target) return;
    setApplying(true);
    setError(null);
    try {
      await addAgent(root, name, target);
      onApplied(`已纳管 ${name}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <section className="assign-dialog" role="dialog" aria-label="扫描本机 Agent" onMouseDown={(event) => event.stopPropagation()}>
        <div className="details-header">
          <div><span className="eyebrow">Scan agents</span><h2>扫描本机 Agent</h2></div>
          <button className="icon-button" aria-label="关闭" onClick={onClose}><X size={17} /></button>
        </div>
        <p className="muted">探测本机常见 Agent 的 skills 目录；勾选确认后纳入 skill-hub 统一管理（可分配、可同步软链）。</p>
        <label className="field-label">发现的 Agent</label>
        <div className="agent-picker" role="group" aria-label="可纳管的本机 Agent">
          {candidates === null && <p className="muted">扫描中…</p>}
          {candidates !== null && available.length === 0 && <p className="muted">未发现可纳管的本机 Agent</p>}
          {available.map((item) => (
            <label key={item.agent} className={`agent-option ${selected.includes(item.agent) ? "checked" : ""}`}>
              <input
                type="checkbox"
                aria-label={item.agent}
                checked={selected.includes(item.agent)}
                onChange={() => toggle(item.agent)}
              />
              <span className="mono">{item.agent}</span>
              <small>{item.target} · {item.skill_count} skills</small>
            </label>
          ))}
          {warning && <div className="detail-warning"><AlertCircle size={14} />扫描失败：{warning}</div>}
        </div>
        <label className="field-label" htmlFor="manual-agent-name">没扫到？手动添加（兜底）</label>
        <div className="source-input-row">
          <input
            id="manual-agent-name"
            className="text-input mono"
            value={manualName}
            placeholder="Agent 名称，如 my-agent"
            aria-label="Agent 名称"
            onChange={(event) => setManualName(event.target.value)}
          />
          <input
            id="manual-agent-target"
            className="text-input mono"
            value={manualTarget}
            placeholder="/path/to/skills"
            aria-label="Skills 目录"
            onChange={(event) => setManualTarget(event.target.value)}
          />
          <button
            type="button"
            className="browse-button"
            aria-label="手动添加"
            disabled={!manualName.trim() || !manualTarget.trim() || applying}
            onClick={() => { void addManual(); }}
          >
            手动添加
          </button>
        </div>
        {error && <div className="detail-warning"><AlertCircle size={14} />纳管失败：{error}</div>}
        <div className="dialog-actions">
          <button onClick={onClose}>取消</button>
          <button className="primary" disabled={selected.length === 0 || applying} onClick={() => { void confirmAdd(); }}>
            {applying ? "纳管中…" : "确认纳管"}
          </button>
        </div>
      </section>
    </div>
  );
}

function AssignDialog({ root, skill, agentTargets, existingProfiles, onClose, onApplied }: {
  root: string;
  skill: RegistryEntry;
  agentTargets: AgentTarget[];
  existingProfiles: ProfilePayload[];
  onClose: () => void;
  onApplied: () => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [previews, setPreviews] = useState<Record<string, SyncResultPayload>>({});
  const [previewing, setPreviewing] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleAgent = (agent: string) => {
    setSelected((current) => current.includes(agent) ? current.filter((item) => item !== agent) : [...current, agent]);
    setPreviews({});
  };

  const selectedTargets = agentTargets.filter((item) => selected.includes(item.agent));

  const runPreview = async () => {
    setPreviewing(true);
    setError(null);
    try {
      const results: Record<string, SyncResultPayload> = {};
      for (const item of selectedTargets) {
        const existing = existingProfiles.find((profile) => profile.agent === item.agent);
        const pendingSkill = !existing || !existing.skills.includes(skill.name);
        // 预览基准必须与执行一致：有磁盘 profile 时用其真实名字，否则 CLI 找不到 profile
        // 会回退成空 candidate，把该 profile 已有的 skill 误报成「将移除」
        results[item.agent] = await dryRunSync(
          root,
          item.target,
          existing ? existing.name : item.agent,
          { addSkills: pendingSkill ? [skill.name] : [], agent: item.agent },
        );
      }
      setPreviews(results);
    } catch (err) {
      setError(String(err));
      setPreviews({});
    } finally {
      setPreviewing(false);
    }
  };

  const runApply = async () => {
    setApplying(true);
    setError(null);
    try {
      for (const item of selectedTargets) {
        const existing = existingProfiles.find((profile) => profile.agent === item.agent);
        const pendingSkill = !existing || !existing.skills.includes(skill.name);
        if (!existing) {
          await createProfile(root, item.agent, item.agent, [skill.name]);
        } else if (pendingSkill) {
          // existing.name 是磁盘 profile 名（可能是 claude-code），写操作必须用它定位
          await updateProfile(root, existing.name, { addSkills: [skill.name] });
        }
        await applySync(root, item.target, existing ? existing.name : item.agent);
      }
      onApplied();
    } catch (err) {
      setError(String(err));
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <section className="assign-dialog" role="dialog" aria-label="分配给 Agent" onMouseDown={(event) => event.stopPropagation()}>
        <div className="details-header">
          <div><span className="eyebrow">Assign skill</span><h2 className="mono">{skill.name}</h2></div>
          <button className="icon-button" aria-label="关闭" onClick={onClose}><X size={17} /></button>
        </div>
        <label className="field-label">目标 Agent（可多选）</label>
        <div className="agent-picker" role="group" aria-label="目标 Agent">
          {agentTargets.map((item) => (
            <label key={item.agent} className={`agent-option ${selected.includes(item.agent) ? "checked" : ""}`}>
              <input
                type="checkbox"
                aria-label={item.agent}
                checked={selected.includes(item.agent)}
                onChange={() => toggleAgent(item.agent)}
              />
              <span className="mono">{item.agent}</span>
              <small>{item.target}</small>
            </label>
          ))}
          {agentTargets.length === 0 && <p className="muted">未检测到 Agent</p>}
        </div>
        <div className="dialog-body">
          {selectedTargets.length > 0 && <p className="muted">将写入 {selectedTargets.length} 个 profile 并同步到 {selectedTargets.map((item) => item.agent).join("、")}</p>}
          {Object.entries(previews).map(([agent, preview]) => (
            <div className="preview-summary" role="status" key={agent}>
              <p className="status-ok"><CheckCircle2 size={14} /> {agent} 预览就绪（dry-run，未写入任何文件）</p>
              <p className="preview-line">将链接 {preview.linked.length} 个 skill{preview.missing.length > 0 ? `，${preview.missing.length} 个缺失` : ""}{preview.removed.length > 0 ? `，将移除 ${preview.removed.length} 个链接` : ""}</p>
              {preview.linked.length > 0 && <div className="badge-row">{preview.linked.map((name) => <span key={name} className="badge mono">{name}</span>)}</div>}
              {preview.missing.length > 0 && <p className="status-bad">缺失：{preview.missing.join("、")}</p>}
              {preview.removed.length > 0 && <p className="status-bad">将移除：{preview.removed.join("、")}</p>}
            </div>
          ))}
        </div>
        {error && <div className="detail-warning"><AlertCircle size={14} />{error}</div>}
        <div className="dialog-actions">
          <button onClick={onClose}>取消</button>
          <button className="secondary" disabled={selectedTargets.length === 0 || previewing} onClick={() => { void runPreview(); }}>
            {previewing ? "预览中…" : "预览同步"}
          </button>
          <button className="primary" disabled={selectedTargets.length === 0 || applying || Object.keys(previews).length === 0} onClick={() => { void runApply(); }}>
            {applying ? "同步中…" : "确认分配并同步"}
          </button>
        </div>
      </section>
    </div>
  );
}

function ImportSkillDialog({ root, onClose, onImported }: {
  root: string;
  onClose: () => void;
  onImported: (message: string) => void;
}) {
  const [source, setSource] = useState("");
  const [name, setName] = useState("");
  const [force, setForce] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const browse = async () => {
    try {
      const picked = await pickDirectory();
      if (picked) setSource(picked);
    } catch (err) {
      setError(String(err));
    }
  };

  const submit = async () => {
    const trimmed = source.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await importSkill(root, {
        source: trimmed,
        name: name.trim() || undefined,
        force: force || undefined,
      });
      onImported(`已导入 ${result.skill}${result.replaced ? "（覆盖）" : ""}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <section className="assign-dialog" role="dialog" aria-label="导入 skill" onMouseDown={(event) => event.stopPropagation()}>
        <div className="details-header">
          <div><span className="eyebrow">Import skill</span><h2>导入本地 skill</h2></div>
          <button className="icon-button" aria-label="关闭" onClick={onClose}><X size={17} /></button>
        </div>
        <label className="field-label" htmlFor="import-source">来源目录</label>
        <div className="source-input-row">
          <input
            id="import-source"
            className="text-input mono"
            value={source}
            placeholder="/path/to/skill-directory"
            onChange={(event) => setSource(event.target.value)}
          />
          <button type="button" className="browse-button" aria-label="浏览…" onClick={() => { void browse(); }}>
            浏览…
          </button>
        </div>
        <label className="field-label" htmlFor="import-name">Skill 名称（可选）</label>
        <input
          id="import-name"
          className="text-input mono"
          value={name}
          placeholder="默认取目录名"
          onChange={(event) => setName(event.target.value)}
        />
        <label className="agent-option">
          <input
            type="checkbox"
            aria-label="覆盖已有同名 skill"
            checked={force}
            onChange={(event) => setForce(event.target.checked)}
          />
          <span>覆盖已有同名 skill（--force）</span>
        </label>
        {error && <div className="detail-warning"><AlertCircle size={14} />导入失败：{error}</div>}
        <div className="dialog-actions">
          <button onClick={onClose}>取消</button>
          <button className="primary" disabled={!source.trim() || submitting} onClick={() => { void submit(); }}>
            {submitting ? "导入中…" : "导入"}
          </button>
        </div>
      </section>
    </div>
  );
}

function RemoveSkillDialog({ root, skill, profiles, onClose, onRemoved }: {
  root: string;
  skill: RegistryEntry;
  profiles: ProfilePayload[];
  onClose: () => void;
  onRemoved: (message: string) => void;
}) {
  const [purgeSource, setPurgeSource] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const affected = profiles.filter((profile) => profile.skills.includes(skill.name));

  const confirmRemove = async () => {
    setRemoving(true);
    setError(null);
    try {
      const result = await removeSkill(root, skill.name, { purgeSource: purgeSource || undefined });
      onRemoved(`已移除 ${result.skill}${result.updated_profiles.length > 0 ? `，已从 ${result.updated_profiles.length} 个 profile 移除` : ""}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setRemoving(false);
    }
  };

  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <section className="assign-dialog" role="dialog" aria-label="删除 skill" onMouseDown={(event) => event.stopPropagation()}>
        <div className="details-header">
          <div><span className="eyebrow">Delete skill</span><h2 className="mono">{skill.name}</h2></div>
          <button className="icon-button" aria-label="关闭" onClick={onClose}><X size={17} /></button>
        </div>
        <p className="muted">将从 vault 真实删除该 skill 目录并重建 registry，此操作不可恢复。</p>
        <div className="detail-section">
          <h3>影响的 Profiles</h3>
          <div className="badge-row">
            {affected.length > 0
              ? affected.map((profile) => <span key={profile.name} className="badge agent">{profile.name}</span>)
              : <span className="muted">无 profile 引用</span>}
          </div>
        </div>
        <label className="agent-option">
          <input
            type="checkbox"
            aria-label="同时清除来源记录"
            checked={purgeSource}
            onChange={(event) => setPurgeSource(event.target.checked)}
          />
          <span>同时清除来源记录（--purge-source）</span>
        </label>
        {error && <div className="detail-warning"><AlertCircle size={14} />移除失败：{error}</div>}
        <div className="dialog-actions">
          <button onClick={onClose}>取消</button>
          <button className="danger" disabled={removing} onClick={() => { void confirmRemove(); }}>
            {removing ? "删除中…" : "确认删除"}
          </button>
        </div>
      </section>
    </div>
  );
}

function UnassignDialog({ root, skill, profiles, agentTargets, onClose, onUnassigned }: {
  root: string;
  skill: RegistryEntry;
  profiles: ProfilePayload[];
  agentTargets: AgentTarget[];
  onClose: () => void;
  onUnassigned: (message: string) => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 只列出当前持有该 skill 的 agent profile（canonical agent 名做 join key，写操作用 profile.name 定位）
  const holders = profiles.filter((profile) => profile.skills.includes(skill.name));
  const holderTargets = agentTargets
    .map((target) => {
      const holder = holders.find((profile) => profile.agent === target.agent);
      return holder ? { target, holder } : null;
    })
    .filter((item): item is { target: AgentTarget; holder: ProfilePayload } => item !== null);

  const toggle = (agent: string) => {
    setSelected((current) => current.includes(agent) ? current.filter((item) => item !== agent) : [...current, agent]);
  };

  const confirmUnassign = async () => {
    setSubmitting(true);
    setError(null);
    try {
      for (const { target, holder } of holderTargets.filter((item) => selected.includes(item.target.agent))) {
        // updateProfile 按磁盘 profile 名定位（claude-code），applySync 同理
        await updateProfile(root, holder.name, { removeSkills: [skill.name] });
        await applySync(root, target.target, holder.name);
      }
      onUnassigned(`已从 ${selected.length} 个 Agent 移除 ${skill.name}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <section className="assign-dialog" role="dialog" aria-label="从 Agent 移除" onMouseDown={(event) => event.stopPropagation()}>
        <div className="details-header">
          <div><span className="eyebrow">Unassign skill</span><h2 className="mono">{skill.name}</h2></div>
          <button className="icon-button" aria-label="关闭" onClick={onClose}><X size={17} /></button>
        </div>
        <p className="muted">仅从所选 Agent 的 profile 中移除该 skill 并同步清理其软链接；skill 本体保留在 vault 中。</p>
        <label className="field-label">选择要移除的 Agent</label>
        <div className="agent-picker" role="group" aria-label="要移除的 Agent">
          {holderTargets.map(({ target }) => (
            <label key={target.agent} className={`agent-option ${selected.includes(target.agent) ? "checked" : ""}`}>
              <input
                type="checkbox"
                aria-label={target.agent}
                checked={selected.includes(target.agent)}
                onChange={() => toggle(target.agent)}
              />
              <span className="mono">{target.agent}</span>
              <small>{target.target}</small>
            </label>
          ))}
          {holderTargets.length === 0 && <p className="muted">该 skill 未加入任何 Agent</p>}
        </div>
        {error && <div className="detail-warning"><AlertCircle size={14} />移除失败：{error}</div>}
        <div className="dialog-actions">
          <button onClick={onClose}>取消</button>
          <button className="danger" disabled={selected.length === 0 || submitting} onClick={() => { void confirmUnassign(); }}>
            {submitting ? "移除中…" : "确认移除"}
          </button>
        </div>
      </section>
    </div>
  );
}
