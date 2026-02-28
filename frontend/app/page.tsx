"use client";

import { useState, useEffect } from "react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? `http://${window.location.hostname}:8000` : "http://127.0.0.1:8000");

type EvidenceItem = {
  goal: string;
  found: boolean;
  content?: string;
  location: string;
  rationale: string;
  confidence: number;
};
type Evidences = Record<string, EvidenceItem[]>;

type RubricDim = { id?: string; name?: string; target_artifact?: string };

type JudgeOpinion = { judge: string; criterion_id: string; score: number; argument: string; cited_evidence?: string[] };
type CriterionResult = {
  dimension_id: string;
  dimension_name: string;
  final_score: number;
  judge_opinions?: JudgeOpinion[];
  dissent_summary?: string | null;
  remediation?: string;
};
type FinalReport = {
  repo_url?: string;
  executive_summary?: string;
  overall_score?: number;
  overall_score_100?: number;
  criteria?: CriterionResult[];
  remediation_plan?: string;
};

function splitEvidencesByArtifact(
  evidences: Evidences,
  rubric: RubricDim[]
): { repo: Evidences; report: Evidences } {
  const repoIds = new Set(
    (rubric || []).filter((d) => d.target_artifact === "github_repo").map((d) => d.id).filter(Boolean)
  );
  const reportIds = new Set(
    (rubric || [])
      .filter((d) => d.target_artifact === "pdf_report" || d.target_artifact === "pdf_images")
      .map((d) => d.id)
      .filter(Boolean)
  );
  const repo: Evidences = {};
  const report: Evidences = {};
  for (const [dimId, items] of Object.entries(evidences)) {
    if (repoIds.has(dimId)) repo[dimId] = items;
    else if (reportIds.has(dimId)) report[dimId] = items;
  }
  return { repo, report };
}

