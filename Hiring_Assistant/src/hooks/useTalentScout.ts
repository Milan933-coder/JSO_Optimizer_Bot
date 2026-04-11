import { useEffect, useRef, useState, type MutableRefObject } from "react";

import {
  runCodingRoundRequest,
  startCodingRoundRequest,
  submitCodingRoundRequest,
} from "@/coding-round/api";
import type { CodingRoundState } from "@/coding-round/types";
import { API_BASE } from "@/lib/api";
import type { ChatMessage } from "@/types/chat";

export type MessageRole = "user" | "assistant";
export type Provider = "openai" | "anthropic" | "gemini";

interface TalentScoutOptions {
  provider: Provider;
  apiKey: string;
  whisperApiKey?: string;
  elevenLabsApiKey?: string;
  elevenLabsVoiceId?: string;
  judge0ApiKey?: string;
  judge0BaseUrl?: string;
}

interface TalentScoutState {
  messages: ChatMessage[];
  isLoading: boolean;
  isClosed: boolean;
  phase: string;
  codingRound: CodingRoundState | null;
  sendMessage: (content: string) => Promise<void>;
  sendVoiceMessage: (audioBlob: Blob) => Promise<void>;
  sendCvFile: (file: File) => Promise<void>;
  startCodingRound: () => Promise<void>;
  runCodingRound: (input: {
    sourceCode: string;
    languageSlug: "python" | "cpp" | "java" | "javascript";
    sampleIndex: number;
  }) => Promise<void>;
  submitCodingRound: (input: {
    sourceCode: string;
    languageSlug: "python" | "cpp" | "java" | "javascript";
  }) => Promise<void>;
  clearChat: () => void;
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

function normalizeAssistantReply(
  rawReply: string,
  questionProgressRef: MutableRefObject<{ current: number; total: number }>,
): string {
  let reply = (rawReply || "").trim();

  const match =
    reply.match(/\*\*Question\s*(\d+)\s*\/\s*(\d+)\s*:\*\*/i) ||
    reply.match(/Question\s*(\d+)\s*\/\s*(\d+)\s*:/i);

  if (match) {
    questionProgressRef.current = {
      current: Number(match[1]),
      total: Number(match[2]),
    };
  }

  reply = reply.replace(/\*\*Question\s*\d+\s*\/\s*\d+\s*:\*\*/gi, "");
  reply = reply.replace(/\*\*Question\s*\d+\s*:\*\*/gi, "");
  reply = reply.replace(/(?:^|\n)Question\s*\d+\s*\/\s*\d+\s*:\s*/gi, "\n");
  reply = reply.replace(/\n\s*---\s*\n/g, "\n\n");

  return reply.trim();
}

export function useTalentScout({
  provider,
  apiKey,
  whisperApiKey = "",
  elevenLabsApiKey = "",
  elevenLabsVoiceId = "",
  judge0ApiKey = "",
  judge0BaseUrl = "",
}: TalentScoutOptions): TalentScoutState {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isClosed, setIsClosed] = useState(false);
  const [phase, setPhase] = useState("INFO_PENDING");
  const [codingRound, setCodingRound] = useState<CodingRoundState | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const questionProgressRef = useRef({ current: 0, total: 0 });

  useEffect(() => {
    if (provider && apiKey && apiKey.trim().length > 10) {
      void initSession();
    }
  }, [provider, apiKey]);

  const applyServerState = (data: {
    phase: string;
    is_closed?: boolean;
    coding_round?: CodingRoundState | null;
  }) => {
    setPhase(data.phase ?? "INFO_PENDING");
    setIsClosed(Boolean(data.is_closed));
    setCodingRound(data.coding_round ?? null);
  };

