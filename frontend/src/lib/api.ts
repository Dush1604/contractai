
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

export interface Contractor {
  id: string;
  email: string;
  role: string;
}

export interface ProjectListItem {
  id: string;
  title: string;
  status: string;
  homeowner_name: string;
  homeowner_email: string;
  created_at: string;
}

export async function loginContractor(email: string, password: string): Promise<Contractor> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include", // send/receive the httpOnly cookie
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Login failed." }));
    throw new ApiError(res.status, body.detail ?? "Login failed.");
  }

  return res.json();
}

export async function logoutContractor(): Promise<void> {
  await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export async function getMyProjects(): Promise<ProjectListItem[]> {
  const res = await fetch(`${API_URL}/contractor/projects/`, {
    credentials: "include", // send the httpOnly cookie along with the request
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unable to load projects." }));
    throw new ApiError(res.status, body.detail ?? "Unable to load projects.");
  }

  return res.json();
}

export async function registerContractor(email: string, password: string): Promise<Contractor> {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Registration failed." }));
    throw new ApiError(res.status, body.detail ?? "Registration failed.");
  }

  return res.json();
}

export interface ProjectAnalysis {
  id: string;
  category: string | null;
  complexity: string | null;
  missing_info: string[];
  follow_up_questions: string[];
  scope_of_work: string[];
  model_version: string | null;
}

export interface ProjectEstimate {
  id: string;
  scope_of_work: string[];
  estimate_min: number | null;
  estimate_max: number | null;
  confidence: string | null;
  assumptions: string[];
  risk_factors: string[];
  approved_by_contractor: boolean;
}

export async function analyzeProject(projectId: string): Promise<ProjectAnalysis> {
  const res = await fetch(`${API_URL}/contractor/projects/${projectId}/analyze`, {
    method: "POST",
    credentials: "include",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Analysis failed." }));
    throw new ApiError(res.status, body.detail ?? "Analysis failed.");
  }

  return res.json();
}

export async function generateEstimate(projectId: string): Promise<ProjectEstimate> {
  const res = await fetch(`${API_URL}/contractor/projects/${projectId}/estimate`, {
    method: "POST",
    credentials: "include",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Estimate generation failed." }));
    throw new ApiError(res.status, body.detail ?? "Estimate generation failed.");
  }

  return res.json();
}

export interface ProjectImageWithPrediction {
  id: string;
  original_filename: string;
  predicted_category: string | null;
  predicted_confidence: number | null;
  created_at: string;
}

export async function getProjectImages(projectId: string): Promise<ProjectImageWithPrediction[]> {
  const res = await fetch(`${API_URL}/contractor/projects/${projectId}/images`, {
    credentials: "include",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unable to load images." }));
    throw new ApiError(res.status, body.detail ?? "Unable to load images.");
  }

  return res.json();
}

export async function downloadEstimatePdf(projectId: string, projectTitle: string): Promise<void> {
  const res = await fetch(`${API_URL}/contractor/projects/${projectId}/export-pdf`, {
    credentials: "include",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "PDF export failed." }));
    throw new ApiError(res.status, body.detail ?? "PDF export failed.");
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${projectTitle.replace(/\s+/g, "_")}_estimate.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}
