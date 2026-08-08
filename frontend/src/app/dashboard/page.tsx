"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getMyProjects,
  logoutContractor,
  analyzeProject,
  generateEstimate,
  ApiError,
  type ProjectListItem,
  type ProjectAnalysis,
  type ProjectEstimate,
} from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  pending_analysis: "Analyzing",
  awaiting_info: "Awaiting info",
  scoped: "Scoped",
  estimated: "Estimated",
  approved: "Approved",
  archived: "Archived",
};

function ProjectRow({ project }: { project: ProjectListItem }) {
  const [expanded, setExpanded] = useState(false);
  const [analysis, setAnalysis] = useState<ProjectAnalysis | null>(null);
  const [estimate, setEstimate] = useState<ProjectEstimate | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [loadingEstimate, setLoadingEstimate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    setError(null);
    setLoadingAnalysis(true);
    try {
      const result = await analyzeProject(project.id);
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Analysis failed.");
    } finally {
      setLoadingAnalysis(false);
    }
  }

  async function handleEstimate() {
    setError(null);
    setLoadingEstimate(true);
    try {
      const result = await generateEstimate(project.id);
      setEstimate(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Estimate generation failed.");
    } finally {
      setLoadingEstimate(false);
    }
  }

  return (
    <>
      <tr
        className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="py-3 pr-4 font-medium">{project.title}</td>
        <td className="py-3 pr-4 text-gray-700">
          {project.homeowner_name}
          <br />
          <span className="text-gray-500">{project.homeowner_email}</span>
        </td>
        <td className="py-3 pr-4">
          <span className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700">
            {STATUS_LABELS[project.status] ?? project.status}
          </span>
        </td>
        <td className="py-3 text-gray-500">
          {new Date(project.created_at).toLocaleDateString()}
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-gray-100 bg-gray-50">
          <td colSpan={4} className="px-4 py-4">
            <div className="flex gap-3">
              <button
                onClick={handleAnalyze}
                disabled={loadingAnalysis}
                className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loadingAnalysis ? "Analyzing..." : "Run AI Analysis"}
              </button>
              <button
                onClick={handleEstimate}
                disabled={loadingEstimate || !analysis}
                className="rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {loadingEstimate ? "Generating..." : "Generate Estimate"}
              </button>
              {!analysis && (
                <span className="self-center text-xs text-gray-500">
                  Run analysis first to enable estimate generation
                </span>
              )}
            </div>

            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

            {analysis && (
              <div className="mt-4 space-y-2 text-sm">
                <p>
                  <span className="font-medium">Category:</span> {analysis.category}{" "}
                  <span className="font-medium">· Complexity:</span> {analysis.complexity}
                </p>
                <div>
                  <p className="font-medium">Follow-up questions:</p>
                  <ul className="ml-4 list-disc text-gray-700">
                    {analysis.follow_up_questions.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="font-medium">Scope of work:</p>
                  <ul className="ml-4 list-disc text-gray-700">
                    {analysis.scope_of_work.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {estimate && (
              <div className="mt-4 rounded border border-green-200 bg-green-50 p-3 text-sm">
                <p className="text-lg font-semibold text-green-800">
                  ${estimate.estimate_min?.toLocaleString()} – $
                  {estimate.estimate_max?.toLocaleString()}
                </p>
                <p className="text-xs text-green-700">Confidence: {estimate.confidence}</p>
                <div className="mt-2">
                  <p className="font-medium">Assumptions:</p>
                  <ul className="ml-4 list-disc text-gray-700">
                    {estimate.assumptions.map((a, i) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                </div>
                <div className="mt-2">
                  <p className="font-medium">Risk factors:</p>
                  <ul className="ml-4 list-disc text-gray-700">
                    {estimate.risk_factors.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMyProjects()
      .then(setProjects)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          router.push("/login");
        } else {
          setError("Unable to load your projects.");
        }
      });
  }, [router]);

  async function handleLogout() {
    await logoutContractor();
    router.push("/login");
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your Projects</h1>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-600 underline hover:text-gray-900"
        >
          Log out
        </button>
      </div>

      {error && <p className="mt-6 text-sm text-red-600">{error}</p>}
      {projects === null && !error && <p className="mt-6 text-gray-600">Loading...</p>}
      {projects !== null && projects.length === 0 && (
        <p className="mt-6 text-gray-600">No project requests yet.</p>
      )}

      {projects !== null && projects.length > 0 && (
        <table className="mt-6 w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-gray-500">
              <th className="py-2 pr-4">Title</th>
              <th className="py-2 pr-4">Homeowner</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2">Submitted</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <ProjectRow key={p.id} project={p} />
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
