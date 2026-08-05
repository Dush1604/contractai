
/**
 * Centralized API client. Every fetch call to the backend goes through
 * here — keeps the base URL, error handling, and response typing in one
 * place instead of scattered across components.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export interface ProjectCreatePayload {
  title: string;
  description: string;
  homeowner_name: string;
  homeowner_email: string;
  homeowner_phone?: string;
  property_location?: string;
  desired_timeline?: string;
  budget_range?: string;
}

export interface ProjectCreateResponse {
  id: string;
  claim_token: string;
  status: string;
  created_at: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function submitProject(
  contractorId: string,
  payload: ProjectCreatePayload
): Promise<ProjectCreateResponse> {
  const res = await fetch(`${API_URL}/projects/${contractorId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Something went wrong." }));
    throw new ApiError(res.status, body.detail ?? "Something went wrong.");
  }

  return res.json();
}

export async function uploadProjectImage(
  projectId: string,
  claimToken: string,
  file: File
): Promise<void> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(
    `${API_URL}/projects/${projectId}/images?claim_token=${encodeURIComponent(claimToken)}`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Image upload failed." }));
    throw new ApiError(res.status, body.detail ?? "Image upload failed.");
  }
}

export interface ProjectStatus {
  id: string;
  title: string;
  description: string;
  status: string;
  homeowner_name: string;
  property_location: string | null;
  desired_timeline: string | null;
  budget_range: string | null;
  created_at: string;
  updated_at: string | null;
}

export async function getProjectStatus(
  projectId: string,
  claimToken: string
): Promise<ProjectStatus> {
  const res = await fetch(
    `${API_URL}/projects/${projectId}/status?claim_token=${encodeURIComponent(claimToken)}`
  );

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unable to load project status." }));
    throw new ApiError(res.status, body.detail ?? "Unable to load project status.");
  }

  return res.json();
}
