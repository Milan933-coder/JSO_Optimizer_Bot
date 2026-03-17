// src/hooks/useTalentScout.ts
// Sends provider + api_key with every request (user sets them in sidebar)

import { useState, useEffect, useRef } from "react";
import { API_BASE } from "@/lib/api";

export type MessageRole = "user" | "assistant";
export type Provider    = "openai" | "anthropic" | "gemini";

export interface Message {
  id:      string;
  role:    MessageRole;
  content: string;
}

interface TalentScoutOptions {
  provider: Provider;
  apiKey:   string;
}

interface TalentScoutState {
  messages:    Message[];
  isLoading:   boolean;
  isClosed:    boolean;
  phase:       string;
  sendMessage: (content: string) => Promise<void>;
  clearChat:   () => void;
}

export function useTalentScout({ provider, apiKey }: TalentScoutOptions): TalentScoutState {
  const [messages,  setMessages]  = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isClosed,  setIsClosed]  = useState(false);
  const [phase,     setPhase]     = useState("INFO_PENDING");
  const sessionIdRef = useRef<string | null>(null);

  // Re-init when provider or key changes
  useEffect(() => {
    if (provider && apiKey) initSession();
  }, [provider, apiKey]);

  // ── Start session ────────────────────────────────────────────────────────
  const initSession = async () => {
    setMessages([]);
    setIsClosed(false);
    setPhase("INFO_PENDING");
    sessionIdRef.current = null;
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/talentscout/start`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, api_key: apiKey }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Failed to start session");
      }

      const data = await res.json();
      sessionIdRef.current = data.session_id;
      setPhase(data.phase);
      appendMessage("assistant", data.reply);
    } catch (err: any) {
      appendMessage("assistant", `⚠️ ${err.message ?? "Could not connect to TalentScout."}`);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Send message ─────────────────────────────────────────────────────────
  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading || isClosed) return;

    appendMessage("user", content);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/talentscout/message`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          provider,
          api_key: apiKey,
          message: content,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? `Server error ${res.status}`);
      }

      const data = await res.json();
      appendMessage("assistant", data.reply);
      setPhase(data.phase);
      if (data.is_closed) setIsClosed(true);

    } catch (err: any) {
      appendMessage("assistant", `⚠️ ${err.message ?? "Something went wrong."}`);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Clear / restart ──────────────────────────────────────────────────────
  const clearChat = () => {
    if (provider && apiKey) initSession();
  };

  // ── Helper ───────────────────────────────────────────────────────────────
  const appendMessage = (role: MessageRole, content: string) => {
    setMessages(prev => [
      ...prev,
      { id: `${Date.now()}-${Math.random()}`, role, content },
    ]);
  };

  return { messages, isLoading, isClosed, phase, sendMessage, clearChat };
}
