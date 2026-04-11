import { API_BASE } from "@/lib/api";
import type { CodingRoundActionResponse } from "@/coding-round/types";
import type { CodingRoundState } from "@/coding-round/types";

interface CodingRoundRequest {
  sessionId: string;
  sourceCode: string;
  languageSlug: "python" | "cpp" | "java" | "javascript";
  sampleIndex?: number;
  judge0ApiKey?: string;
  judge0BaseUrl?: string;
}

interface CodingRoundStartResponse {
  session_id: string;
  reply: string;
  phase: string;
  is_closed: boolean;
  coding_round?: CodingRoundState | null;
}

async function safeJson(res: Response): Promise<any> {
  const text = await res.text();
  if (!text || text.trim() === "") {
    throw new Error(`Server returned empty response (status ${res.status})`);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Server error (${res.status}): ${text.slice(0, 200)}`);
  }
}

async function sendRoundRequest(
  path: "run" | "submit",
  req: CodingRoundRequest,
): Promise<CodingRoundActionResponse> {
  const res = await fetch(`${API_BASE}/api/talentscout/coding-round/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: req.sessionId,
      source_code: req.sourceCode,
      language_slug: req.languageSlug,
      sample_index: req.sampleIndex ?? 0,
      judge0_api_key: req.judge0ApiKey?.trim() || null,
      judge0_base_url: req.judge0BaseUrl?.trim() || null,
    }),
  });

  const data = await safeJson(res);
  if (!res.ok) {
    throw new Error(data?.detail ?? `Server error ${res.status}`);
  }

  return data as CodingRoundActionResponse;
}

export function runCodingRoundRequest(req: CodingRoundRequest) {
  return sendRoundRequest("run", req);
}

export function submitCodingRoundRequest(req: CodingRoundRequest) {
  return sendRoundRequest("submit", req);
}

export async function startCodingRoundRequest(sessionId: string): Promise<CodingRoundStartResponse> {
  const res = await fetch(`${API_BASE}/api/talentscout/coding-round/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
    }),
  });

  const data = await safeJson(res);
  if (!res.ok) {
    throw new Error(data?.detail ?? `Server error ${res.status}`);
  }

  return data as CodingRoundStartResponse;
}
