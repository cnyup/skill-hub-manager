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
  auditAll,
  doctor,
  findSkills,
  getProfile,
  getSkillDetail,
  getSkillSource,
  getVersion,
  listProfiles,
  listSkills,
  registryDoctor,
  resolveWorkspaceRoot,
  validateProfiles,
} from "./api/client";
import type {
  AuditReport,
  ProfilePayload,
  ProfileValidation,
  RegistryEntry,
  SkillDetail,
  SkillSourceRecord,
} from "./api/client";

type View = "library" | "agents" | "doctor";
type DetailTab = "preview" | "source" | "profiles";

interface HealthState {
  registry: { ok: boolean; issues: string[] };
  links: { broken: string[]; expected_missing: string[]; hasIssues: boolean };
  profiles: ProfileValidation[];
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
  const [selectedSkill, setSelectedSkill] = useState<RegistryEntry | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<SkillDetail | null>(null);
  const [selectedSource, setSelectedSource] = useState<SkillSourceRecord | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailWarning, setDetailWarning] = useState<string | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [query, setQuery] = useState("");

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
        const [nextSkills, nextProfileNames, nextAudit, nextRegistry, nextLinks, nextValidation] = await Promise.all([
          listSkills(root).catch((error) => { nextWarnings.push(`Library: ${String(error)}`); return []; }),
          listProfiles(root).catch((error) => { nextWarnings.push(`Profiles: ${String(error)}`); return []; }),
          auditAll(root).catch((error) => { nextWarnings.push(`Audit: ${String(error)}`); return []; }),
          registryDoctor(root).catch((error) => { nextWarnings.push(`Registry doctor: ${String(error)}`); return EMPTY_HEALTH.registry; }),
          doctor(root).catch((error) => { nextWarnings.push(`Link doctor: ${String(error)}`); return EMPTY_HEALTH.links; }),
          validateProfiles(root).catch((error) => { nextWarnings.push(`Profile validate: ${String(error)}`); return []; }),
        ]);
        const nextProfiles = await Promise.all(
          nextProfileNames.map((name) => getProfile(root, name).catch((error) => {
            nextWarnings.push(`Profile ${name}: ${String(error)}`);
            return null;
          })),
        );
        if (!alive) return;
        setSkills(nextSkills);
        setProfileNames(nextProfileNames);
        setAudit(nextAudit);
        setProfiles(nextProfiles.filter((profile): profile is ProfilePayload => profile !== null));
        setHealth({ registry: nextRegistry, links: nextLinks, profiles: nextValidation });
        setWarnings(nextWarnings);
      } catch (error) {
        if (alive) setFatalError(String(error));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [root]);

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
      <Sidebar view={view} profiles={profileNames} version={version} onNavigate={navigate} />
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
          <button className="command-trigger" onClick={() => setPaletteOpen(true)}>
            <Search size={14} /> 搜索或执行命令 <kbd>⌘K</kbd>
          </button>
        </header>

        {warnings.length > 0 && (
          <div className="warning-banner" role="status">
            <AlertCircle size={15} /> 部分数据加载失败：{warnings.join("；")}
          </div>
        )}

        {loading ? (
          <div className="empty-state">正在读取 workspace…</div>
        ) : view === "library" ? (
          <LibraryView skills={skills} profiles={profileNames} audit={audit} onOpenSkill={openSkill} />
        ) : view === "agents" ? (
          <AgentsView profiles={profiles} audit={audit} />
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

function Sidebar({ view, profiles, version, onNavigate }: {
  view: View;
  profiles: string[];
  version: string;
  onNavigate: (view: View) => void;
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
        {profiles.map((profile) => <span key={profile} className="profile-link">{profile}</span>)}
        {profiles.length === 0 && <span className="profile-link muted">暂无 profile</span>}
      </div>
      <div className="sidebar-footer mono">{version}</div>
    </aside>
  );
}

function NavButton({ active, icon, label, onClick }: { active: boolean; icon: React.ReactNode; label: string; onClick: () => void }) {
  return <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}>{icon}{label}</button>;
}

function LibraryView({ skills, profiles, audit, onOpenSkill }: {
  skills: RegistryEntry[];
  profiles: string[];
  audit: AuditReport[];
  onOpenSkill: (skill: RegistryEntry) => void;
}) {
  if (skills.length === 0) return <div className="empty-state">vault 为空——用 CLI 导入第一个 skill 试试</div>;
  return (
    <section className="card-grid" aria-label="Skill library">
      {skills.map((skill) => (
        <button key={skill.name} className="skill-card" aria-label={`打开 ${skill.name}`} onClick={() => onOpenSkill(skill)}>
          <div className="card-title mono">{skill.name}</div>
          <p>{skill.description ?? "（无描述）"}</p>
          <div className="badge-row">
            {profiles.map((profile) => {
              const report = audit.find((item) => item.profile === profile);
              const enabled = report?.effective_skills.includes(skill.name) ?? false;
              return <span key={profile} className={`badge agent ${enabled ? "enabled" : "disabled"}`}>{report?.agent ?? profile}</span>;
            })}
            {(skill.tags ?? []).slice(0, 2).map((tag) => <span key={tag} className="badge">{tag}</span>)}
          </div>
        </button>
      ))}
    </section>
  );
}

function AgentsView({ profiles, audit }: { profiles: ProfilePayload[]; audit: AuditReport[] }) {
  if (profiles.length === 0) return <div className="empty-state">尚未创建 profile</div>;
  return (
    <section className="stack-list">
      {profiles.map((profile) => {
        const report = audit.find((item) => item.profile === profile.name);
        return (
          <article className="panel" key={profile.name}>
            <div className="panel-heading"><div><h2>{profile.name}</h2><span className="badge agent enabled">{profile.agent}</span></div><span>{profile.effective_skills.length} effective</span></div>
            <div className="detail-section"><h3>Effective skills</h3><div className="badge-row">{profile.effective_skills.map((skill) => <span className="badge mono" key={skill}>{skill}</span>)}</div></div>
            <div className="detail-section"><h3>Exclude patterns</h3><div className="badge-row">{profile.exclude.length ? profile.exclude.map((item) => <span className="badge mono" key={item}>{item}</span>) : <span className="muted">无</span>}</div></div>
            {(report?.missing_skills.length ?? 0) > 0 && <div className="issue-list">{report?.missing_skills.map((item) => <span key={item}><AlertCircle size={14} />{item}</span>)}</div>}
          </article>
        );
      })}
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

function SkillDetails({ skill, content, source, profiles, loading, warning, onClose }: {
  skill: RegistryEntry;
  content: string;
  source: SkillSourceRecord | null;
  profiles: ProfilePayload[];
  loading: boolean;
  warning: string | null;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<DetailTab>("preview");
  const memberships = profiles.filter((profile) => profile.effective_skills.includes(skill.name));
  return (
    <aside className="details-panel" aria-label="Skill details">
      <div className="details-header"><div><span className="eyebrow">Skill details</span><h2 className="mono">{skill.name}</h2></div><button className="icon-button" aria-label="关闭详情" onClick={onClose}><X size={17} /></button></div>
      <p className="detail-description">{skill.description ?? "（无描述）"}</p>
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
