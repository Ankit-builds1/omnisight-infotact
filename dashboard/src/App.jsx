import { useState, useEffect } from "react";

const API_BASE = "http://127.0.0.1:8000";

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
  const [prs, setPrs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [rejectReasonMap, setRejectReasonMap] = useState({});

  const fetchPRs = () => {
    setLoading(true);
    setError(null);
    fetch(API_BASE + "/prs")
      .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then((data) => {
        setPrs(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchPRs();
  }, []);

  const handleApprove = async (prNumber) => {
    if (!confirm("PR #" + prNumber + " ko approve (merge) karna hai?")) return;
    setActionLoading(prNumber);
    try {
      const res = await fetch(API_BASE + "/prs/" + prNumber + "/approve", {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Approve failed");
      alert("PR #" + prNumber + " merged successfully!");
      fetchPRs();
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

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "2.5rem 2rem", maxWidth: "900px", margin: "0 auto", color: "#eee" }}>
      <div style={{ textAlign: "center", marginBottom: "2rem", paddingTop: "1rem" }}>
        <h1 style={{ margin: "0 0 0.5rem 0", fontSize: "2rem", fontWeight: 700 }}>
          OmniSight QA Review Dashboard
        </h1>
        <p style={{ color: "#999", margin: 0, fontSize: "0.95rem" }}>
          Review and approve or reject AI-generated UI fix Pull Requests.
        </p>
      </div>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", padding: "1.25rem", background: "#1a1a1a", borderRadius: "10px", border: "1px solid #2a2a2a" }}>
        <StatBox label="Open PRs" value={totalPRs} highlight={false} />
        <StatBox label="Needs Review" value={needsReviewCount} highlight={needsReviewCount > 0} />
        <StatBox label="Avg Confidence" value={avgConfidence} highlight={false} />
      </div>

      <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
        <button onClick={fetchPRs} style={{ padding: "0.6rem 1.4rem", cursor: "pointer", background: "#2a2a2a", color: "#eee", border: "1px solid #3a3a3a", borderRadius: "8px", fontSize: "0.9rem" }}>
          Refresh
        </button>
      </div>

      {loading && <p style={{ textAlign: "center", color: "#999" }}>Loading PRs...</p>}
      {error && <p style={{ textAlign: "center", color: "#e74c3c" }}>Error: {error}</p>}
      {!loading && !error && prs.length === 0 && (
        <p style={{ textAlign: "center", color: "#888" }}>No open PRs right now.</p>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {prs.map(function (pr) {
          return (
            <div key={pr.number} style={{ border: "2px solid " + confidenceColor(pr.confidence), borderRadius: "12px", padding: "1.5rem", background: "#161616" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "0.75rem" }}>
                <div>
                  <h3 style={{ margin: "0 0 0.4rem 0", fontSize: "1.1rem", lineHeight: 1.4 }}>
                    {"#" + pr.number + " - " + pr.title}
                  </h3>
                  <a href={pr.url} target="_blank" rel="noreferrer" style={{ fontSize: "0.85rem", color: "#5dade2", textDecoration: "none" }}>
                    View on GitHub
                  </a>
                </div>
                {pr.needs_review && (
                  <span style={{ background: "#e74c3c", color: "white", padding: "0.3rem 0.7rem", borderRadius: "6px", fontSize: "0.75rem", fontWeight: "bold", whiteSpace: "nowrap" }}>
                    NEEDS REVIEW
                  </span>
                )}
              </div>

              <div style={{ display: "flex", gap: "0.6rem", margin: "0.75rem 0 1rem 0", fontSize: "0.85rem", flexWrap: "wrap", alignItems: "center" }}>
                <span style={{ background: severityBadgeColor(pr.severity), padding: "0.3rem 0.7rem", borderRadius: "6px", color: "white", fontWeight: 600 }}>
                  {pr.severity || "N/A"}
                </span>
                <span style={{ background: confidenceColor(pr.confidence), padding: "0.3rem 0.7rem", borderRadius: "6px", color: "white", fontWeight: 600 }}>
                  {"Confidence: " + (pr.confidence !== null && pr.confidence !== undefined ? pr.confidence : "N/A")}
                </span>
                <span style={{ color: "#888" }}>{"Branch: " + pr.branch}</span>
              </div>

              <div style={{ display: "flex", gap: "0.6rem", alignItems: "center", flexWrap: "wrap" }}>
                <button
                  onClick={function () { handleApprove(pr.number); }}
                  disabled={actionLoading === pr.number}
                  style={{ background: "#2ecc71", color: "white", border: "none", padding: "0.6rem 1.1rem", borderRadius: "7px", cursor: "pointer", fontWeight: 600, fontSize: "0.9rem" }}
                >
                  Approve and Merge
                </button>

                <input
                  type="text"
                  placeholder="Rejection reason (optional)"
                  value={rejectReasonMap[pr.number] || ""}
                  onChange={function (e) {
                    const updated = Object.assign({}, rejectReasonMap);
                    updated[pr.number] = e.target.value;
                    setRejectReasonMap(updated);
                  }}
                  style={{ padding: "0.6rem 0.8rem", borderRadius: "7px", border: "1px solid #3a3a3a", background: "#1f1f1f", color: "#eee", flex: 1, minWidth: "150px", fontSize: "0.9rem" }}
                />

                <button
                  onClick={function () { handleReject(pr.number); }}
                  disabled={actionLoading === pr.number}
                  style={{ background: "#e74c3c", color: "white", border: "none", padding: "0.6rem 1.1rem", borderRadius: "7px", cursor: "pointer", fontWeight: 600, fontSize: "0.9rem" }}
                >
                  Reject
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatBox(props) {
  return (
    <div style={{ textAlign: "center", flex: 1 }}>
      <div style={{ fontSize: "1.6rem", fontWeight: 700, color: props.highlight ? "#e74c3c" : "#eee" }}>
        {props.value}
      </div>
      <div style={{ fontSize: "0.8rem", color: "#888", marginTop: "0.2rem" }}>{props.label}</div>
    </div>
  );
}