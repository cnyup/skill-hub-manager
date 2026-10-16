import { useEffect, useState } from "react";
import { getVersion, listSkills, listProfiles, auditAll } from "./api/client";
import type { RegistryEntry, AuditReport } from "./api/client";

export default function App() {
  const [version, setVersion] = useState<string>("(连接中…)");
  const [error, setError] = useState<string | null>(null);
  const [skills, setSkills] = useState<RegistryEntry[]>([]);
  const [profiles, setProfiles] = useState<string[]>([]);
  const [audit, setAudit] = useState<AuditReport[]>([]);

  const root = "~/.skill-hub";

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const v = await getVersion();
        if (!alive) return;
        setVersion(v);
        const [s, p, a] = await Promise.all([
          listSkills(root).catch(() => []),
          listProfiles(root).catch(() => []),
          auditAll(root).catch(() => []),
        ]);
        if (!alive) return;
        setSkills(s);
        setProfiles(p);
        setAudit(a);
      } catch (e) {
        if (alive) setError(String(e));
      }
    })();
    return () => {
      alive = false;
    };
  }, [root]);

  if (error) {
    return (
      <div style={{ padding: 40, color: "#71717a" }}>
        <h2 style={{ color: "#18181b" }}>CLI 连接失败</h2>
        <p className="mono" style={{ fontSize: 12 }}>{error}</p>
        <p>请确认 skill-hub 包装器已注册到 Tauri shell 白名单（tauri.conf.json → plugin-shell.scope）。</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100%" }}>
      {/* 侧栏 */}
      <aside
        style={{
          width: 220,
          background: "#fafafa",
          borderRight: "1px solid #e4e4e7",
          padding: "14px 10px",
          flexShrink: 0,
        }}
      >
        <div style={{ fontWeight: 700, padding: "4px 10px 14px", fontSize: 13 }}>skill-hub</div>
        <div style={{ padding: "7px 10px", background: "#f4f4f5", borderRadius: 7, fontWeight: 600, fontSize: 13 }}>
          Library
        </div>
        <div style={{ padding: "16px 10px 6px", fontSize: 11, fontWeight: 600, color: "#a1a1aa", textTransform: "uppercase", letterSpacing: 0.4 }}>
          Agents
        </div>
        {profiles.map((p) => (
          <div key={p} style={{ padding: "7px 10px", borderRadius: 7, fontSize: 13, color: "#3f3f46" }}>
            {p}
          </div>
        ))}
        <div style={{ marginTop: 24, padding: "0 10px", fontSize: 11, color: "#a1a1aa" }} className="mono">
          {version}
        </div>
      </aside>

      {/* 主区 */}
      <main style={{ flex: 1, padding: 20, overflow: "auto" }}>
        <h1 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 2px" }}>Library</h1>
        <p style={{ fontSize: 12.5, color: "#71717a", margin: "0 0 16px" }}>
          {skills.length} skills · {profiles.length} profiles
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(230px,1fr))", gap: 12 }}>
          {skills.map((s) => {
            const exposure = new Set(
              audit.filter((r) => r.effective_skills.includes(s.name)).map((r) => r.agent),
            );
            return (
              <div
                key={s.name}
                style={{
                  border: "1px solid #e4e4e7",
                  borderRadius: 10,
                  padding: 14,
                  background: "#fff",
                }}
              >
                <div className="mono" style={{ fontWeight: 600, fontSize: 13.5 }}>{s.name}</div>
                <div style={{ fontSize: 12, color: "#71717a", margin: "5px 0 10px", lineHeight: 1.5 }}>
                  {s.description ?? "（无描述）"}
                </div>
                <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                  {profiles.map((p) => {
                    const agent = audit.find((r) => r.profile === p)?.agent ?? p;
                    const on = audit.find((r) => r.profile === p)?.effective_skills.includes(s.name);
                    return (
                      <span
                        key={p}
                        style={{
                          fontSize: 10.5,
                          fontWeight: 600,
                          padding: "2px 8px",
                          borderRadius: 99,
                          ...(on
                            ? { background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" }
                            : { background: "#fafafa", color: "#a1a1aa", border: "1px dashed #d4d4d8" }),
                        }}
                      >
                        {agent}
                      </span>
                    );
                  })}
                  {exposure.size === 0 && profiles.length === 0 && (
                    <span style={{ fontSize: 10.5, color: "#a1a1aa" }}>（无 profile）</span>
                  )}
                </div>
              </div>
            );
          })}
          {skills.length === 0 && (
            <div style={{ color: "#71717a", gridColumn: "1 / -1", textAlign: "center", padding: 40 }}>
              vault 为空——用 CLI 导入第一个 skill 试试
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
