// src/hooks/useTalentScout.ts

import { useEffect, useRef, useState, type MutableRefObject } from "react";
import { API_BASE } from "@/lib/api";

export type MessageRole = "user" | "assistant";
export type Provider = "openai" | "anthropic" | "gemini";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
}

interface TalentScoutOptions {
  provider: Provider;
  apiKey: string;
  whisperApiKey?: string;
  elevenLabsApiKey?: string;
  elevenLabsVoiceId?: string;
}

interface TalentScoutState {
  messages: Message[];
  isLoading: boolean;
  isClosed: boolean;
  phase: string;
  sendMessage: (content: string) => Promise<void>;
  sendVoiceMessage: (audioBlob: Blob) => Promise<void>;
  sendCvFile: (file: File) => Promise<void>;
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
  questionProgressRef: MutableRefObject<{ current: number; total: number }>
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
}: TalentScoutOptions): TalentScoutState {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isClosed, setIsClosed] = useState(false);
  const [phase, setPhase] = useState("INFO_PENDING");
  const sessionIdRef = useRef<string | null>(null);
  const questionProgressRef = useRef({ current: 0, total: 0 });

  useEffect(() => {
    if (provider && apiKey && apiKey.trim().length > 10) {
      void initSession();
    }
  }, [provider, apiKey]);

  const initSession = async () => {
    setMessages([]);
    setIsClosed(false);
    setPhase("INFO_PENDING");
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
      setPhase(data.phase);
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
      setPhase(data.phase);
      if (data.is_closed) setIsClosed(true);
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
      setPhase(data.phase);
      if (data.is_closed) setIsClosed(true);

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
      setPhase(data.phase);
      if (data.is_closed) setIsClosed(true);
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
      { id: `${Date.now()}-${Math.random()}`, role, content },
    ]);
  };

  return {
    messages,
    isLoading,
    isClosed,
    phase,
    sendMessage,
    sendVoiceMessage,
    sendCvFile,
    clearChat,
  };
}
