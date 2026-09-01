import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const REFRESH_INTERVAL_MS = 15000;

function confidenceColor(confidence) {
  if (confidence === null || confidence === undefined) return "#888";
  if (confidence >= 0.8) return "#2ecc71";
  if (confidence >= 0.6) return "#f1c40f";
  return "#e74c3c";
}

function severityBadgeColor(severity) {
  if (severity === "Critical") return "#e74c3c";
  if (severity === "Major") return "#f39c12";
  if (severity === "Minor") return "#3498db";
  return "#888";
}

export default function App() {
  const [view, setView] = useState("open");
  const [prs, setPrs] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [rejectReasonMap, setRejectReasonMap] = useState({});
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchPRs = () => {
    fetch(API_BASE + "/prs")
      .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then((data) => {
        setPrs(data);
        setLoading(false);
        setLastUpdated(new Date());
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  const fetchHistory = () => {
    fetch(API_BASE + "/prs/history")
      .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then((data) => setHistory(data))
      .catch((err) => console.error("Failed to load history:", err));
  };

  useEffect(() => {
    setLoading(true);
    fetchPRs();
    fetchHistory();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      fetchPRs();
      fetchHistory();
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (prNumber) => {
    if (!confirm("PR #" + prNumber + " ko approve (merge) karna hai?")) return;
    setActionLoading(prNumber);
    try {
      const res = await fetch(API_BASE + "/prs/" + prNumber + "/approve", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Approve failed");
      alert("PR #" + prNumber + " merged successfully!");
      fetchPRs();
      fetchHistory();
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (prNumber) => {
    const reason = rejectReasonMap[prNumber] || "Rejected by QA manager";
    if (!confirm("PR #" + prNumber + " ko reject karna hai?\nReason: " + reason)) return;
    setActionLoading(prNumber);
    try {
      const res = await fetch(API_BASE + "/prs/" + prNumber + "/reject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: reason }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Reject failed");
      alert("PR #" + prNumber + " closed.");
      fetchPRs();
      fetchHistory();
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const totalPRs = prs.length;
  const needsReviewCount = prs.filter(function (p) { return p.needs_review; }).length;
  const avgConfidence = totalPRs > 0
    ? (prs.reduce(function (sum, p) { return sum + (p.confidence || 0); }, 0) / totalPRs).toFixed(2)
    : "N/A";
  const approvedCount = history.filter(function (h) { return h.decision === "approved"; }).length;
  const rejectedCount = history.filter(function (h) { return h.decision === "rejected"; }).length;

  return (
    <div style={styles.page}>
      <style>{globalAnimations}</style>

      <div style={{ ...styles.header, animation: "fadeSlideDown 0.6s ease-out" }}>
        <h1 style={styles.title}>OmniSight <span style={styles.titleAccent}>QA Review</span></h1>
        <p style={styles.subtitle}>Review and approve or reject AI-generated UI fix Pull Requests.</p>
        {lastUpdated && (
          <p style={styles.timestamp}>
            <span style={styles.livePulse}></span>
            Auto-refreshes every 15s · Last updated {lastUpdated.toLocaleTimeString()}
          </p>
        )}
      </div>

      <div style={{ ...styles.statBar, animation: "fadeSlideUp 0.6s ease-out 0.1s both" }}>
        <StatBox label="Open PRs" value={totalPRs} />
        <StatBox label="Needs Review" value={needsReviewCount} highlight={needsReviewCount > 0} />
        <StatBox label="Avg Confidence" value={avgConfidence} />
        <StatBox label="Approved" value={approvedCount} accent="#2ecc71" />
        <StatBox label="Rejected" value={rejectedCount} accent="#e74c3c" />
      </div>

      <div style={{ ...styles.tabBar, animation: "fadeSlideUp 0.6s ease-out 0.2s both" }}>
        <TabButton label="Open PRs" active={view === "open"} onClick={() => setView("open")} />
        <TabButton label="History" active={view === "history"} onClick={() => setView("history")} />
        <button style={styles.refreshBtn} onClick={() => { fetchPRs(); fetchHistory(); }}>
          ⟳ Refresh Now
        </button>
      </div>

      {view === "open" && (
        <div key="open-view" style={{ animation: "fadeIn 0.4s ease-out" }}>
          {loading && <p style={styles.mutedCenter}>Loading PRs...</p>}
          {error && <p style={{ ...styles.mutedCenter, color: "#e74c3c" }}>Error: {error}</p>}
          {!loading && !error && prs.length === 0 && (
            <p style={styles.mutedCenter}>No open PRs right now.</p>
          )}

          <div style={styles.cardList}>
            {prs.map(function (pr, idx) {
              return (
                <div
                  key={pr.number}
                  style={{
                    ...styles.card,
                    borderColor: confidenceColor(pr.confidence),
                    animation: `fadeSlideUp 0.5s ease-out ${0.05 * idx}s both`,
                  }}
                  className="pr-card"
                >
                  <div style={styles.cardTop}>
                    <div>
                      <h3 style={styles.cardTitle}>{"#" + pr.number + " — " + pr.title}</h3>
                      <a href={pr.url} target="_blank" rel="noreferrer" style={styles.cardLink}>
                        View on GitHub ↗
                      </a>
                    </div>
                    {pr.needs_review && <span style={styles.reviewBadge}>NEEDS REVIEW</span>}
                  </div>

                  <div style={styles.badgeRow}>
                    <span style={{ ...styles.badge, background: severityBadgeColor(pr.severity) }}>
                      {pr.severity || "N/A"}
                    </span>
                    <span style={{ ...styles.badge, background: confidenceColor(pr.confidence) }}>
                      Confidence: {pr.confidence ?? "N/A"}
                    </span>
                    <span style={styles.branchText}>Branch: {pr.branch}</span>
                  </div>

                  <div style={styles.actionRow}>
                    <button
                      className="btn-hover"
                      onClick={() => handleApprove(pr.number)}
                      disabled={actionLoading === pr.number}
                      style={styles.approveBtn}
                    >
                      ✓ Approve & Merge
                    </button>

                    <input
                      type="text"
                      placeholder="Rejection reason (optional)"
                      value={rejectReasonMap[pr.number] || ""}
                      onChange={(e) => {
                        const updated = Object.assign({}, rejectReasonMap);
                        updated[pr.number] = e.target.value;
                        setRejectReasonMap(updated);
                      }}
                      style={styles.input}
                    />

                    <button
                      className="btn-hover"
                      onClick={() => handleReject(pr.number)}
                      disabled={actionLoading === pr.number}
                      style={styles.rejectBtn}
                    >
                      ✕ Reject
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {view === "history" && (
        <div key="history-view" style={{ ...styles.cardList, animation: "fadeIn 0.4s ease-out" }}>
          {history.length === 0 && <p style={styles.mutedCenter}>No decision history yet.</p>}
          {history.map(function (h, idx) {
            const isApproved = h.decision === "approved";
            return (
              <div
                key={h.number}
                className="pr-card"
                style={{
                  ...styles.historyCard,
                  borderColor: isApproved ? "#2ecc71" : "#e74c3c",
                  animation: `fadeSlideUp 0.4s ease-out ${0.04 * idx}s both`,
                }}
              >
                <div>
                  <a href={h.url} target="_blank" rel="noreferrer" style={styles.historyLink}>
                    {"#" + h.number + " — " + h.title}
                  </a>
                  <div style={styles.historyMeta}>
                    {h.decided_at ? new Date(h.decided_at).toLocaleString() : "Unknown time"}
                    {h.confidence !== null && h.confidence !== undefined ? " · Confidence: " + h.confidence : ""}
                  </div>
                </div>
                <span style={{ ...styles.decisionTag, background: isApproved ? "#2ecc71" : "#e74c3c" }}>
                  {h.decision}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TabButton({ label, active, onClick }) {
  return (
    <button className="btn-hover" onClick={onClick} style={active ? styles.tabActive : styles.tabInactive}>
      {label}
    </button>
  );
}

function StatBox({ label, value, highlight, accent }) {
  return (
    <div style={styles.statBox} className="stat-pop">
      <div style={{ fontSize: "1.7rem", fontWeight: 800, color: highlight ? "#e74c3c" : accent || "#fff" }}>
        {value}
      </div>
      <div style={{ fontSize: "0.78rem", color: "#8a8a9a", marginTop: "0.2rem", letterSpacing: "0.03em" }}>
        {label}
      </div>
    </div>
  );
}

// ------------------- Animations (CSS keyframes) -------------------
const globalAnimations = `
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeSlideDown {
  from { opacity: 0; transform: translateY(-16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.4); }
  100% { opacity: 1; transform: scale(1); }
}
.btn-hover { transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease; }
.btn-hover:hover:not(:disabled) { transform: translateY(-2px) scale(1.03); box-shadow: 0 6px 16px rgba(0,0,0,0.35); }
.btn-hover:active:not(:disabled) { transform: translateY(0) scale(0.98); }
.pr-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
.pr-card:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(0,0,0,0.4); }
.stat-pop { transition: transform 0.2s ease; }
.stat-pop:hover { transform: scale(1.06); }
`;

// ------------------- Styles -------------------
const styles = {
  page: {
    fontFamily: "'Inter', system-ui, sans-serif",
    padding: "2.5rem 2rem",
    maxWidth: "920px",
    margin: "0 auto",
    color: "#eee",
    background: "radial-gradient(circle at top, #14141c 0%, #0a0a0f 100%)",
    minHeight: "100vh",
  },
  header: { textAlign: "center", marginBottom: "2rem", paddingTop: "1rem" },
  title: { margin: "0 0 0.5rem 0", fontSize: "2.1rem", fontWeight: 800, letterSpacing: "-0.02em" },
  titleAccent: {
    background: "linear-gradient(90deg, #3498db, #9b59b6)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  subtitle: { color: "#999", margin: 0, fontSize: "0.95rem" },
  timestamp: {
    color: "#666", margin: "0.6rem 0 0 0", fontSize: "0.75rem",
    display: "flex", alignItems: "center", justifyContent: "center", gap: "0.4rem",
  },
  livePulse: {
    width: "7px", height: "7px", borderRadius: "50%", background: "#2ecc71",
    display: "inline-block", animation: "pulse 1.8s ease-in-out infinite",
  },
  statBar: {
    display: "flex", gap: "1rem", marginBottom: "1.5rem", padding: "1.4rem",
    background: "rgba(255,255,255,0.03)", borderRadius: "14px",
    border: "1px solid rgba(255,255,255,0.08)", backdropFilter: "blur(10px)",
  },
  statBox: { textAlign: "center", flex: 1, cursor: "default" },
  tabBar: { display: "flex", justifyContent: "center", gap: "0.6rem", marginBottom: "1.75rem" },
  tabActive: {
    padding: "0.65rem 1.5rem", cursor: "pointer",
    background: "linear-gradient(90deg, #3498db, #2980b9)",
    color: "#fff", border: "none", borderRadius: "10px",
    fontSize: "0.9rem", fontWeight: 700, boxShadow: "0 4px 14px rgba(52,152,219,0.4)",
  },
  tabInactive: {
    padding: "0.65rem 1.5rem", cursor: "pointer", background: "rgba(255,255,255,0.05)",
    color: "#ccc", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "10px",
    fontSize: "0.9rem", fontWeight: 500,
  },
  refreshBtn: {
    padding: "0.65rem 1.4rem", cursor: "pointer", background: "rgba(255,255,255,0.05)",
    color: "#ccc", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "10px",
    fontSize: "0.9rem", transition: "transform 0.15s ease",
  },
  mutedCenter: { textAlign: "center", color: "#888" },
  cardList: { display: "flex", flexDirection: "column", gap: "1.25rem" },
  card: {
    border: "2px solid", borderRadius: "16px", padding: "1.6rem",
    background: "rgba(255,255,255,0.03)", backdropFilter: "blur(8px)",
  },
  cardTop: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "0.75rem" },
  cardTitle: { margin: "0 0 0.4rem 0", fontSize: "1.1rem", lineHeight: 1.4, fontWeight: 700 },
  cardLink: { fontSize: "0.85rem", color: "#5dade2", textDecoration: "none" },
  reviewBadge: {
    background: "#e74c3c", color: "white", padding: "0.3rem 0.7rem", borderRadius: "8px",
    fontSize: "0.72rem", fontWeight: 800, whiteSpace: "nowrap", letterSpacing: "0.03em",
  },
  badgeRow: { display: "flex", gap: "0.6rem", margin: "0.75rem 0 1.1rem 0", fontSize: "0.85rem", flexWrap: "wrap", alignItems: "center" },
  badge: { padding: "0.3rem 0.75rem", borderRadius: "8px", color: "white", fontWeight: 700, fontSize: "0.78rem" },
  branchText: { color: "#888", fontSize: "0.78rem" },
  actionRow: { display: "flex", gap: "0.6rem", alignItems: "center", flexWrap: "wrap" },
  approveBtn: {
    background: "linear-gradient(90deg, #27ae60, #2ecc71)", color: "white", border: "none",
    padding: "0.65rem 1.2rem", borderRadius: "9px", cursor: "pointer", fontWeight: 700, fontSize: "0.88rem",
  },
  rejectBtn: {
    background: "linear-gradient(90deg, #c0392b, #e74c3c)", color: "white", border: "none",
    padding: "0.65rem 1.2rem", borderRadius: "9px", cursor: "pointer", fontWeight: 700, fontSize: "0.88rem",
  },
  input: {
    padding: "0.65rem 0.9rem", borderRadius: "9px", border: "1px solid rgba(255,255,255,0.12)",
    background: "rgba(0,0,0,0.3)", color: "#eee", flex: 1, minWidth: "150px", fontSize: "0.88rem",
  },
  historyCard: {
    border: "1px solid", borderRadius: "12px", padding: "1.1rem 1.4rem",
    background: "rgba(255,255,255,0.03)", display: "flex",
    justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem",
  },
  historyLink: { color: "#eee", textDecoration: "none", fontWeight: 700, fontSize: "0.95rem" },
  historyMeta: { fontSize: "0.78rem", color: "#888", marginTop: "0.3rem" },
  decisionTag: {
    color: "white", padding: "0.35rem 0.9rem", borderRadius: "8px",
    fontSize: "0.75rem", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.05em",
  },
};