type Tab = "repository" | "document" | "parallelism";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("repository");
  const [rubricDimensions, setRubricDimensions] = useState<RubricDim[]>([]);
  const [rubricError, setRubricError] = useState<string | null>(null);

  const [repoUrl, setRepoUrl] = useState("");
  const [repoReportType, setRepoReportType] = useState<"self" | "peer">("self");
  const [repoLoading, setRepoLoading] = useState(false);
  const [repoError, setRepoError] = useState<string | null>(null);
  const [repoEvidences, setRepoEvidences] = useState<Evidences | null>(null);

  const [docUrl, setDocUrl] = useState("");
  const [docReportType, setDocReportType] = useState<"self" | "peer">("self");
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);
  const [docEvidences, setDocEvidences] = useState<Evidences | null>(null);

  const [parallelRepoUrl, setParallelRepoUrl] = useState("");
  const [parallelDocUrl, setParallelDocUrl] = useState("");
  const [reportType, setReportType] = useState<"self" | "peer">("self");
  const [parallelLoading, setParallelLoading] = useState(false);
  const [parallelError, setParallelError] = useState<string | null>(null);
  const [parallelRepoEvidences, setParallelRepoEvidences] = useState<Evidences | null>(null);
  const [parallelDocEvidences, setParallelDocEvidences] = useState<Evidences | null>(null);

  const [lastFinalReport, setLastFinalReport] = useState<FinalReport | null>(null);

  useEffect(() => {
    setRubricError(null);
    fetch(`${API_URL}/api/rubric`)
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json();
      })
      .then((data) => {
        const dims = data.dimensions ?? [];
        setRubricDimensions(Array.isArray(dims) ? dims : []);
        if (!dims?.length) setRubricError("Rubric empty (check rubric.json in repo root).");
        else setRubricError(null);
      })
      .catch(() => {
        setRubricError(
          `Cannot reach API at ${API_URL}. Start backend: uv run uvicorn src.api:app --port 8000`
        );
      });
  }, []);

  const runRepoAudit = async () => {
    const url = repoUrl.trim();
    if (!url) {
      setRepoError("Enter repository URL.");
      return;
    }
    if (!rubricDimensions.length) {
      setRepoError("Rubric not loaded. Ensure rubric.json exists and API is running.");
      return;
    }
    setRepoError(null);
    setRepoEvidences(null);
    setRepoLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: url, pdf_path: "", report_type: repoReportType }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText || "Request failed");
      setRepoEvidences(data.evidences ?? {});
      setLastFinalReport(data.final_report ?? null);
    } catch (e) {
      setRepoError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setRepoLoading(false);
    }
  };

  const runDocAudit = async () => {
    const url = docUrl.trim();
    if (!url) {
      setDocError("Enter document (PDF) path or URL.");
      return;
    }
    if (!rubricDimensions.length) {
      setDocError("Rubric not loaded. Ensure rubric.json exists and API is running.");
      return;
    }
    setDocError(null);
    setDocEvidences(null);
    setDocLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: "", pdf_path: url, report_type: docReportType }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText || "Request failed");
      setDocEvidences(data.evidences ?? {});
      setLastFinalReport(data.final_report ?? null);
    } catch (e) {
      setDocError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setDocLoading(false);
    }
  };

  const runParallelAudit = async () => {
    const repo = parallelRepoUrl.trim();
    if (!repo) {
      setParallelError("Enter repository URL.");
      return;
    }
    if (!rubricDimensions.length) {
      setParallelError("Rubric not loaded. Ensure rubric.json exists and API is running.");
      return;
    }
    setParallelError(null);
    setParallelRepoEvidences(null);
    setParallelDocEvidences(null);
    setParallelLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          repo_url: repo, 
          pdf_path: parallelDocUrl.trim(),
          report_type: reportType,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText || "Request failed");
      const evidences: Evidences = data.evidences ?? {};
      const { repo: repoEv, report: docEv } = splitEvidencesByArtifact(evidences, rubricDimensions);
      setParallelRepoEvidences(repoEv);
      setParallelDocEvidences(docEv);
      setLastFinalReport(data.final_report ?? null);
    } catch (e) {
      setParallelError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setParallelLoading(false);
    }
  };

  function ReportBlock({ report }: { report: FinalReport }) {
    const score = report.overall_score ?? 0;
    const score100 = report.overall_score_100 ?? Math.round(score * 20);
    const criteria = report.criteria ?? [];
    return (
      <div className="mt-6 rounded-xl border border-amber-500/30 bg-slate-900/50 p-6">
        <h3 className="mb-3 text-lg font-medium text-amber-200">Final report</h3>
        <div className="mb-4 flex items-baseline gap-2">
          <span className="text-3xl font-light text-white">{score.toFixed(1)}</span>
          <span className="text-slate-400">/ 5</span>
          <span className="text-slate-500">({score100}/100)</span>
        </div>
        {report.executive_summary && (
          <p className="mb-4 text-sm text-slate-300">{report.executive_summary}</p>
        )}
        <h4 className="mb-2 text-sm font-medium text-slate-400">Criteria</h4>
        <ul className="space-y-3">
          {criteria.map((c) => (
            <li key={c.dimension_id} className="rounded-lg border border-slate-700/40 bg-slate-800/40 p-3">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-medium text-slate-200">{c.dimension_name}</span>
                <span className="text-amber-200">{c.final_score}/5</span>
              </div>
              {c.dissent_summary && (
                <p className="mb-2 text-xs text-amber-200/80">{c.dissent_summary}</p>
              )}
              {c.judge_opinions?.length ? (
                <ul className="space-y-1 text-xs text-slate-400">
                  {c.judge_opinions.map((op, i) => (
                    <li key={i}>
                      <span className="text-slate-500">{op.judge}:</span> {op.score} — {(op.argument || "").slice(0, 120)}
                      {(op.argument?.length ?? 0) > 120 ? "…" : ""}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
        {report.remediation_plan && (
          <>
            <h4 className="mb-2 mt-4 text-sm font-medium text-slate-400">Remediation</h4>
            <p className="text-sm text-slate-400">{report.remediation_plan}</p>
          </>
        )}
      </div>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "repository", label: "Repository" },
    { id: "document", label: "Document" },
    { id: "parallelism", label: "Full audit" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <div className="mx-auto max-w-5xl px-6 py-16">
        <header className="mb-10 text-center">
          <h1 className="heading-font text-4xl font-light tracking-wide text-white md:text-5xl">
            Automaton Auditor
          </h1>
          <p className="mt-3 text-slate-400">
            Digital Courtroom — Rubric from rubric.json (TRP1 Challenge)
          </p>
          {rubricError && <p className="mt-2 text-sm text-amber-400">{rubricError}</p>}
        </header>

        <div className="mb-6 flex border-b border-slate-700">
          {tabs.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              className={`border-b-2 px-6 py-3 text-sm font-medium transition-colors ${
                activeTab === id
                  ? "border-amber-500 text-amber-200"
                  : "border-transparent text-slate-400 hover:text-slate-300"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {activeTab === "repository" && (
          <section className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-8 shadow-xl backdrop-blur">
            <h2 className="mb-4 heading-font text-xl font-light text-slate-200">Repository only</h2>
            <p className="mb-4 text-sm text-slate-500">Repository URL. Report PDF is taken from repo (reports/final_report.pdf on main) when available.</p>
            <div className="mb-4">
              <label className="mb-1 block text-sm text-slate-400">Repository URL</label>
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/owner/repo"
                className="w-full rounded-lg border border-slate-600 bg-slate-900/50 px-4 py-2 text-slate-100 placeholder-slate-500 focus:border-amber-500/50 focus:outline-none"
              />
            </div>
            <div className="mb-4">
              <label className="mb-2 block text-sm font-medium text-slate-400">Report Type</label>
              <div className="flex gap-3">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="repoReportType"
                    value="self"
                    checked={repoReportType === "self"}
                    onChange={(e) => setRepoReportType(e.target.value as "self")}
                    className="text-amber-600 focus:ring-amber-500"
                  />
                  <span className="text-sm text-slate-300">Self-Audit</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="repoReportType"
                    value="peer"
                    checked={repoReportType === "peer"}
                    onChange={(e) => setRepoReportType(e.target.value as "peer")}
                    className="text-amber-600 focus:ring-amber-500"
                  />
                  <span className="text-sm text-slate-300">Peer-Audit</span>
                </label>
              </div>
            </div>
            {repoError && <p className="mb-2 text-sm text-red-300">{repoError}</p>}
            <button
              type="button"
              onClick={runRepoAudit}
              disabled={repoLoading || !rubricDimensions.length}
              className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-amber-500 disabled:opacity-50"
            >
              {repoLoading ? "Running…" : "Run repo audit"}
            </button>
            {!repoLoading && repoEvidences !== null && (
              <p className="mt-4 text-sm text-emerald-400">Audit completed.</p>
            )}
          </section>
        )}

        {activeTab === "document" && (
          <section className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-8 shadow-xl backdrop-blur">
            <h2 className="mb-4 heading-font text-xl font-light text-slate-200">Document only</h2>
            <p className="mb-4 text-sm text-slate-500">PDF report URL or path (no repo). For full audit with repo, use the Full audit tab.</p>
            <div className="mb-4">
              <label className="mb-1 block text-sm text-slate-400">Document URL or path (PDF)</label>
              <input
                type="text"
                value={docUrl}
                onChange={(e) => setDocUrl(e.target.value)}
                placeholder="https://example.com/report.pdf or /path/to/file.pdf"
                className="w-full rounded-lg border border-slate-600 bg-slate-900/50 px-4 py-2 text-slate-100 placeholder-slate-500 focus:border-amber-500/50 focus:outline-none"
              />
            </div>
            <div className="mb-4">
              <label className="mb-2 block text-sm font-medium text-slate-400">Report Type</label>
              <div className="flex gap-3">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="docReportType"
                    value="self"
                    checked={docReportType === "self"}
                    onChange={(e) => setDocReportType(e.target.value as "self")}
                    className="text-amber-600 focus:ring-amber-500"
                  />
                  <span className="text-sm text-slate-300">Self-Audit</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="docReportType"
                    value="peer"
                    checked={docReportType === "peer"}
                    onChange={(e) => setDocReportType(e.target.value as "peer")}
                    className="text-amber-600 focus:ring-amber-500"
                  />
                  <span className="text-sm text-slate-300">Peer-Audit</span>
                </label>
              </div>
            </div>
            {docError && <p className="mb-2 text-sm text-red-300">{docError}</p>}
            <button
              type="button"
              onClick={runDocAudit}
              disabled={docLoading || !rubricDimensions.length}
              className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-amber-500 disabled:opacity-50"
            >
              {docLoading ? "Running…" : "Run document audit"}
            </button>
            {!docLoading && docEvidences !== null && (
              <p className="mt-4 text-sm text-emerald-400">Audit completed.</p>
            )}
          </section>
        )}

        {activeTab === "parallelism" && (
          <section className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-8 shadow-xl backdrop-blur">
            <h2 className="mb-4 heading-font text-xl font-light text-slate-200">Full audit (repo + report)</h2>
            <p className="mb-6 text-sm text-slate-500">
              Per challenge: provide a GitHub repository URL and optionally a link to the PDF report. The report may be committed to the repo (e.g. reports/final_report.pdf) — use the button below to fill the default.
            </p>
            <div className="grid gap-8 md:grid-cols-2">
              <div className="rounded-xl border border-slate-700/50 bg-slate-900/30 p-5">
                <h3 className="mb-3 text-sm font-medium text-amber-200/90">Repository URL (required)</h3>
                <label className="mb-1 block text-xs text-slate-500">GitHub repository URL</label>
                <input
                  type="text"
                  value={parallelRepoUrl}
                  onChange={(e) => setParallelRepoUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo"
                  className="w-full rounded-lg border border-slate-600 bg-slate-900/50 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-amber-500/50 focus:outline-none"
                />
              </div>
              <div className="rounded-xl border border-slate-700/50 bg-slate-900/30 p-5">
                <h3 className="mb-3 text-sm font-medium text-amber-200/90">PDF report (optional)</h3>
                <label className="mb-1 block text-xs text-slate-500">Link to PDF or leave empty to use report from repo</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={parallelDocUrl}
                    onChange={(e) => setParallelDocUrl(e.target.value)}
                    placeholder="https://raw.githubusercontent.com/.../reports/final_report.pdf"
                    className="flex-1 rounded-lg border border-slate-600 bg-slate-900/50 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-amber-500/50 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={async () => {
                      const repo = parallelRepoUrl.trim();
                      if (!repo) {
                        setParallelError("Enter repository URL first.");
                        return;
                      }
                      setParallelError(null);
                      try {
                        const res = await fetch(`${API_URL}/api/default-pdf-url?repo_url=${encodeURIComponent(repo)}`);
                        const data = await res.json().catch(() => ({}));
                        const url = data.pdf_url || "";
                        if (url) setParallelDocUrl(url);
                        else setParallelError("Could not derive PDF URL for this repo.");
                      } catch {
                        setParallelError("Failed to get default PDF URL.");
                      }
                    }}
                    className="shrink-0 rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-slate-600"
                  >
                    Use report from repo
                  </button>
                </div>
              </div>
            </div>
            <div className="mt-4">
              <label className="mb-2 block text-sm font-medium text-slate-400">Report Type</label>
              <div className="flex gap-3">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="reportType"
                    value="self"
                    checked={reportType === "self"}
                    onChange={(e) => setReportType(e.target.value as "self")}
                    className="text-amber-600 focus:ring-amber-500"
                  />
                  <span className="text-sm text-slate-300">Self-Audit (report_onself_generated/)</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="reportType"
                    value="peer"
                    checked={reportType === "peer"}
                    onChange={(e) => setReportType(e.target.value as "peer")}
                    className="text-amber-600 focus:ring-amber-500"
                  />
                  <span className="text-sm text-slate-300">Peer-Audit (report_onpeer_generated/)</span>
                </label>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Select the report type to organize reports in the correct folder. Self-audit is for auditing your own repository. Peer-received reports should be added manually.
              </p>
            </div>
            {parallelError && <p className="mt-4 text-sm text-red-300">{parallelError}</p>}
            <button
              type="button"
              onClick={runParallelAudit}
              disabled={parallelLoading || !rubricDimensions.length}
              className="mt-6 w-full rounded-lg bg-amber-600 py-3 text-sm font-medium text-slate-950 hover:bg-amber-500 disabled:opacity-50"
            >
              {parallelLoading ? "Running…" : "Run full audit (repo + report)"}
            </button>
            <p className="mt-2 text-xs text-slate-500">If PDF is left empty, the backend uses reports/final_report.pdf from the repo (main branch).</p>
            {!parallelLoading && (parallelRepoEvidences !== null || parallelDocEvidences !== null) && (
              <p className="mt-4 text-sm text-emerald-400">Audit completed.</p>
            )}
          </section>
        )}

        {lastFinalReport && (
          <section className="mt-8 rounded-2xl border border-slate-700/50 bg-slate-800/30 p-8 shadow-xl backdrop-blur">
            <ReportBlock report={lastFinalReport} />
          </section>
        )}
      </div>
    </div>
  );
}
