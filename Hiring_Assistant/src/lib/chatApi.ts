import type { LLMProvider } from "@/types/chat";

const BACKEND_URL = "http://localhost:8000";

export interface ChatRequest {
  message: string;
  provider: LLMProvider;
  apiKey: string;
  image?: string; // base64
  history?: { role: string; content: string }[];
}

export async function sendChatMessage(req: ChatRequest): Promise<string> {
  const res = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: req.message,
      provider: req.provider,
      api_key: req.apiKey,
      image: req.image || null,
      history: req.history || [],
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Backend error ${res.status}`);
  }

  const data = await res.json();
  return data.response ?? data.message ?? JSON.stringify(data);
}
