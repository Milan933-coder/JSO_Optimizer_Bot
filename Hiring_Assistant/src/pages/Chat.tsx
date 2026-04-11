import { useState } from "react";

import { CodingRoundPanel } from "@/coding-round/CodingRoundPanel";
import { CandidateInfoForm, type CandidateInfoFormValues } from "@/components/chat/CandidateInfoForm";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatMessages } from "@/components/chat/ChatMessages";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Provider, useTalentScout } from "@/hooks/useTalentScout";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { Maximize2, MessageSquarePlus, Play, Power, SlidersHorizontal } from "lucide-react";

const PROVIDERS: { id: Provider; name: string; color: string; placeholder: string }[] = [
  { id: "openai", name: "OpenAI GPT-4o", color: "#10a37f", placeholder: "sk-..." },
  { id: "anthropic", name: "Anthropic Claude", color: "#d97706", placeholder: "sk-ant-..." },
  { id: "gemini", name: "Google Gemini", color: "#4285f4", placeholder: "AIza..." },
];

const DEFAULT_ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL";
const DEFAULT_JUDGE0_BASE_URL = "https://ce.judge0.com";

const PHASE_LABELS: Record<string, { label: string; color: string }> = {
  INFO_PENDING: { label: "Gathering Info", color: "#f59e0b" },
  INFO_COLLECTED: { label: "Preparing Questions", color: "#3b82f6" },
  INTERVIEWING: { label: "Technical Interview", color: "#10b981" },
  CODING_ROUND: { label: "Coding Round", color: "#f97316" },
  CLOSED: { label: "Session Ended", color: "#6b7280" },
};

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}

