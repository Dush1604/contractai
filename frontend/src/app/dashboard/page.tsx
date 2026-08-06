"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMyProjects, logoutContractor, ApiError, type ProjectListItem } from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  pending_analysis: "Analyzing",
  awaiting_info: "Awaiting info",
  scoped: "Scoped",
  estimated: "Estimated",
  approved: "Approved",
  archived: "Archived",
};

export default function DashboardPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMyProjects()
      .then(setProjects)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          // Not logged in (or session expired) — bounce to login rather
          // than showing a raw error on a page that requires auth.
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
              <tr key={p.id} className="border-b border-gray-100">
                <td className="py-3 pr-4 font-medium">{p.title}</td>
                <td className="py-3 pr-4 text-gray-700">
                  {p.homeowner_name}
                  <br />
                  <span className="text-gray-500">{p.homeowner_email}</span>
                </td>
                <td className="py-3 pr-4">
                  <span className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700">
                    {STATUS_LABELS[p.status] ?? p.status}
                  </span>
                </td>
                <td className="py-3 text-gray-500">
                  {new Date(p.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
