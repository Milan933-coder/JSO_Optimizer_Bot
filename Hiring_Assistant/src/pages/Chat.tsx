// src/pages/Chat.tsx
// Provider selector + API key input restored in sidebar
// Passes provider + apiKey into useTalentScout

import { useState }           from "react";
import { useTalentScout, Provider } from "@/hooks/useTalentScout";
import { ChatMessages }        from "@/components/chat/ChatMessages";
import { ChatInput }           from "@/components/chat/ChatInput";
import { toast }               from "@/hooks/use-toast";
import { Button }              from "@/components/ui/button";
import { Input }               from "@/components/ui/input";
import { MessageSquarePlus }   from "lucide-react";

// ── Provider config ──────────────────────────────────────────────────────────
const PROVIDERS: { id: Provider; name: string; color: string; placeholder: string }[] = [
  { id: "openai",    name: "OpenAI GPT-4o",      color: "#10a37f", placeholder: "sk-..."          },
  { id: "anthropic", name: "Anthropic Claude",    color: "#d97706", placeholder: "sk-ant-..."      },
  { id: "gemini",    name: "Google Gemini",       color: "#4285f4", placeholder: "AIza..."         },
];

const DEFAULT_ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL";

// ── Phase labels ─────────────────────────────────────────────────────────────
const PHASE_LABELS: Record<string, { label: string; color: string }> = {
  INFO_PENDING:   { label: "Gathering Info",      color: "#f59e0b" },
  INFO_COLLECTED: { label: "Preparing Questions", color: "#3b82f6" },
  INTERVIEWING:   { label: "Technical Interview", color: "#10b981" },
  CLOSED:         { label: "Session Ended",        color: "#6b7280" },
};