  const initSession = async () => {
    setMessages([]);
    setIsClosed(false);
    setPhase("INFO_PENDING");
    setCodingRound(null);
    sessionIdRef.current = null;
    questionProgressRef.current = { current: 0, total: 0 };
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/talentscout/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, api_key: apiKey }),
      });

      const data = await safeJson(res);
      if (!res.ok) {
        throw new Error(data?.detail ?? `Server error ${res.status}`);
      }

      sessionIdRef.current = data.session_id;
      applyServerState(data);
      appendMessage("assistant", normalizeAssistantReply(data.reply, questionProgressRef));
    } catch (err: any) {
      appendMessage("assistant", `Warning: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading || isClosed) return;

    if (!sessionIdRef.current) {
      appendMessage("assistant", "Warning: Session not started yet. Please wait or re-enter your API key.");
      return;
    }

    appendMessage("user", content);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/talentscout/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          provider,
          api_key: apiKey,
          message: content,
        }),
      });

      const data = await safeJson(res);
      if (!res.ok) {
        throw new Error(data?.detail ?? `Server error ${res.status}`);
      }

      appendMessage("assistant", normalizeAssistantReply(data.reply, questionProgressRef));
      applyServerState(data);
    } catch (err: any) {
      appendMessage("assistant", `Warning: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const sendVoiceMessage = async (audioBlob: Blob) => {
    if (!audioBlob || audioBlob.size === 0 || isLoading || isClosed) return;

    if (!sessionIdRef.current) {
      appendMessage("assistant", "Warning: Session not started yet. Please wait or re-enter your API key.");
      return;
    }

    if (!elevenLabsApiKey.trim()) {
      appendMessage("assistant", "Warning: ElevenLabs API key is required for voice output.");
      return;
    }

    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append("session_id", sessionIdRef.current);
      formData.append("provider", provider);
      formData.append("api_key", apiKey);
      formData.append("elevenlabs_api_key", elevenLabsApiKey.trim());

      if (whisperApiKey.trim()) {
        formData.append("whisper_api_key", whisperApiKey.trim());
      }
      if (elevenLabsVoiceId.trim()) {
        formData.append("elevenlabs_voice_id", elevenLabsVoiceId.trim());
      }

      formData.append("audio_file", audioBlob, `voice-${Date.now()}.webm`);

      const res = await fetch(`${API_BASE}/api/talentscout/voice-message`, {
        method: "POST",
        body: formData,
      });

      const data = await safeJson(res);
      if (!res.ok) {
        throw new Error(data?.detail ?? `Server error ${res.status}`);
      }

      if (data.transcript) {
        appendMessage("user", data.transcript);
      }
      appendMessage("assistant", normalizeAssistantReply(data.reply, questionProgressRef));
      applyServerState(data);

      if (data.audio_base64 && data.audio_mime_type) {
        const audio = new Audio(`data:${data.audio_mime_type};base64,${data.audio_base64}`);
        void audio.play().catch(() => {
          // Browser autoplay policy may block playback.
        });
      }
    } catch (err: any) {
      appendMessage("assistant", `Warning: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const sendCvFile = async (file: File) => {
    if (!file || isLoading || isClosed) return;

    if (!sessionIdRef.current) {
      appendMessage("assistant", "Warning: Session not started yet. Please wait or re-enter your API key.");
      return;
    }

    appendMessage("user", `Uploaded CV: ${file.name}`);
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append("session_id", sessionIdRef.current);
      formData.append("provider", provider);
      formData.append("api_key", apiKey);
      formData.append("cv_file", file, file.name);

      const res = await fetch(`${API_BASE}/api/talentscout/cv-intake`, {
        method: "POST",
        body: formData,
      });

      const data = await safeJson(res);
      if (!res.ok) {
        throw new Error(data?.detail ?? `Server error ${res.status}`);
      }

      appendMessage("assistant", normalizeAssistantReply(data.reply, questionProgressRef));
      applyServerState(data);
    } catch (err: any) {
      appendMessage("assistant", `Warning: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const runCodingRound = async ({
    sourceCode,
    languageSlug,
    sampleIndex,
  }: {
    sourceCode: string;
    languageSlug: "python" | "cpp" | "java" | "javascript";
    sampleIndex: number;
  }) => {
    if (isLoading || !sessionIdRef.current || !codingRound) return;

    setIsLoading(true);
    try {
      const data = await runCodingRoundRequest({
        sessionId: sessionIdRef.current,
        sourceCode,
        languageSlug,
        sampleIndex,
        judge0ApiKey,
        judge0BaseUrl,
      });

      applyServerState(data);
      if (data.reply) {
        appendMessage("assistant", data.reply);
      }
    } catch (err: any) {
      appendMessage("assistant", `Warning: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const startCodingRound = async () => {
    if (isLoading || !sessionIdRef.current || isClosed) return;

    setIsLoading(true);
    try {
      const data = await startCodingRoundRequest(sessionIdRef.current);
      applyServerState(data);
      if (data.reply) {
        appendMessage("assistant", normalizeAssistantReply(data.reply, questionProgressRef));
      }
    } catch (err: any) {
      appendMessage("assistant", `Warning: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const submitCodingRound = async ({
    sourceCode,
    languageSlug,
  }: {
    sourceCode: string;
    languageSlug: "python" | "cpp" | "java" | "javascript";
  }) => {
    if (isLoading || !sessionIdRef.current || !codingRound) return;

    setIsLoading(true);
    try {
      const data = await submitCodingRoundRequest({
        sessionId: sessionIdRef.current,
        sourceCode,
        languageSlug,
        judge0ApiKey,
        judge0BaseUrl,
      });

      applyServerState(data);
      if (data.reply) {
        appendMessage("assistant", data.reply);
      }
    } catch (err: any) {
      appendMessage("assistant", `Warning: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    if (provider && apiKey) {
      void initSession();
    }
  };

  const appendMessage = (role: MessageRole, content: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        role,
        content,
        timestamp: new Date(),
      },
    ]);
  };

  return {
    messages,
    isLoading,
    isClosed,
    phase,
    codingRound,
    sendMessage,
    sendVoiceMessage,
    sendCvFile,
    startCodingRound,
    runCodingRound,
    submitCodingRound,
    clearChat,
  };
}
