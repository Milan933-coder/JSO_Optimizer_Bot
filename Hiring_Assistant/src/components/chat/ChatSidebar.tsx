import { useState } from "react";
import { MessageSquarePlus, Key, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiKeyModal } from "@/components/settings/ApiKeyModal";
import { PROVIDERS, type LLMProvider } from "@/types/chat";

interface ChatSidebarProps {
  provider: LLMProvider;
  onProviderChange: (p: LLMProvider) => void;
  apiKeys: Record<LLMProvider, string>;
  onSetApiKey: (p: LLMProvider, key: string) => void;
  onNewChat: () => void;
}

export function ChatSidebar({
  provider,
  onProviderChange,
  apiKeys,
  onSetApiKey,
  onNewChat,
}: ChatSidebarProps) {
  const [modalProvider, setModalProvider] = useState<LLMProvider | null>(null);
  const activeConfig = PROVIDERS.find((p) => p.id === modalProvider);

  return (
    <aside className="flex h-full w-64 flex-col border-r border-border/30 bg-card/40 backdrop-blur-xl">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border/20 px-4 py-5">
        <Zap className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-bold tracking-tight text-foreground">
          CV Chat
        </h1>
      </div>

      {/* New Chat */}
      <div className="px-3 pt-4">
        <Button
          onClick={onNewChat}
          variant="outline"
          className="w-full justify-start gap-2 border-border/30 bg-background/30 hover:bg-background/50"
        >
          <MessageSquarePlus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Provider Selection */}
      <div className="flex-1 px-3 pt-6">
        <p className="mb-3 px-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          LLM Provider
        </p>
        <div className="space-y-1.5">
          {PROVIDERS.map((p) => {
            const isActive = provider === p.id;
            const hasKey = !!apiKeys[p.id];
            return (
              <button
                key={p.id}
                onClick={() => onProviderChange(p.id)}
                className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all ${
                  isActive
                    ? "bg-primary/10 text-foreground"
                    : "text-muted-foreground hover:bg-background/40 hover:text-foreground"
                }`}
              >
                <span
                  className="h-2.5 w-2.5 rounded-full border-2 transition-all"
                  style={{
                    backgroundColor: isActive ? p.color : "transparent",
                    borderColor: p.color,
                  }}
                />
                <span className="flex-1 text-left font-medium">{p.name}</span>
                {hasKey && (
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                )}
              </button>
            );
          })}
        </div>

        {/* API Key buttons */}
        <p className="mb-3 mt-6 px-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          API Keys
        </p>
        <div className="space-y-1.5">
          {PROVIDERS.map((p) => {
            const hasKey = !!apiKeys[p.id];
            return (
              <button
                key={p.id}
                onClick={() => setModalProvider(p.id)}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-all hover:bg-background/40 hover:text-foreground"
              >
                <Key className="h-3.5 w-3.5" />
                <span className="flex-1 text-left">{p.name}</span>
                <span
                  className={`text-xs ${
                    hasKey ? "text-green-400" : "text-muted-foreground/50"
                  }`}
                >
                  {hasKey ? "Set" : "Not set"}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border/20 px-4 py-3">
        <p className="text-xs text-muted-foreground/60">
          Keys stored in session only
        </p>
      </div>

      {/* Modal */}
      {activeConfig && (
        <ApiKeyModal
          open={!!modalProvider}
          onOpenChange={(open) => !open && setModalProvider(null)}
          provider={activeConfig}
          currentKey={apiKeys[modalProvider!]}
          onSave={(key) => onSetApiKey(modalProvider!, key)}
        />
      )}
    </aside>
  );
}
