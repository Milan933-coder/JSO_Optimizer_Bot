import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";

import {
  runCodingRoundRequest,
  startCodingRoundRequest,
  submitCodingRoundRequest,
} from "@/coding-round/api";
import type { CandidateInfoFormValues } from "@/components/chat/CandidateInfoForm";
import type { CodingRoundState } from "@/coding-round/types";
import { API_BASE } from "@/lib/api";
import type { ChatMessage } from "@/types/chat";

export type MessageRole = "user" | "assistant";
export type Provider = "openai" | "anthropic" | "gemini";

interface TalentScoutOptions {
  provider: Provider;
  apiKey: string;
  autoStartEnabled?: boolean;
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
  hasActiveSession: boolean;
  sessionError: string | null;
  submitCandidateInfo: (values: CandidateInfoFormValues) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  sendVoiceMessage: (audioBlob: Blob) => Promise<void>;
  sendCvFile: (file: File) => Promise<void>;
  stopSession: () => Promise<void>;
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

interface TalentScoutResponsePayload {
  session_id?: string;
  reply?: string;
  phase?: string;
  is_closed?: boolean;
  coding_round?: CodingRoundState | null;
  detail?: string;
  transcript?: string;
  audio_base64?: string;
  audio_mime_type?: string;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}

function isMissingSessionMessage(message: string): boolean {
  return /session not found or expired/i.test(message);
}

async function safeJson(res: Response): Promise<TalentScoutResponsePayload> {
  const text = await res.text();
  if (!text || text.trim() === "") {
    throw new Error(`Server returned empty response (status ${res.status})`);
  }
  try {
    return JSON.parse(text) as TalentScoutResponsePayload;
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

function buildCandidateSummary(values: CandidateInfoFormValues): string {
  return [
    "Candidate details submitted:",
    `Full Name: ${values.name}`,
    `Email Address: ${values.email}`,
    `Phone Number: ${values.phone}`,
    `Years of Experience: ${values.yearsExperience}`,
    `Desired Position(s): ${values.desiredPosition}`,
    `Current Location: ${values.location}`,
    `Tech Stack: ${values.techStack}`,
  ].join("\n");
}

export function useTalentScout({
  provider,
  apiKey,
  autoStartEnabled = false,
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
  const [sessionError, setSessionError] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const questionProgressRef = useRef({ current: 0, total: 0 });

  const applyServerState = (data: {
    phase: string;
    is_closed?: boolean;
    coding_round?: CodingRoundState | null;
  }) => {
    setPhase(data.phase ?? "INFO_PENDING");
    setIsClosed(Boolean(data.is_closed));
    setCodingRound(data.coding_round ?? null);
  };

  const invalidateSession = useCallback((message: string) => {
    sessionIdRef.current = null;
    setIsClosed(false);
    setPhase("INFO_PENDING");
    setCodingRound(null);
    setSessionError(message);
  }, []);

  const recordError = useCallback((error: unknown): string => {
    const message = getErrorMessage(error);
    if (isMissingSessionMessage(message)) {
      invalidateSession(message);
      return message;
    }

    setSessionError(message);
    return message;
  }, [invalidateSession]);

  const initSession = useCallback(async () => {
    setMessages([]);
    setIsClosed(false);
    setPhase("INFO_PENDING");
    setCodingRound(null);
    setSessionError(null);
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

      sessionIdRef.current = data.session_id ?? null;
      setSessionError(null);
      applyServerState({
        phase: data.phase ?? "INFO_PENDING",
        is_closed: data.is_closed,
        coding_round: data.coding_round,
      });
      appendMessage("assistant", normalizeAssistantReply(data.reply ?? "", questionProgressRef));
    } catch (error: unknown) {
      const message = recordError(error);
      appendMessage("assistant", `Warning: ${message}`);
    } finally {
      setIsLoading(false);
    }
  }, [apiKey, provider, recordError]);

  useEffect(() => {
    if (provider && autoStartEnabled) {
      void initSession();
    } else {
      sessionIdRef.current = null;
      setSessionError(null);
      setIsClosed(false);
      setPhase("INFO_PENDING");
      setCodingRound(null);
    }
  }, [provider, autoStartEnabled, initSession]);

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading || isClosed) return;

    if (!sessionIdRef.current) {
      const warning = "Session not started yet. Please wait or check your UI key / backend .env configuration.";
      setSessionError(warning);
      appendMessage("assistant", `Warning: ${warning}`);
      return;
    }

    setSessionError(null);
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

      appendMessage("assistant", normalizeAssistantReply(data.reply ?? "", questionProgressRef));
      applyServerState({
        phase: data.phase ?? "INFO_PENDING",
        is_closed: data.is_closed,
        coding_round: data.coding_round,
      });
    } catch (error: unknown) {
      const message = recordError(error);
      appendMessage("assistant", `Warning: ${message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const submitCandidateInfo = async (values: CandidateInfoFormValues) => {
    if (isLoading || isClosed) return;

    if (!sessionIdRef.current) {
      const warning = "Session not started yet. Please wait or check your UI key / backend .env configuration.";
      setSessionError(warning);
      appendMessage("assistant", `Warning: ${warning}`);
      return;
    }

    setSessionError(null);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/talentscout/candidate-info`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          provider,
          api_key: apiKey,
          name: values.name,
          email: values.email,
          phone: values.phone,
          years_experience: values.yearsExperience,
          desired_position: values.desiredPosition,
          location: values.location,
          tech_stack: values.techStack,
        }),
      });

      const data = await safeJson(res);
      if (!res.ok) {
        throw new Error(data?.detail ?? `Server error ${res.status}`);
      }

      appendMessage("user", buildCandidateSummary(values));
      appendMessage("assistant", normalizeAssistantReply(data.reply ?? "", questionProgressRef));
      applyServerState({
        phase: data.phase ?? "INFO_PENDING",
        is_closed: data.is_closed,
        coding_round: data.coding_round,
      });
      setSessionError(null);
    } catch (error: unknown) {
      const message = recordError(error);
      appendMessage("assistant", `Warning: ${message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const sendVoiceMessage = async (audioBlob: Blob) => {
    if (!audioBlob || audioBlob.size === 0 || isLoading || isClosed) return;

    if (!sessionIdRef.current) {
      const warning = "Session not started yet. Please wait or check your UI key / backend .env configuration.";
      setSessionError(warning);
      appendMessage("assistant", `Warning: ${warning}`);
      return;
    }

    setSessionError(null);
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
      appendMessage("assistant", normalizeAssistantReply(data.reply ?? "", questionProgressRef));
      applyServerState({
        phase: data.phase ?? "INFO_PENDING",
        is_closed: data.is_closed,
        coding_round: data.coding_round,
      });
      setSessionError(null);

      if (data.audio_base64 && data.audio_mime_type) {
        const audio = new Audio(`data:${data.audio_mime_type};base64,${data.audio_base64}`);
        void audio.play().catch(() => {
          // Browser autoplay policy may block playback.
        });
      }
    } catch (error: unknown) {
      const message = recordError(error);
      appendMessage("assistant", `Warning: ${message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const sendCvFile = async (file: File) => {
    if (!file || isLoading || isClosed) return;

    if (!sessionIdRef.current) {
      const warning = "Session not started yet. Please wait or check your UI key / backend .env configuration.";
      setSessionError(warning);
      appendMessage("assistant", `Warning: ${warning}`);
      return;
    }

    setSessionError(null);
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

      appendMessage("assistant", normalizeAssistantReply(data.reply ?? "", questionProgressRef));
      applyServerState({
        phase: data.phase ?? "INFO_PENDING",
        is_closed: data.is_closed,
        coding_round: data.coding_round,
      });
      setSessionError(null);
    } catch (error: unknown) {
      const message = recordError(error);
      appendMessage("assistant", `Warning: ${message}`);
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

    setSessionError(null);
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
    } catch (error: unknown) {
      const message = recordError(error);
      appendMessage("assistant", `Warning: ${message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const startCodingRound = async () => {
    if (isLoading || !sessionIdRef.current || isClosed) return;

    setSessionError(null);
    setIsLoading(true);
    try {
      const data = await startCodingRoundRequest(sessionIdRef.current);
      applyServerState(data);
      if (data.reply) {
        appendMessage("assistant", normalizeAssistantReply(data.reply, questionProgressRef));
      }
    } catch (error: unknown) {
      const message = recordError(error);
      appendMessage("assistant", `Warning: ${message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const stopSession = async () => {
    if (isLoading || !sessionIdRef.current || isClosed) return;

    setSessionError(null);
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/talentscout/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
        }),
      });

      const data = await safeJson(res);
      if (!res.ok) {
        throw new Error(data?.detail ?? `Server error ${res.status}`);
      }

      sessionIdRef.current = null;
      setCodingRound(null);
      setIsClosed(true);
      setPhase(data.phase ?? "CLOSED");
      if (data.reply) {
        appendMessage("assistant", normalizeAssistantReply(data.reply, questionProgressRef));
      }
    } catch (error: unknown) {
      const message = recordError(error);
      appendMessage("assistant", `Warning: ${message}`);
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

    setSessionError(null);
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
    } catch (error: unknown) {
      const message = recordError(error);
      appendMessage("assistant", `Warning: ${message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    if (provider && autoStartEnabled) {
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
    hasActiveSession: Boolean(sessionIdRef.current),
    sessionError,
    submitCandidateInfo,
    sendMessage,
    sendVoiceMessage,
    sendCvFile,
    stopSession,
    startCodingRound,
    runCodingRound,
    submitCodingRound,
    clearChat,
  };
}
