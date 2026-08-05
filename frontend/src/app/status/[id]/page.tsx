"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { getProjectStatus, ApiError, type ProjectStatus } from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  pending_analysis: "Analyzing your project",
  awaiting_info: "Waiting on a few more details",
  scoped: "Scope of work ready",
  estimated: "Estimate ready",
  approved: "Approved — contractor will be in touch",
  archived: "Archived",
};

export default function StatusPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const claimToken = searchParams.get("claim_token");

  const [project, setProject] = useState<ProjectStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!claimToken) {
      setError("This link is missing a required access token.");
      setLoading(false);
      return;
    }

    getProjectStatus(params.id, claimToken)
      .then(setProject)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 410) {
          setError("This link has expired. Please contact the contractor for an update.");
        } else if (err instanceof ApiError && err.status === 404) {
          setError("We couldn't find a project matching this link.");
        } else {
          setError("Something went wrong loading your project status.");
        }
      })
      .finally(() => setLoading(false));
  }, [params.id, claimToken]);

  if (loading) {
    return (
      <main className="mx-auto max-w-xl px-6 py-16">
        <p className="text-gray-600">Loading...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-xl px-6 py-16">
        <h1 className="text-xl font-semibold text-red-700">Unable to load status</h1>
        <p className="mt-2 text-gray-700">{error}</p>
      </main>
    );
  }

  if (!project) return null;

  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      <h1 className="text-2xl font-semibold">{project.title}</h1>
      <p className="mt-2 inline-block rounded bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700">
        {STATUS_LABELS[project.status] ?? project.status}
      </p>

      <div className="mt-6 space-y-3 text-sm text-gray-700">
        <p>{project.description}</p>
        {project.property_location && (
          <p>
            <span className="font-medium">Location:</span> {project.property_location}
          </p>
        )}
        {project.desired_timeline && (
          <p>
            <span className="font-medium">Timeline:</span> {project.desired_timeline}
          </p>
        )}
        {project.budget_range && (
          <p>
            <span className="font-medium">Budget:</span> {project.budget_range}
          </p>
        )}
        <p className="text-gray-500">
          Submitted {new Date(project.created_at).toLocaleDateString()}
        </p>
      </div>
    </main>
  );
}
