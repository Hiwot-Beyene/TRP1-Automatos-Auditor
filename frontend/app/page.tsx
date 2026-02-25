"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const DEFAULT_RUBRIC_JSON = JSON.stringify(
  [
    { id: "git_forensic_analysis", name: "Git Forensic Analysis", target_artifact: "github_repo" },
    { id: "graph_orchestration", name: "Graph Orchestration", target_artifact: "github_repo" },
    { id: "theoretical_depth", name: "Theoretical Depth", target_artifact: "pdf_report" },
    { id: "swarm_visual", name: "Swarm Visual", target_artifact: "pdf_images" },
  ],
  null,
  2
);

type EvidenceItem = { goal: string; found: boolean; content?: string; location: string; rationale: string; confidence: number };
type Evidences = Record<string, EvidenceItem[]>;

export default function Home() {
  const [mode, setMode] = useState<"repo" | "doc">("repo");
  const [url, setUrl] = useState("");
  const [rubricJson, setRubricJson] = useState(DEFAULT_RUBRIC_JSON);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [evidences, setEvidences] = useState<Evidences | null>(null);

  const loadDefaultRubric = () => setRubricJson(DEFAULT_RUBRIC_JSON);

  const runAudit = async () => {
    const trimmedUrl = url.trim();
    if (!trimmedUrl) {
      setError("Enter a Repo URL or Doc URL.");
      return;
    }
    let rubricDimensions: unknown[];
    try {
      const parsed = JSON.parse(rubricJson);
      rubricDimensions = Array.isArray(parsed) ? parsed : parsed?.dimensions ?? [];
    } catch {
      setError("Rubric must be valid JSON (array of dimensions or object with 'dimensions' array).");
      return;
    }
    if (!Array.isArray(rubricDimensions) || rubricDimensions.length === 0) {
      setError("Rubric must contain at least one dimension.");
      return;
    }
    setError(null);
    setEvidences(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_url: mode === "repo" ? trimmedUrl : "",
          pdf_path: mode === "doc" ? trimmedUrl : "",
          rubric_dimensions: rubricDimensions,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText || "Request failed");
      setEvidences(data.evidences ?? {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <div className="mx-auto max-w-4xl px-6 py-16">
        <header className="mb-16 text-center">
          <h1 className="heading-font text-4xl font-light tracking-wide text-white md:text-5xl">
            Automaton Auditor
          </h1>
          <p className="mt-3 text-slate-400">
            Digital Courtroom — forensic evidence from repo or document
          </p>
        </header>

        <section className="rounded-2xl border border-slate-700/50 bg-slate-800/30 p-8 shadow-xl backdrop-blur">
          <h2 className="mb-6 heading-font text-xl font-light text-slate-200">Run audit</h2>
          <div className="space-y-6">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">Audit type</label>
              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => setMode("repo")}
                  className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                    mode === "repo"
                      ? "border-amber-500/60 bg-amber-500/20 text-amber-200"
                      : "border-slate-600 bg-slate-800/50 text-slate-400 hover:border-slate-500 hover:text-slate-300"
                  }`}
                >
                  Repo URL
                </button>
                <button
                  type="button"
                  onClick={() => setMode("doc")}
                  className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                    mode === "doc"
                      ? "border-amber-500/60 bg-amber-500/20 text-amber-200"
                      : "border-slate-600 bg-slate-800/50 text-slate-400 hover:border-slate-500 hover:text-slate-300"
                  }`}
                >
                  Doc URL
                </button>
              </div>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-400">
                {mode === "repo" ? "Repository URL" : "Document URL (PDF path or URL)"}
              </label>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder={mode === "repo" ? "https://github.com/owner/repo" : "https://example.com/report.pdf or /path/to/file.pdf"}
                className="w-full rounded-lg border border-slate-600 bg-slate-900/50 px-4 py-3 text-slate-100 placeholder-slate-500 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30"
              />
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-sm font-medium text-slate-400">Rubric (JSON)</label>
                <button
                  type="button"
                  onClick={loadDefaultRubric}
                  className="text-xs text-amber-400 hover:text-amber-300"
                >
                  Load default
                </button>
              </div>
              <textarea
                value={rubricJson}
                onChange={(e) => setRubricJson(e.target.value)}
                rows={10}
                className="w-full rounded-lg border border-slate-600 bg-slate-900/50 px-4 py-3 font-mono text-sm text-slate-300 placeholder-slate-500 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30"
                placeholder='[{"id":"...","name":"...","target_artifact":"github_repo|pdf_report|pdf_images"}]'
              />
            </div>
            {error && (
              <p className="rounded-lg bg-red-900/30 px-4 py-2 text-sm text-red-200">{error}</p>
            )}
            <button
              type="button"
              onClick={runAudit}
              disabled={loading}
              className="w-full rounded-lg bg-amber-600 px-4 py-3 font-medium text-slate-950 transition-colors hover:bg-amber-500 disabled:opacity-50"
            >
              {loading ? "Running…" : "Run audit"}
            </button>
          </div>
        </section>

        {evidences && Object.keys(evidences).length > 0 && (
          <section className="mt-12">
            <h2 className="mb-6 heading-font text-xl font-light text-slate-200">Evidence by dimension</h2>
            <div className="space-y-6">
              {Object.entries(evidences).map(([dimId, items]) => (
                <div
                  key={dimId}
                  className="rounded-2xl border border-slate-700/50 bg-slate-800/20 p-6 shadow-lg"
                >
                  <h3 className="mb-4 font-medium capitalize text-amber-200/90">
                    {dimId.replace(/_/g, " ")}
                  </h3>
                  <ul className="space-y-4">
                    {items.map((ev, i) => (
                      <li
                        key={i}
                        className="rounded-lg border border-slate-700/40 bg-slate-900/40 p-4"
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-block h-2 w-2 rounded-full ${
                              ev.found ? "bg-emerald-500" : "bg-slate-500"
                            }`}
                          />
                          <span className="text-sm font-medium text-slate-300">
                            {ev.found ? "Found" : "Not found"}
                          </span>
                          <span className="text-slate-500">· {ev.goal}</span>
                        </div>
                        {ev.rationale && (
                          <p className="mt-2 text-sm text-slate-400">{ev.rationale}</p>
                        )}
                        {ev.content && (
                          <p className="mt-1 font-mono text-xs text-slate-500">{ev.content}</p>
                        )}
                        <p className="mt-1 text-xs text-slate-500">Location: {ev.location}</p>
                        <p className="mt-0.5 text-xs text-slate-600">Confidence: {ev.confidence}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        )}

        {evidences && Object.keys(evidences).length === 0 && !loading && (
          <p className="mt-12 text-center text-slate-500">No evidence returned.</p>
        )}
      </div>
    </div>
  );
}
