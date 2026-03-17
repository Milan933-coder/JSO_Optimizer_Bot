import { useState, useCallback } from "react";
import type { ChatMessage, LLMProvider } from "@/types/chat";
import { sendChatMessage } from "@/lib/chatApi";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [provider, setProvider] = useState<LLMProvider>("openai");
  const [apiKeys, setApiKeys] = useState<Record<LLMProvider, string>>({
    openai: "",
    gemini: "",
    anthropic: "",
  });

  const setApiKey = useCallback((p: LLMProvider, key: string) => {
    setApiKeys((prev) => ({ ...prev, [p]: key }));
  }, []);

  const sendMessage = useCallback(
    async (content: string, image?: string) => {
      const key = apiKeys[provider];
      if (!key) throw new Error(`Please set your ${provider} API key first.`);

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        image,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        const history = messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const response = await sendChatMessage({
          message: content,
          provider,
          apiKey: key,
          image,
          history,
        });

        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err: any) {
        const errorMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `⚠️ Error: ${err.message}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [apiKeys, provider, messages]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isLoading,
    provider,
    setProvider,
    apiKeys,
    setApiKey,
    sendMessage,
    clearChat,
  };
}
