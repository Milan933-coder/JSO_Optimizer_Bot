import { useEffect, useMemo, useState, type ReactNode } from "react";
import MonacoEditor from "@monaco-editor/react";
import {
  CheckCircle2,
  Clock3,
  Code2,
  ExternalLink,
  Loader2,
  Play,
  Send,
  XCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkBreaks from "remark-breaks";
import remarkMath from "remark-math";

import type { CodingRoundState, CodingSampleResult } from "@/coding-round/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

interface CodingRoundPanelProps {
  codingRound: CodingRoundState;
  isBusy: boolean;
  onRun: (input: {
    sourceCode: string;
    languageSlug: "python" | "cpp" | "java" | "javascript";
    sampleIndex: number;
  }) => Promise<void>;
  onSubmit: (input: {
    sourceCode: string;
    languageSlug: "python" | "cpp" | "java" | "javascript";
  }) => Promise<void>;
}

type SupportedLanguage = "python" | "cpp" | "java" | "javascript";

const PANEL_SHELL_CLASS =
  "overflow-hidden rounded-2xl border border-zinc-800/80 bg-[#0b1120]/95 shadow-[0_24px_80px_rgba(2,6,23,0.45)]";
const MINIMAL_SCROLLBAR_CLASS =
  "[scrollbar-width:thin] [scrollbar-color:rgba(113,113,122,0.55)_transparent] [&::-webkit-scrollbar]:h-1.5 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-zinc-700/60 [&::-webkit-scrollbar-thumb:hover]:bg-zinc-600/80";

function formatCountdown(totalSeconds: number): string {
  const safeSeconds = Math.max(totalSeconds, 0);
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
}

function prettifyStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function displayValue(value?: string | null): string {
  return value && value.trim() ? value : "(empty)";
}

function normalizeProblemMarkdown(value?: string | null): string {
  if (!value) return "";
  return value
    .replace(/\$\$\$\$\$\$/g, "$$")
    .replace(/\$\$\$/g, "$")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function getMonacoLanguage(language: SupportedLanguage): string {
  if (language === "cpp") return "cpp";
  if (language === "javascript") return "javascript";
  if (language === "java") return "java";
  return "python";
}

function ProblemMarkdown({
  content,
  className,
}: {
  content?: string | null;
  className?: string;
}) {
  const normalized = normalizeProblemMarkdown(content);

  if (!normalized) {
    return <p className="text-sm leading-7 text-zinc-500">No details were provided for this section.</p>;
  }

  return (
    <div
      className={cn(
        "problem-markdown prose prose-invert max-w-none text-sm leading-7 text-zinc-400",
        "prose-p:my-3 prose-p:text-zinc-400",
        "prose-headings:text-zinc-100 prose-strong:text-zinc-100",
        "prose-ul:my-3 prose-ol:my-3 prose-li:text-zinc-400 prose-li:marker:text-zinc-500",
        "prose-code:rounded-lg prose-code:bg-zinc-950 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-zinc-200 prose-code:before:hidden prose-code:after:hidden",
        "prose-pre:overflow-x-auto prose-pre:rounded-lg prose-pre:border prose-pre:border-zinc-800 prose-pre:bg-zinc-950 prose-pre:text-zinc-200",
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkMath, remarkBreaks]} rehypePlugins={[rehypeKatex]}>
        {normalized}
      </ReactMarkdown>
    </div>
  );
}

function PanelSection({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-zinc-100">{label}</h3>
      {children}
    </section>
  );
}

function ValueCard({
  label,
  value,
  tone = "text-zinc-200",
}: {
  label: string;
  value?: string | null;
  tone?: string;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-zinc-500">{label}</p>
      <pre
        className={cn(
          "mt-3 max-h-32 overflow-auto whitespace-pre-wrap font-mono text-sm leading-7",
          MINIMAL_SCROLLBAR_CLASS,
          tone,
        )}
      >
        {displayValue(value)}
      </pre>
    </div>
  );
}

function ResultCard({ sampleResult }: { sampleResult: CodingSampleResult }) {
  return (
    <article className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-100">
          {sampleResult.passed ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          ) : (
            <XCircle className="h-4 w-4 text-rose-400" />
          )}
          Sample {sampleResult.sample_index + 1}
        </div>
        <span className="text-xs text-zinc-500">{sampleResult.judge0_status}</span>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/80 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-zinc-500">Expected Output</p>
          <pre
            className={cn(
              "mt-3 max-h-28 overflow-auto whitespace-pre-wrap font-mono text-xs leading-6 text-emerald-300",
              MINIMAL_SCROLLBAR_CLASS,
            )}
          >
            {displayValue(sampleResult.expected_output)}
          </pre>
        </div>

        <div className="rounded-lg border border-zinc-800 bg-zinc-900/80 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-zinc-500">Actual Output</p>
          <pre
            className={cn(
              "mt-3 max-h-28 overflow-auto whitespace-pre-wrap font-mono text-xs leading-6 text-zinc-200",
              MINIMAL_SCROLLBAR_CLASS,
            )}
          >
            {displayValue(sampleResult.actual_output)}
          </pre>
        </div>

        {(sampleResult.stderr || sampleResult.compile_output || sampleResult.message) && (
          <div className="rounded-lg border border-rose-500/20 bg-rose-950/20 p-4 lg:col-span-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-rose-200">Diagnostics</p>
            <pre
              className={cn(
                "mt-3 max-h-28 overflow-auto whitespace-pre-wrap font-mono text-xs leading-6 text-rose-100",
                MINIMAL_SCROLLBAR_CLASS,
              )}
            >
              {displayValue(sampleResult.compile_output || sampleResult.stderr || sampleResult.message)}
            </pre>
          </div>
        )}
      </div>
    </article>
  );
}

export function CodingRoundPanel({
  codingRound,
  isBusy,
  onRun,
  onSubmit,
}: CodingRoundPanelProps) {
  const roundKey = `${codingRound.problem.codeforces_id}-${codingRound.started_at ?? "pending"}`;
  const availableLanguages = codingRound.problem.available_languages;
  const [selectedLanguage, setSelectedLanguage] = useState<SupportedLanguage>("python");
  const [selectedSampleIndex, setSelectedSampleIndex] = useState(0);
  const [remainingSeconds, setRemainingSeconds] = useState(codingRound.remaining_seconds);
  const [sourceByLanguage, setSourceByLanguage] = useState<Record<string, string>>({});
  const [pendingAction, setPendingAction] = useState<"run" | "submit" | null>(null);

  useEffect(() => {
    const initialLanguage = (availableLanguages[0]?.slug ?? "python") as SupportedLanguage;
    const initialSources = Object.fromEntries(
      availableLanguages.map((language) => [language.slug, language.starter_code]),
    );
    setSelectedLanguage(initialLanguage);
    setSelectedSampleIndex(0);
    setSourceByLanguage(initialSources);
    setPendingAction(null);
  }, [roundKey, availableLanguages]);

  useEffect(() => {
    setRemainingSeconds(codingRound.remaining_seconds);
  }, [codingRound.remaining_seconds]);

  useEffect(() => {
    if (!codingRound.is_active) return;
    const timer = window.setInterval(() => {
      setRemainingSeconds((prev) => Math.max(prev - 1, 0));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [codingRound.is_active, roundKey]);

  const activeCode = sourceByLanguage[selectedLanguage] ?? "";
  const latestResult = codingRound.last_result ?? null;
  const isLocked = !codingRound.is_active || codingRound.attempts_left <= 0;
  const activeSample = codingRound.problem.samples[selectedSampleIndex] ?? codingRound.problem.samples[0];
  const statusLabel = prettifyStatus(codingRound.status);
  const isCriticalTimer = remainingSeconds <= 300;
  const notesContent = codingRound.problem.notes?.trim() || "No extra notes were provided for this problem.";
  const monacoLanguage = useMemo(() => getMonacoLanguage(selectedLanguage), [selectedLanguage]);

  const updateCode = (nextCode: string) => {
    setSourceByLanguage((prev) => ({
      ...prev,
      [selectedLanguage]: nextCode,
    }));
  };

  const handleRun = async () => {
    if (isBusy || isLocked) return;
    setPendingAction("run");
    try {
      await onRun({
        sourceCode: activeCode,
        languageSlug: selectedLanguage,
        sampleIndex: selectedSampleIndex,
      });
    } finally {
      setPendingAction(null);
    }
  };

  const handleSubmit = async () => {
    if (isBusy || isLocked) return;
    setPendingAction("submit");
    try {
      await onSubmit({
        sourceCode: activeCode,
        languageSlug: selectedLanguage,
      });
    } finally {
      setPendingAction(null);
    }
  };

  return (
    <section className="flex h-screen min-h-0 w-full flex-col overflow-hidden bg-[#0f172a] text-zinc-100">
      <header className="sticky top-0 z-20 border-b border-zinc-800/80 bg-[#0f172a]/95 backdrop-blur-xl">
        <div className="flex flex-col gap-6 px-6 py-5 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex items-start gap-4">
            <div className="rounded-xl border border-sky-500/20 bg-sky-500/10 p-3 text-sky-200">
              <Code2 className="h-5 w-5" />
            </div>
            <div className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-zinc-500">Session Status</p>
              <div>
                <h2 className="text-2xl font-semibold text-zinc-100">{codingRound.problem.title}</h2>
                <p className="text-sm leading-6 text-zinc-400">
                  {statusLabel} with {codingRound.attempts_left}/{codingRound.max_attempts} attempts left.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-3 xl:items-end">
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-zinc-500">Timer / Controls</p>
            <div className="flex flex-wrap items-center gap-3">
              <div
                className={cn(
                  "inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium",
                  isCriticalTimer
                    ? "border-rose-400/40 bg-rose-500/10 text-rose-100"
                    : "border-zinc-800 bg-zinc-900/80 text-zinc-100",
                )}
              >
                <Clock3 className="h-4 w-4" />
                {formatCountdown(remainingSeconds)}
              </div>

              <Badge variant="outline" className="rounded-lg border-zinc-700 bg-zinc-900/80 text-zinc-200">
                Rating {codingRound.problem.rating}
              </Badge>

              <Badge
                variant="outline"
                className={cn(
                  "rounded-lg border-zinc-700",
                  codingRound.is_completed ? "bg-emerald-500/10 text-emerald-200" : "bg-zinc-900/80 text-zinc-200",
                )}
              >
                {statusLabel}
              </Badge>

              <a
                href={codingRound.problem.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900/80 px-4 py-2 text-sm text-zinc-200 transition-colors hover:border-zinc-500 hover:bg-zinc-800"
              >
                Open Source
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 gap-6 overflow-hidden p-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <aside className={PANEL_SHELL_CLASS}>
          <div className="flex h-full min-h-0 flex-col">
            <div className="border-b border-zinc-800/80 p-6">
              <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-zinc-500">Problem Description</p>
              <h3 className="mt-2 text-lg font-semibold text-zinc-100">Read carefully before you code</h3>
            </div>

            <div className={cn("min-h-0 flex-1 space-y-8 overflow-y-auto p-6", MINIMAL_SCROLLBAR_CLASS)}>
              <PanelSection label="Description">
                <ProblemMarkdown content={codingRound.problem.statement} />

                {codingRound.problem.input_spec && (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-zinc-500">Input</p>
                    <ProblemMarkdown content={codingRound.problem.input_spec} className="mt-3" />
                  </div>
                )}

                {codingRound.problem.output_spec && (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-zinc-500">Output</p>
                    <ProblemMarkdown content={codingRound.problem.output_spec} className="mt-3" />
                  </div>
                )}
              </PanelSection>

              <PanelSection label="Notes">
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-5">
                  <ProblemMarkdown content={notesContent} />
                </div>
              </PanelSection>

              <PanelSection label="Tags">
                <div className="flex flex-wrap gap-3">
                  {codingRound.problem.tags.length > 0 ? (
                    codingRound.problem.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-lg border border-zinc-700 bg-zinc-900/80 px-3 py-2 text-xs font-medium text-zinc-300"
                      >
                        {tag}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-zinc-500">No tags were provided for this challenge.</span>
                  )}
                </div>
              </PanelSection>
            </div>
          </div>
        </aside>

        <section className={cn(PANEL_SHELL_CLASS, "h-full")}>
          <div className="flex h-full min-h-0 flex-col overflow-hidden">
            <div className="border-b border-zinc-800/80 p-6">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="flex min-w-0 flex-wrap items-center gap-4">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-zinc-500">Workspace</p>
                    <h3 className="text-lg font-semibold text-zinc-100">Code Editor</h3>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <div className="w-[220px] max-w-full">
                      <Select
                        value={selectedLanguage}
                        onValueChange={(value) => setSelectedLanguage(value as SupportedLanguage)}
                      >
                        <SelectTrigger className="h-11 rounded-lg border-zinc-700 bg-zinc-900 text-zinc-100 transition-colors hover:border-zinc-500">
                          <SelectValue placeholder="Select language" />
                        </SelectTrigger>
                        <SelectContent className="border-zinc-800 bg-zinc-950 text-zinc-100">
                          {availableLanguages.map((language) => (
                            <SelectItem key={language.slug} value={language.slug}>
                              {language.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="w-[180px] max-w-full">
                      <Select value={String(selectedSampleIndex)} onValueChange={(value) => setSelectedSampleIndex(Number(value))}>
                        <SelectTrigger className="h-11 rounded-lg border-zinc-700 bg-zinc-900 text-zinc-100 transition-colors hover:border-zinc-500">
                          <SelectValue placeholder="Sample case" />
                        </SelectTrigger>
                        <SelectContent className="border-zinc-800 bg-zinc-950 text-zinc-100">
                          {codingRound.problem.samples.map((sample, index) => (
                            <SelectItem key={`${sample.title}-${index}`} value={String(index)}>
                              {sample.title}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <p className="text-sm text-zinc-500">Ctrl/Cmd + Enter runs, Ctrl/Cmd + Shift + Enter submits</p>
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <div className="min-h-0 flex-1 overflow-hidden bg-zinc-950">
                <div className="h-full min-h-[500px] flex-1 overflow-y-auto">
                  <MonacoEditor
                    key={`${roundKey}-${selectedLanguage}`}
                    language={monacoLanguage}
                    theme="vs-dark"
                    value={activeCode}
                    onChange={(value) => updateCode(value ?? "")}
                    height="100%"
                    options={{
                      automaticLayout: true,
                      scrollBeyondLastLine: false,
                      minimap: { enabled: false },
                      fontSize: 15,
                      lineHeight: 24,
                      fontFamily:
                        'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                      padding: { top: 20, bottom: 20 },
                      renderLineHighlight: "gutter",
                      lineNumbersMinChars: 3,
                      overviewRulerBorder: false,
                      smoothScrolling: true,
                      scrollbar: {
                        verticalScrollbarSize: 10,
                        horizontalScrollbarSize: 10,
                      },
                    }}
                    loading={
                      <div className="flex h-full min-h-[500px] items-center justify-center text-sm text-zinc-500">
                        Loading editor...
                      </div>
                    }
                  />
                </div>
              </div>

              <div className="border-t border-zinc-800 bg-[#0a0f1d] p-6">
                <div className="grid gap-6 md:grid-cols-2">
                  <ValueCard label="Selected Input" value={activeSample?.input} />
                  <ValueCard label="Expected Output" value={activeSample?.output} tone="text-emerald-300" />
                </div>

                {(pendingAction || latestResult) && (
                  <div className="mt-6 space-y-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-zinc-500">Execution Results</p>

                      {pendingAction && (
                        <span className="inline-flex items-center gap-2 rounded-lg border border-sky-400/20 bg-sky-500/10 px-3 py-1.5 text-sm text-sky-100">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {pendingAction === "submit" ? "Submitting samples..." : "Running selected sample..."}
                        </span>
                      )}

                      {latestResult && (
                        <>
                          <Badge
                            variant="outline"
                            className={cn(
                              "rounded-lg border-zinc-700",
                              latestResult.passed
                                ? "bg-emerald-500/10 text-emerald-200"
                                : "bg-rose-500/10 text-rose-200",
                            )}
                          >
                            {latestResult.verdict}
                          </Badge>
                          <span className="text-sm text-zinc-500">
                            Passed {latestResult.passed_samples}/{latestResult.total_samples} checked sample(s)
                          </span>
                        </>
                      )}
                    </div>

                    {latestResult && latestResult.sample_results.length > 0 ? (
                      <div className={cn("max-h-48 space-y-4 overflow-y-auto pr-1", MINIMAL_SCROLLBAR_CLASS)}>
                        {latestResult.sample_results.map((sampleResult, index) => (
                          <ResultCard key={`${sampleResult.sample_index}-${index}`} sampleResult={sampleResult} />
                        ))}
                      </div>
                    ) : !pendingAction ? (
                      <p className="text-sm text-zinc-500">Run a sample or submit to populate the result tray.</p>
                    ) : null}
                  </div>
                )}
              </div>

              <footer className="sticky bottom-0 z-10 flex shrink-0 items-center justify-between gap-4 border-t border-zinc-800 bg-[#0b1120] px-6 py-4">
                <div className="text-sm text-zinc-500">
                  Time limit: {codingRound.problem.time_limit} • Memory limit: {codingRound.problem.memory_limit}
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    type="button"
                    onClick={() => void handleRun()}
                    disabled={isBusy || isLocked}
                    className="h-11 rounded-lg bg-sky-500 px-5 text-slate-950 transition-colors hover:bg-sky-400"
                  >
                    {isBusy && pendingAction === "run" ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    Run
                  </Button>

                  <Button
                    type="button"
                    onClick={() => void handleSubmit()}
                    disabled={isBusy || isLocked}
                    className="h-11 rounded-lg bg-emerald-400 px-5 text-slate-950 transition-colors hover:bg-emerald-300"
                  >
                    {isBusy && pendingAction === "submit" ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="mr-2 h-4 w-4" />
                    )}
                    Submit
                  </Button>
                </div>
              </footer>
            </div>
          </div>
        </section>
      </div>
    </section>
  );
}