export default function Chat() {
  const [provider, setProvider] = useState<Provider>("openai");
  const [apiKeys,  setApiKeys]  = useState<Record<Provider, string>>({
    openai:    "",
    anthropic: "",
    gemini:    "",
  });
  const [whisperApiKey, setWhisperApiKey] = useState("");
  const [elevenLabsApiKey, setElevenLabsApiKey] = useState("");
  const [elevenLabsVoiceId, setElevenLabsVoiceId] = useState(DEFAULT_ELEVENLABS_VOICE_ID);

  const activeKey     = apiKeys[provider];
  const activeProvider = PROVIDERS.find(p => p.id === provider)!;

  const { messages, isLoading, isClosed, phase, sendMessage, sendVoiceMessage, sendCvFile, clearChat } =
    useTalentScout({
      provider,
      apiKey: activeKey,
      whisperApiKey,
      elevenLabsApiKey,
      elevenLabsVoiceId,
    });

  const handleSend = async (content: string) => {
    if (!activeKey) {
      toast({ title: "API Key Required", description: `Please enter your ${activeProvider.name} API key.`, variant: "destructive" });
      return;
    }
    try {
      await sendMessage(content);
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    }
  };

  const handleSendVoice = async (audioBlob: Blob) => {
    if (!activeKey) {
      toast({ title: "API Key Required", description: `Please enter your ${activeProvider.name} API key.`, variant: "destructive" });
      return;
    }
    if (!elevenLabsApiKey.trim()) {
      toast({ title: "ElevenLabs Key Required", description: "Add your ElevenLabs API key to enable voice replies.", variant: "destructive" });
      return;
    }
    if (provider !== "openai" && !whisperApiKey.trim()) {
      toast({ title: "Whisper Key Required", description: "For Anthropic/Gemini chat, add an OpenAI key for Whisper transcription.", variant: "destructive" });
      return;
    }

    try {
      await sendVoiceMessage(audioBlob);
    } catch (err: any) {
      toast({ title: "Voice Error", description: err.message, variant: "destructive" });
    }
  };

  const handleSendCv = async (file: File) => {
    if (!activeKey) {
      toast({ title: "API Key Required", description: `Please enter your ${activeProvider.name} API key.`, variant: "destructive" });
      return;
    }

    const isSupported = (
      file.type === "application/pdf"
      || file.name.toLowerCase().endsWith(".pdf")
    );
    if (!isSupported) {
      toast({ title: "Unsupported CV format", description: "Please upload PDF CV only.", variant: "destructive" });
      return;
    }

    try {
      await sendCvFile(file);
    } catch (err: any) {
      toast({ title: "CV Intake Error", description: err.message, variant: "destructive" });
    }
  };

  const phaseInfo = PHASE_LABELS[phase] ?? PHASE_LABELS["INFO_PENDING"];

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">

      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="flex w-72 flex-col gap-5 border-r border-border/20 bg-card/20 p-5 backdrop-blur-xl">

        {/* Brand */}
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold text-foreground">🎯 TalentScout</span>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          AI-powered hiring assistant. Select a provider, add your API key, and start interviewing.
        </p>

        <hr className="border-border/20" />

        {/* Provider selector */}
        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            AI Provider
          </span>
          <div className="flex flex-col gap-1">
            {PROVIDERS.map(p => (
              <button
                key={p.id}
                onClick={() => setProvider(p.id)}
                className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors
                  ${provider === p.id
                    ? "bg-accent text-accent-foreground font-medium"
                    : "hover:bg-accent/50 text-muted-foreground"}`}
              >
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
                {p.name}
              </button>
            ))}
          </div>
        </div>

        {/* API Key input */}
        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {activeProvider.name} API Key
          </span>
          <Input
            type="password"
            placeholder={activeProvider.placeholder}
            value={apiKeys[provider]}
            onChange={e => setApiKeys(prev => ({ ...prev, [provider]: e.target.value }))}
            className="text-xs font-mono"
          />
          {!activeKey && (
            <p className="text-xs text-destructive">Key required to start</p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Whisper (OpenAI) Key
          </span>
          <Input
            type="password"
            placeholder="sk-... (optional for OpenAI provider)"
            value={whisperApiKey}
            onChange={(e) => setWhisperApiKey(e.target.value)}
            className="text-xs font-mono"
          />
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            ElevenLabs API Key
          </span>
          <Input
            type="password"
            placeholder="xi-..."
            value={elevenLabsApiKey}
            onChange={(e) => setElevenLabsApiKey(e.target.value)}
            className="text-xs font-mono"
          />
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            ElevenLabs Voice ID
          </span>
          <Input
            type="text"
            placeholder={DEFAULT_ELEVENLABS_VOICE_ID}
            value={elevenLabsVoiceId}
            onChange={(e) => setElevenLabsVoiceId(e.target.value)}
            className="text-xs font-mono"
          />
        </div>

        <div className="mt-auto flex flex-col gap-2">
          <Button
            variant="outline"
            className="w-full gap-2"
            onClick={clearChat}
            disabled={!activeKey}
          >
            <MessageSquarePlus className="h-4 w-4" />
            New Interview
          </Button>
        </div>
      </aside>

      {/* ── Main area ───────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col">

        {/* Header */}
        <header className="flex items-center gap-2 border-b border-border/20 bg-card/20 px-6 py-3 backdrop-blur-xl">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: phaseInfo.color }} />
          <span className="text-sm font-medium text-foreground">{phaseInfo.label}</span>
          <span className="mx-2 text-border">·</span>
          <span className="text-xs text-muted-foreground">{activeProvider.name}</span>
          {!activeKey && (
            <span className="ml-1 text-xs text-destructive">— API key not set</span>
          )}
          {isClosed && (
            <span className="ml-auto text-xs text-muted-foreground">
              Session closed — click "New Interview" to restart
            </span>
          )}
        </header>

        {/* No key state */}
        {!activeKey && messages.length === 0 && (
          <div className="flex flex-1 items-center justify-center text-center text-muted-foreground">
            <div>
              <p className="text-4xl mb-3">🔑</p>
              <p className="text-sm font-medium">Enter your {activeProvider.name} API key to begin</p>
              <p className="text-xs mt-1">Your key is never stored — it's sent directly to the AI provider.</p>
            </div>
          </div>
        )}

        {/* Messages */}
        {(activeKey || messages.length > 0) && (
          <ChatMessages messages={messages} isLoading={isLoading} />
        )}

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          onSendVoice={handleSendVoice}
          onSendCv={handleSendCv}
          disabled={isLoading || isClosed || !activeKey}
        />

        {/* Closed banner */}
        {isClosed && (
          <div className="border-t border-border/20 bg-muted/30 px-6 py-2 text-center text-xs text-muted-foreground">
            Session ended — click <strong>New Interview</strong> in the sidebar to start fresh.
          </div>
        )}
      </div>
    </div>
  );
}
