/**
 * Raptorflow Lead Engine - API Client
 * Thin wrapper around fetch for backend API calls
 */

const CANDIDATE_API_BASES = Array.from(
  new Set(
    [
      process.env.NEXT_PUBLIC_API_BASE_URL,
      'http://127.0.0.1:8010',
      'http://127.0.0.1:8001',
      'http://127.0.0.1:8000',
      'http://localhost:8010',
      'http://localhost:8001',
      'http://localhost:8000',
    ].filter(Boolean)
  )
) as string[];

let apiBase: string = CANDIDATE_API_BASES[0] ?? 'http://127.0.0.1:8001';

export function getApiBaseUrl(): string {
  return apiBase;
}

async function fetchApi(path: string, init?: RequestInit): Promise<Response> {
  const bases = [apiBase, ...CANDIDATE_API_BASES.filter((b) => b !== apiBase)];

  let lastError: unknown = null;
  for (const base of bases) {
    try {
      const response = await fetch(`${base}${path}`, init);
      // Any HTTP response means the server is reachable; cache the base.
      apiBase = base;
      return response;
    } catch (err) {
      lastError = err;
      continue;
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Unable to reach backend API');
}

// Error handling
export class APIError extends Error {
  constructor(
    public status: number,
    public message: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.text();
    throw new APIError(response.status, error || response.statusText);
  }
  return response.json() as Promise<T>;
}

// ============ ICP APIs ============

export interface ICP {
  id: number;
  name: string;
  description?: string;
  size_buckets: string[];
  industries: string[];
  locations: string[];
  hiring_keywords: string[];
  pain_keywords: string[];
  channel_preferences: string[];
  created_at: string;
  updated_at: string;
}

export async function listICPs(): Promise<ICP[]> {
  const response = await fetchApi(`/api/icp/`);
  return handleResponse<ICP[]>(response);
}

export async function getICP(id: number): Promise<ICP> {
  const response = await fetchApi(`/api/icp/${id}`);
  return handleResponse<ICP>(response);
}

export async function createICP(icp: Omit<ICP, 'id' | 'created_at' | 'updated_at'>): Promise<ICP> {
  const response = await fetchApi(`/api/icp/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(icp),
  });
  return handleResponse<ICP>(response);
}

export async function updateICP(id: number, icp: Partial<ICP>): Promise<ICP> {
  const response = await fetchApi(`/api/icp/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(icp),
  });
  return handleResponse<ICP>(response);
}

export async function deleteICP(id: number): Promise<void> {
  const response = await fetchApi(`/api/icp/${id}`, {
    method: 'DELETE',
  });
  await handleResponse<unknown>(response);
}

// ============ Lead APIs ============

export interface Lead {
  id: number;
  company_id: number;
  contact_id?: number;
  score_icp_fit: number;
  score_marketing_pain: number;
  score_data_quality: number;
  total_score: number;
  score_bucket: string;
  role_type?: string;
  pain_tags: string[];
  situation?: string;
  problem?: string;
  implication?: string;
  need_payoff?: string;
  economic_buyer_guess?: string;
  key_pain?: string;
  chaos_flags: string[];
  silver_bullet_phrases: string[];
  context_dossier?: string;
  challenger_insight?: string;
  reframe_suggestion?: string;
  status: string;
  created_at: string;
  updated_at: string;
  company?: {
    id: number;
    name: string;
    website?: string;
    sector?: string;
  };
  contact?: {
    id: number;
    name?: string;
    role?: string;
    email?: string;
    phone_numbers: string[];
  };
  signals: {
    id: number;
    source_type: string;
    source_url?: string;
    created_at: string;
  }[];
  activities: {
    id: number;
    type: string;
    content?: string;
    timestamp: string;
  }[];
}

export async function listLeads(params: {
  score_min?: number;
  score_max?: number;
  status?: string;
  score_bucket?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<Lead[]> {
  const query = new URLSearchParams();
  if (params.score_min !== undefined) query.append('score_min', params.score_min.toString());
  if (params.score_max !== undefined) query.append('score_max', params.score_max.toString());
  if (params.status) query.append('status', params.status);
  if (params.score_bucket) query.append('score_bucket', params.score_bucket);
  if (params.limit) query.append('limit', params.limit.toString());
  if (params.offset) query.append('offset', params.offset.toString());

  const response = await fetchApi(`/api/leads/?${query}`);
  return handleResponse<Lead[]>(response);
}

export async function getLead(id: number): Promise<Lead> {
  const response = await fetchApi(`/api/leads/${id}`);
  return handleResponse<Lead>(response);
}

export async function updateLeadStatus(id: number, status: string): Promise<{ status: string }> {
  const response = await fetchApi(`/api/leads/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  return handleResponse<{ status: string }>(response);
}

export async function updateLeadNotes(id: number, notes: string): Promise<{ status: string }> {
  const response = await fetchApi(`/api/leads/${id}/notes`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes }),
  });
  return handleResponse<{ status: string }>(response);
}

export async function deleteLead(id: number): Promise<void> {
  const response = await fetchApi(`/api/leads/${id}`, {
    method: 'DELETE',
  });
  await handleResponse<unknown>(response);
}

export async function getBucketCounts(): Promise<{
  red_hot: number;
  warm: number;
  nurture: number;
  parked: number;
}> {
  const response = await fetchApi(`/api/leads/score-distribution/bucket-counts`);
  return handleResponse<{ red_hot: number; warm: number; nurture: number; parked: number }>(response);
}

// ============ Advanced Lead Search APIs ============

export interface LeadFilter {
  score_min?: number;
  score_max?: number;
  status?: string;
  score_bucket?: string;
  decision_making_level?: string;
  company_size_estimate?: string;
  budget_authority?: string;
  target_priority?: string;
  urgency_level?: string;
  role_type?: string;
  company_name_contains?: string;
  pain_tags_contains?: string;
  economic_buyer_guess?: string;
  created_after?: string;
  created_before?: string;
  executive_level_min?: number;
  budget_potential_min?: number;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_desc?: boolean;
}

export async function advancedLeadSearch(filters: LeadFilter): Promise<Lead[]> {
  const response = await fetchApi(`/api/leads/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters),
  });
  return handleResponse<Lead[]>(response);
}

// ============ Classification APIs ============

export interface ClassifyPayload {
  signal_text: string;
  source_type?: string;
  source_url?: string;
  company_name?: string;
  company_website?: string;
}

export interface ClassificationResult {
  icp_match: boolean;
  total_score: number;
  score_bucket: string;
  company_id?: number;
  lead_id?: number;
  classification: Record<string, unknown>;
}

export async function classifySignal(payload: ClassifyPayload): Promise<ClassificationResult> {
  const response = await fetchApi(`/api/classify/signal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<ClassificationResult>(response);
}

// ============ Ingest APIs ============

export interface OCRResult {
  extracted_text: string;
  detected_emails: string[];
  detected_phones: string[];
  detected_names: string[];
  detected_company?: string;
}

export async function ocrFile(file: File): Promise<OCRResult> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetchApi(`/api/ingest/ocr`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<OCRResult>(response);
}

export async function ocrAndClassify(file: File, companyName?: string): Promise<ClassificationResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (companyName) {
    formData.append('company_name', companyName);
  }

  const response = await fetchApi(`/api/ingest/ocr-and-classify`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<ClassificationResult>(response);
}

export async function ingestCSV(file: File): Promise<{
  total_processed: number;
  total_created: number;
  results: Array<Record<string, unknown>>;
  message: string;
}> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetchApi(`/api/ingest/csv`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<{
    total_processed: number;
    total_created: number;
    results: Array<Record<string, unknown>>;
    message: string;
  }>(response);
}

// ============ Mission Control APIs ============

export async function launchMission(prompt: string, icp_profile_id?: number): Promise<{ status: string }> {
  const response = await fetchApi(`/api/mission/launch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, icp_profile_id }),
  });
  return handleResponse<{ status: string }>(response);
}

// ============ Health Check ============

export interface SystemHealth {
  api: string;
  database: string;
  ollama: {
    status: string;
    models: {
      '1b': string | null;
      '4b': string | null;
    };
  };
  scraping?: {
    browsers_installed: boolean;
  };
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetchApi(`/health`, {
      method: 'GET',
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function getSystemHealth(): Promise<SystemHealth> {
  const response = await fetchApi(`/health`);
  return handleResponse<SystemHealth>(response);
}

export function getLeadsCsvExportUrl(): string {
  return `${apiBase}/api/leads/export/csv`;
}

export function getLeadPdfExportUrl(leadId: number): string {
  return `${apiBase}/api/leads/${leadId}/export/pdf`;
}
