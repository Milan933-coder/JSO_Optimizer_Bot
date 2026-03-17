export type LLMProvider = "openai" | "gemini" | "anthropic";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  image?: string; // base64 data URL
  timestamp: Date;
}

export interface ProviderConfig {
  id: LLMProvider;
  name: string;
  color: string;
  placeholder: string;
}

export const PROVIDERS: ProviderConfig[] = [
  {
    id: "openai",
    name: "OpenAI",
    color: "hsl(160, 60%, 45%)",
    placeholder: "sk-...",
  },
  {
    id: "gemini",
    name: "Gemini",
    color: "hsl(217, 90%, 60%)",
    placeholder: "AIza...",
  },
  {
    id: "anthropic",
    name: "Anthropic",
    color: "hsl(25, 90%, 55%)",
    placeholder: "sk-ant-...",
  },
];