export default function Chat() {
  const [provider, setProvider] = useState<Provider>("openai");
  const [apiKeys, setApiKeys] = useState<Record<Provider, string>>({
    openai: "",
    anthropic: "",
    gemini: "",
  });
  const [whisperApiKey, setWhisperApiKey] = useState("");
  const [elevenLabsApiKey, setElevenLabsApiKey] = useState("");
  const [elevenLabsVoiceId, setElevenLabsVoiceId] = useState(DEFAULT_ELEVENLABS_VOICE_ID);
  const [judge0ApiKey, setJudge0ApiKey] = useState("");
  const [judge0BaseUrl, setJudge0BaseUrl] = useState(DEFAULT_JUDGE0_BASE_URL);
  const [isSidebarSheetOpen, setIsSidebarSheetOpen] = useState(false);
  const [isStopDialogOpen, setIsStopDialogOpen] = useState(false);

  const activeKey = apiKeys[provider];
  const activeProvider = PROVIDERS.find((item) => item.id === provider)!;

  const {
    messages,
    isLoading,
    isClosed,
    phase,
    codingRound,
    hasActiveSession,
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
  } = useTalentScout({
    provider,
    apiKey: activeKey,
    whisperApiKey,
    elevenLabsApiKey,
    elevenLabsVoiceId,
    judge0ApiKey,
    judge0BaseUrl,
  });

  const handleSend = async (content: string) => {
    if (!activeKey) {
      toast({
        title: "API Key Required",
        description: `Please enter your ${activeProvider.name} API key.`,
        variant: "destructive",
      });
      return;
    }
    try {
      await sendMessage(content);
    } catch (error: unknown) {
      toast({ title: "Error", description: getErrorMessage(error), variant: "destructive" });
    }
  };

  const handleSendVoice = async (audioBlob: Blob) => {
    if (!activeKey) {
      toast({
        title: "API Key Required",
        description: `Please enter your ${activeProvider.name} API key.`,
        variant: "destructive",
      });
      return;
    }
    if (!elevenLabsApiKey.trim()) {
      toast({
        title: "ElevenLabs Key Required",
        description: "Add your ElevenLabs API key to enable voice replies.",
        variant: "destructive",
      });
      return;
    }
    if (provider !== "openai" && !whisperApiKey.trim()) {
      toast({
        title: "Whisper Key Required",
        description: "For Anthropic/Gemini chat, add an OpenAI key for Whisper transcription.",
        variant: "destructive",
      });
      return;
    }

    try {
      await sendVoiceMessage(audioBlob);
    } catch (error: unknown) {
      toast({ title: "Voice Error", description: getErrorMessage(error), variant: "destructive" });
    }
  };

  const handleSendCv = async (file: File) => {
    if (!activeKey) {
      toast({
        title: "API Key Required",
        description: `Please enter your ${activeProvider.name} API key.`,
        variant: "destructive",
      });
      return;
    }

    const isSupported = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isSupported) {
      toast({
        title: "Unsupported CV format",
        description: "Please upload PDF CV only.",
        variant: "destructive",
      });
      return;
    }

    try {
      await sendCvFile(file);
    } catch (error: unknown) {
      toast({ title: "CV Intake Error", description: getErrorMessage(error), variant: "destructive" });
    }
  };

  const phaseInfo = PHASE_LABELS[phase] ?? PHASE_LABELS.INFO_PENDING;
  const candidateFormDisabledReason =
    !activeKey
      ? `Enter your ${activeProvider.name} API key first.`
      : isLoading
        ? "Connecting to the interview session..."
        : !hasActiveSession
          ? sessionError || "The interview session is not ready yet. Check the API key and backend connection."
          : null;
  const chatInputDisabled = isLoading || isClosed || !activeKey || Boolean(codingRound?.is_active);
  const canStopSession = Boolean(hasActiveSession && !isClosed && !isLoading);
  const canStartManualDsaRound = Boolean(
    activeKey && !isLoading && !isClosed && !codingRound && phase === "INTERVIEWING",
  );
  const dsaRoundLockedReason = !activeKey
    ? "Add your API key first."
    : codingRound?.is_active
      ? "The coding round is already active."
      : codingRound
        ? "A coding round has already been created for this session."
        : isClosed
          ? "This session is closed."
          : phase !== "INTERVIEWING"
            ? "Available after the technical interview starts."
            : "Ready to start now.";

  const handleStartDsaRound = async () => {
    try {
      await startCodingRound();
      setIsSidebarSheetOpen(false);
    } catch (error: unknown) {
      toast({ title: "Error", description: getErrorMessage(error), variant: "destructive" });
    }
  };

  const handleSubmitCandidateInfo = async (values: CandidateInfoFormValues) => {
    try {
      await submitCandidateInfo(values);
    } catch (error: unknown) {
      toast({ title: "Error", description: getErrorMessage(error), variant: "destructive" });
    }
  };

  const handleStopSession = async () => {
    try {
      await stopSession();
      setIsSidebarSheetOpen(false);
      setIsStopDialogOpen(false);
    } catch (error: unknown) {
      toast({ title: "Error", description: getErrorMessage(error), variant: "destructive" });
    }
  };

  const handleClearChat = () => {
    clearChat();
    setIsSidebarSheetOpen(false);
  };

  const renderSidebarContent = (mode: "panel" | "sheet") => (
    <div
      className={cn(
        "flex h-full flex-col overflow-y-auto bg-[radial-gradient(circle_at_top,#1e293b,transparent_34%),linear-gradient(180deg,rgba(2,6,23,0.98),rgba(15,23,42,0.98))] text-slate-100",
        mode === "sheet" ? "px-5 pb-6 pt-16 sm:px-8" : "px-5 py-5 xl:px-6 xl:py-6",
      )}
    >
      <div className="space-y-4">
        <div className="rounded-[28px] border border-white/10 bg-white/5 p-5 shadow-2xl shadow-slate-950/35 backdrop-blur-xl">
          <div className="flex items-start gap-3">
            <div className="space-y-2">
              <p className="text-[11px] uppercase tracking-[0.32em] text-slate-400">
                {mode === "sheet" ? "Expanded Controls" : "Control Deck"}
              </p>
              <h1 className="text-2xl font-semibold tracking-tight text-white">TalentScout</h1>
              <p className="max-w-sm text-sm leading-6 text-slate-300">
                Tune providers, voice tools, and the DSA round from one place, then jump back into the interview.
              </p>
            </div>

            {mode === "panel" && (
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsSidebarSheetOpen(true)}
                className="ml-auto gap-2 border-white/15 bg-slate-950/60 text-slate-100 hover:bg-slate-900"
              >
                <Maximize2 className="h-4 w-4" />
                Full Window
              </Button>
            )}
          </div>
        </div>

        <div className="rounded-[28px] border border-white/10 bg-white/5 p-4 shadow-xl shadow-slate-950/20 backdrop-blur-xl">
          <div className="mb-4 flex items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">AI Provider</span>
            <Badge variant="outline" className="border-white/15 bg-slate-950/60 text-slate-200">
              {activeProvider.name}
            </Badge>
          </div>

          <div className="space-y-2">
            {PROVIDERS.map((item) => (
              <button
                key={item.id}
                onClick={() => setProvider(item.id)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-2xl border px-3 py-3 text-left text-sm transition-all",
                  provider === item.id
                    ? "border-white/20 bg-white text-slate-950 shadow-lg shadow-white/10"
                    : "border-white/10 bg-slate-950/55 text-slate-300 hover:border-white/20 hover:bg-slate-900/80",
                )}
              >
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="font-medium">{item.name}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-4 rounded-[28px] border border-white/10 bg-white/5 p-4 shadow-xl shadow-slate-950/20 backdrop-blur-xl">
          <div className="grid gap-4">
            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                {activeProvider.name} API Key
              </span>
              <Input
                type="password"
                placeholder={activeProvider.placeholder}
                value={apiKeys[provider]}
                onChange={(event) => setApiKeys((prev) => ({ ...prev, [provider]: event.target.value }))}
                className="border-white/10 bg-slate-950/70 font-mono text-xs text-slate-100 placeholder:text-slate-500"
              />
              {!activeKey && <p className="text-xs text-rose-300">Key required to start</p>}
            </div>

            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                Whisper (OpenAI) Key
              </span>
              <Input
                type="password"
                placeholder="sk-... (optional for OpenAI provider)"
                value={whisperApiKey}
                onChange={(event) => setWhisperApiKey(event.target.value)}
                className="border-white/10 bg-slate-950/70 font-mono text-xs text-slate-100 placeholder:text-slate-500"
              />
            </div>

            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                ElevenLabs API Key
              </span>
              <Input
                type="password"
                placeholder="xi-..."
                value={elevenLabsApiKey}
                onChange={(event) => setElevenLabsApiKey(event.target.value)}
                className="border-white/10 bg-slate-950/70 font-mono text-xs text-slate-100 placeholder:text-slate-500"
              />
            </div>

            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                ElevenLabs Voice ID
              </span>
              <Input
                type="text"
                placeholder={DEFAULT_ELEVENLABS_VOICE_ID}
                value={elevenLabsVoiceId}
                onChange={(event) => setElevenLabsVoiceId(event.target.value)}
                className="border-white/10 bg-slate-950/70 font-mono text-xs text-slate-100 placeholder:text-slate-500"
              />
            </div>

            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                Judge0 Base URL
              </span>
              <Input
                type="text"
                placeholder={DEFAULT_JUDGE0_BASE_URL}
                value={judge0BaseUrl}
                onChange={(event) => setJudge0BaseUrl(event.target.value)}
                className="border-white/10 bg-slate-950/70 font-mono text-xs text-slate-100 placeholder:text-slate-500"
              />
            </div>

            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                Judge0 API Key
              </span>
              <Input
                type="password"
                placeholder="Optional on public CE, required on secured instances"
                value={judge0ApiKey}
                onChange={(event) => setJudge0ApiKey(event.target.value)}
                className="border-white/10 bg-slate-950/70 font-mono text-xs text-slate-100 placeholder:text-slate-500"
              />
            </div>
          </div>
        </div>

        <div className="rounded-[28px] border border-amber-300/15 bg-amber-300/10 p-4 shadow-xl shadow-slate-950/20 backdrop-blur-xl">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-amber-100">DSA Round</span>
            <Badge
              variant={canStartManualDsaRound ? "default" : "outline"}
              className={cn(
                canStartManualDsaRound
                  ? "bg-amber-300 text-slate-950 hover:bg-amber-300"
                  : "border-white/15 bg-slate-950/50 text-slate-100",
              )}
            >
              {codingRound?.is_active ? "Live" : canStartManualDsaRound ? "Ready" : "Locked"}
            </Badge>
          </div>

          <p className="mt-3 text-sm leading-6 text-slate-200">
            Start the coding round here, or type <strong>start dsa round</strong> in chat once the interview reaches the
            technical phase.
          </p>

          <Button
            type="button"
            variant={canStartManualDsaRound ? "default" : "outline"}
            className={cn(
              "mt-4 w-full gap-2",
              canStartManualDsaRound
                ? "bg-amber-300 text-slate-950 hover:bg-amber-200"
                : "border-white/15 bg-slate-950/60 text-slate-100 hover:bg-slate-900",
            )}
            onClick={() => void handleStartDsaRound()}
            disabled={!canStartManualDsaRound}
          >
            <Play className="h-4 w-4" />
            Start DSA Round
          </Button>

          <p className="mt-3 text-xs leading-5 text-slate-300">{dsaRoundLockedReason}</p>
        </div>
      </div>

      <div className="mt-4">
        <div className="grid gap-3">
          <Button
            variant="outline"
            className="w-full gap-2 border-rose-400/25 bg-rose-500/10 text-rose-100 hover:bg-rose-500/20"
            onClick={() => setIsStopDialogOpen(true)}
            disabled={!canStopSession}
          >
            <Power className="h-4 w-4" />
            Stop Session
          </Button>

          <Button
            variant="outline"
            className="w-full gap-2 border-white/15 bg-slate-950/60 text-slate-100 hover:bg-slate-900"
            onClick={handleClearChat}
            disabled={!activeKey}
          >
            <MessageSquarePlus className="h-4 w-4" />
            New Interview
          </Button>
        </div>
      </div>
    </div>
  );

  const renderInterviewContent = () => (
    <div className="flex min-h-screen min-w-0 flex-1 flex-col xl:h-full xl:min-h-0">
      <header className="flex flex-wrap items-center gap-2 border-b border-border/20 bg-card/20 px-4 py-3 backdrop-blur-xl sm:px-6">
        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: phaseInfo.color }} />
        <span className="text-sm font-medium text-foreground">{phaseInfo.label}</span>
        <span className="mx-1 text-border">.</span>
        <span className="text-xs text-muted-foreground">{activeProvider.name}</span>
        {!activeKey && <span className="text-xs text-destructive">- API key not set</span>}

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setIsSidebarSheetOpen(true)}
            className="gap-2 border-border/40 bg-background/40"
          >
            <SlidersHorizontal className="h-4 w-4" />
            Controls
          </Button>

          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setIsStopDialogOpen(true)}
            className="gap-2 border-rose-400/30 bg-rose-500/10 text-rose-700 hover:bg-rose-500/20"
            disabled={!canStopSession}
          >
            <Power className="h-4 w-4" />
            Stop Session
          </Button>

          {canStartManualDsaRound && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => void handleStartDsaRound()}
              className="gap-2 border-amber-400/40 bg-amber-400/10 text-amber-800 hover:bg-amber-400/20"
            >
              <Play className="h-4 w-4" />
              Start DSA Round
            </Button>
          )}

          {isClosed && !canStartManualDsaRound && (
            <span className="text-xs text-muted-foreground">
              Session closed - click "New Interview" to restart
            </span>
          )}
        </div>
      </header>

      {canStartManualDsaRound && (
        <div className="border-b border-border/20 bg-sky-500/10 px-4 py-3 text-sm text-sky-900 sm:px-6">
          You can start the DSA round any time from here, or type <strong>start dsa round</strong> in chat.
        </div>
      )}

      {!activeKey && messages.length === 0 && (
        <div className="flex flex-1 items-center justify-center px-6 text-center text-muted-foreground">
          <div>
            <p className="mb-3 text-4xl">Key</p>
            <p className="text-sm font-medium">Enter your {activeProvider.name} API key to begin</p>
            <p className="mt-1 text-xs">Your key is never stored - it is sent directly to the AI provider.</p>
          </div>
        </div>
      )}

      {phase === "INFO_PENDING" && activeKey && (
        <div className="flex-1 overflow-y-auto">
          <CandidateInfoForm
            isLoading={isLoading}
            submitDisabledReason={candidateFormDisabledReason}
            onSubmit={handleSubmitCandidateInfo}
          />
        </div>
      )}

      {phase !== "INFO_PENDING" && (activeKey || messages.length > 0) && (
        <ChatMessages messages={messages} isLoading={isLoading} />
      )}

      {phase !== "INFO_PENDING" && (
        <ChatInput
          onSend={handleSend}
          onSendVoice={handleSendVoice}
          onSendCv={handleSendCv}
          disabled={chatInputDisabled}
        />
      )}

      {isClosed && (
        <div className="border-t border-border/20 bg-muted/30 px-6 py-2 text-center text-xs text-muted-foreground">
          Session ended - click <strong>New Interview</strong> in the sidebar to start fresh.
        </div>
      )}
    </div>
  );

  const renderCodingWorkspace = () => {
    if (!codingRound) return null;

    return (
      <div className="flex min-h-screen min-w-0 flex-1 flex-col xl:h-full xl:min-h-0">
        <header className="flex flex-wrap items-center gap-2 border-b border-border/20 bg-card/20 px-4 py-3 backdrop-blur-xl sm:px-6">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: phaseInfo.color }} />
          <span className="text-sm font-medium text-foreground">{phaseInfo.label}</span>
          <span className="mx-1 text-border">.</span>
          <span className="text-xs text-muted-foreground">{activeProvider.name}</span>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setIsSidebarSheetOpen(true)}
              className="gap-2 border-border/40 bg-background/40"
            >
              <SlidersHorizontal className="h-4 w-4" />
              Controls
            </Button>

            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setIsStopDialogOpen(true)}
              className="gap-2 border-rose-400/30 bg-rose-500/10 text-rose-700 hover:bg-rose-500/20"
              disabled={!canStopSession}
            >
              <Power className="h-4 w-4" />
              Stop Session
            </Button>

            <span className="text-xs text-amber-700">
              Coding workspace live - interview chat is paused while the timer runs
            </span>
          </div>
        </header>

        <CodingRoundPanel
          codingRound={codingRound}
          isBusy={isLoading}
          onRun={runCodingRound}
          onSubmit={submitCodingRound}
        />
      </div>
    );
  };

  const renderMainContent = () => (codingRound ? renderCodingWorkspace() : renderInterviewContent());

  return (
    <AlertDialog open={isStopDialogOpen} onOpenChange={setIsStopDialogOpen}>
      <Sheet open={isSidebarSheetOpen} onOpenChange={setIsSidebarSheetOpen}>
        <div className="min-h-screen bg-background text-foreground xl:h-screen">
          <div className="xl:hidden">{renderMainContent()}</div>

          <div className="hidden h-full xl:block">
            <ResizablePanelGroup direction="horizontal" className="bg-background">
              <ResizablePanel defaultSize={23} minSize={18} maxSize={38}>
                {renderSidebarContent("panel")}
              </ResizablePanel>

              <ResizableHandle withHandle className="bg-border/20" />

              <ResizablePanel defaultSize={77}>{renderMainContent()}</ResizablePanel>
            </ResizablePanelGroup>
          </div>
        </div>

        <SheetContent
          side="left"
          className="w-full border-0 bg-transparent p-0 text-slate-100 sm:max-w-none"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>TalentScout Controls</SheetTitle>
            <SheetDescription>Expanded sidebar controls for provider settings and DSA round actions.</SheetDescription>
          </SheetHeader>
          {renderSidebarContent("sheet")}
        </SheetContent>
      </Sheet>

      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Stop this session?</AlertDialogTitle>
          <AlertDialogDescription>
            This will close the current interview immediately. Typed messages will no longer stop the session, so use
            this button only when you really want to end it.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep Interviewing</AlertDialogCancel>
          <AlertDialogAction
            onClick={() => void handleStopSession()}
            className="bg-rose-600 text-white hover:bg-rose-500"
          >
            Stop Session
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
