import { useEffect, useMemo, useState } from "react";
import {
  BookOpenText,
  CheckCircle2,
  Clock3,
  Code2,
  ExternalLink,
  Loader2,
  Play,
  Send,
  TerminalSquare,
  XCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkBreaks from "remark-breaks";
import remarkMath from "remark-math";

import type { CodingRoundState } from "@/coding-round/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
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

function ProblemMarkdown({
  content,
  className,
}: {
  content?: string | null;
  className?: string;
}) {
  const normalized = normalizeProblemMarkdown(content);

  if (!normalized) {
    return <p className="text-sm text-slate-400">No details were provided for this section.</p>;
  }

  return (
    <div
      className={cn(
        "problem-markdown prose prose-invert max-w-none text-sm leading-7",
        "prose-p:my-3 prose-p:text-slate-200",
        "prose-headings:text-slate-100 prose-strong:text-white",
        "prose-ul:my-3 prose-ol:my-3 prose-li:text-slate-200 prose-li:marker:text-amber-300",
        "prose-code:rounded prose-code:bg-slate-900/80 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-amber-200 prose-code:before:hidden prose-code:after:hidden",
        "prose-pre:border prose-pre:border-slate-800 prose-pre:bg-slate-950/85",
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkMath, remarkBreaks]} rehypePlugins={[rehypeKatex]}>
        {normalized}
      </ReactMarkdown>
    </div>
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
  const [selectedLanguage, setSelectedLanguage] = useState<"python" | "cpp" | "java" | "javascript">("python");
  const [selectedSampleIndex, setSelectedSampleIndex] = useState(0);
  const [remainingSeconds, setRemainingSeconds] = useState(codingRound.remaining_seconds);
  const [sourceByLanguage, setSourceByLanguage] = useState<Record<string, string>>({});
  const [hasOpenedResultPanel, setHasOpenedResultPanel] = useState(Boolean(codingRound.last_result));
  const [pendingAction, setPendingAction] = useState<"run" | "submit" | null>(null);

  useEffect(() => {
    const initialLanguage = (availableLanguages[0]?.slug ?? "python") as "python" | "cpp" | "java" | "javascript";
    const initialSources = Object.fromEntries(
      availableLanguages.map((language) => [language.slug, language.starter_code]),
    );
    setSelectedLanguage(initialLanguage);
    setSelectedSampleIndex(0);
    setSourceByLanguage(initialSources);
    setHasOpenedResultPanel(Boolean(codingRound.last_result));
    setPendingAction(null);
  }, [roundKey, availableLanguages]);

  useEffect(() => {
    setRemainingSeconds(codingRound.remaining_seconds);
  }, [codingRound.remaining_seconds]);

  useEffect(() => {
    if (codingRound.last_result) {
      setHasOpenedResultPanel(true);
      setPendingAction(null);
    }
  }, [codingRound.last_result]);

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
  const shouldShowResultPanel = hasOpenedResultPanel || Boolean(latestResult) || Boolean(pendingAction);

  const ratingVariant = codingRound.problem.rating >= 1400 ? "default" : "secondary";
  const statusVariant = useMemo(() => {
    if (codingRound.is_completed && codingRound.status === "accepted") return "default";
    if (codingRound.is_completed) return "destructive";
    return "outline";
  }, [codingRound.is_completed, codingRound.status]) as "default" | "secondary" | "destructive" | "outline";

  const updateCode = (nextCode: string) => {
    setSourceByLanguage((prev) => ({
      ...prev,
      [selectedLanguage]: nextCode,
    }));
  };

  const handleRun = async () => {
    if (isBusy || isLocked) return;
    setHasOpenedResultPanel(true);
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
    setHasOpenedResultPanel(true);
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

  const handleEditorKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || (!event.ctrlKey && !event.metaKey)) return;
    event.preventDefault();
    if (event.shiftKey) {
      void handleSubmit();
      return;
    }
    void handleRun();
  };

  const renderActionBar = () => (
    <div className="flex flex-wrap items-center gap-3 rounded-[1.4rem] border border-white/10 bg-white/5 p-3">
      <Button
        type="button"
        onClick={() => void handleRun()}
        disabled={isBusy || isLocked}
        className="bg-sky-500 text-slate-950 hover:bg-sky-400"
      >
        {isBusy && pendingAction === "run" ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Play className="mr-2 h-4 w-4" />
        )}
        Run Sample
      </Button>
      <Button
        type="button"
        onClick={() => void handleSubmit()}
        disabled={isBusy || isLocked}
        className="bg-emerald-400 text-slate-950 hover:bg-emerald-300"
      >
        {isBusy && pendingAction === "submit" ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Send className="mr-2 h-4 w-4" />
        )}
        Submit Samples
      </Button>
      <div className="ml-auto text-xs leading-5 text-slate-400">
        <p>Ctrl/Cmd + Enter runs the selected sample.</p>
        <p>Ctrl/Cmd + Shift + Enter submits all retrieved samples.</p>
      </div>
    </div>
  );

  const renderEditorSurface = () => (
    <div className="flex h-full min-h-0 flex-col gap-4 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <CardTitle className="text-xl text-slate-50">Workspace</CardTitle>
          <p className="mt-1 text-sm text-slate-400">
            Write your solution, pick a sample, and open results only when you are ready.
          </p>
        </div>

        <div className="ml-auto flex min-w-[240px] items-center gap-3">
          <Badge variant="outline" className="border-slate-700 bg-slate-900/70 text-slate-200">
            Sample {selectedSampleIndex + 1}
          </Badge>
          <Select
            value={selectedLanguage}
            onValueChange={(value) => setSelectedLanguage(value as "python" | "cpp" | "java" | "javascript")}
          >
            <SelectTrigger className="border-slate-700 bg-slate-900/80 text-slate-100">
              <SelectValue placeholder="Language" />
            </SelectTrigger>
            <SelectContent>
              {availableLanguages.map((language) => (
                <SelectItem key={language.slug} value={language.slug}>
                  {language.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid gap-3 rounded-[1.4rem] border border-white/10 bg-slate-900/45 p-3 sm:grid-cols-2">
        <div className="rounded-[1.2rem] border border-white/10 bg-slate-950/80 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Selected Input</p>
          <pre className="max-h-28 overflow-auto whitespace-pre-wrap font-mono text-xs leading-6 text-slate-200">
            {displayValue(codingRound.problem.samples[selectedSampleIndex]?.input)}
          </pre>
        </div>
        <div className="rounded-[1.2rem] border border-white/10 bg-slate-950/80 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Expected Output</p>
          <pre className="max-h-28 overflow-auto whitespace-pre-wrap font-mono text-xs leading-6 text-emerald-200">
            {displayValue(codingRound.problem.samples[selectedSampleIndex]?.output)}
          </pre>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col rounded-[1.6rem] border border-slate-800 bg-slate-950/92 p-1 shadow-inner shadow-slate-950/40">
        <Textarea
          value={activeCode}
          onChange={(event) => updateCode(event.target.value)}
          onKeyDown={handleEditorKeyDown}
          disabled={isBusy || isLocked}
          className="min-h-[340px] flex-1 resize-none border-0 bg-transparent px-4 py-4 font-mono text-sm leading-7 text-slate-100 placeholder:text-slate-500 focus-visible:ring-0 focus-visible:ring-offset-0"
          placeholder="Write your solution here."
        />
      </div>

      {renderActionBar()}

      {!shouldShowResultPanel && (
        <div className="rounded-[1.4rem] border border-dashed border-slate-700 bg-slate-900/35 px-4 py-3 text-sm leading-6 text-slate-300">
          The result console stays hidden until you run or submit. On desktop, you can drag the divider after it opens.
        </div>
      )}
    </div>
  );

  const renderResultSurface = () => (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-slate-800/70 px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-full bg-slate-900/80 p-2 text-slate-200">
            <TerminalSquare className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-50">Execution Console</h3>
            <p className="text-xs text-slate-400">Drag the handle to resize this panel after you run or submit.</p>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {isBusy && pendingAction && (
          <div className="mb-4 flex items-center gap-3 rounded-[1.3rem] border border-sky-400/20 bg-sky-400/10 px-4 py-3 text-sm text-sky-100">
            <Loader2 className="h-4 w-4 animate-spin" />
            {pendingAction === "submit"
              ? "Submitting the retrieved samples to Judge0..."
              : "Running the selected sample with Judge0..."}
          </div>
        )}

        {latestResult ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant={latestResult.passed ? "default" : "destructive"}
                className={latestResult.passed ? "bg-emerald-400 text-slate-950 hover:bg-emerald-400" : ""}
              >
                {latestResult.passed ? (
                  <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                ) : (
                  <XCircle className="mr-1 h-3.5 w-3.5" />
                )}
                {latestResult.verdict}
              </Badge>
              <Badge variant="outline" className="border-slate-700 bg-slate-900/60 text-slate-100">
                {latestResult.mode === "submit" ? "Final submit" : "Run sample"}
              </Badge>
              <span className="text-xs text-slate-400">
                Passed {latestResult.passed_samples}/{latestResult.total_samples} checked sample(s)
              </span>
            </div>

            {latestResult.sample_results.map((sampleResult, index) => (
              <Card
                key={`${sampleResult.sample_index}-${index}`}
                className="border-slate-800 bg-slate-900/60 text-slate-100"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    {sampleResult.passed ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                    ) : (
                      <XCircle className="h-4 w-4 text-rose-300" />
                    )}
                    <CardTitle className="text-sm">Example {sampleResult.sample_index + 1}</CardTitle>
                    <span className="ml-auto text-xs text-slate-400">{sampleResult.judge0_status}</span>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-3 lg:grid-cols-2">
                  <div>
                    <p className="mb-2 text-xs uppercase tracking-[0.16em] text-slate-400">Expected</p>
                    <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl bg-slate-950/85 p-4 font-mono text-xs leading-6 text-emerald-200">
                      {displayValue(sampleResult.expected_output)}
                    </pre>
                  </div>
                  <div>
                    <p className="mb-2 text-xs uppercase tracking-[0.16em] text-slate-400">Actual</p>
                    <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl bg-slate-950/85 p-4 font-mono text-xs leading-6 text-slate-100">
                      {displayValue(sampleResult.actual_output)}
                    </pre>
                  </div>

                  {(sampleResult.stderr || sampleResult.compile_output || sampleResult.message) && (
                    <div className="lg:col-span-2">
                      <p className="mb-2 text-xs uppercase tracking-[0.16em] text-slate-400">Diagnostics</p>
                      <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl bg-rose-950/40 p-4 font-mono text-xs leading-6 text-rose-100">
                        {displayValue(sampleResult.compile_output || sampleResult.stderr || sampleResult.message)}
                      </pre>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="rounded-[1.4rem] border border-dashed border-slate-700 bg-slate-900/45 px-4 py-3 text-sm leading-6 text-slate-300">
            Run a sample or submit to load the Judge0 output here.
          </div>
        )}
      </div>
    </div>
  );

  return (
    <section className="flex min-h-0 w-full flex-1 flex-col overflow-hidden border-t border-border/20 bg-[radial-gradient(circle_at_top,#1f2937,transparent_46%),linear-gradient(180deg,rgba(15,23,42,0.985),rgba(2,6,23,0.96))] text-slate-100">
      <div className="border-b border-slate-800/80 px-5 py-4 sm:px-6">
        <div className="flex flex-wrap items-start gap-3">
          <div className="flex items-center gap-3">
            <div className="rounded-[1.4rem] bg-amber-400/15 p-3 text-amber-200">
              <Code2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-slate-400">Coding Round</p>
              <h2 className="text-2xl font-semibold tracking-tight text-white">{codingRound.problem.title}</h2>
            </div>
          </div>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <Badge variant={ratingVariant} className="bg-amber-400/20 text-amber-100 hover:bg-amber-400/20">
              Rating {codingRound.problem.rating}
            </Badge>
            <Badge variant="outline" className="border-slate-700 bg-slate-900/60 text-slate-200">
              <Clock3 className="mr-1 h-3.5 w-3.5" />
              {formatCountdown(remainingSeconds)}
            </Badge>
            <Badge variant={statusVariant} className="border-slate-700 bg-slate-900/60 text-slate-100">
              {prettifyStatus(codingRound.status)}
            </Badge>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-300">
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
            Time limit: {codingRound.problem.time_limit}
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
            Memory limit: {codingRound.problem.memory_limit}
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
            Attempts left: {codingRound.attempts_left}/{codingRound.max_attempts}
          </span>
          <a
            href={codingRound.problem.source_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-full border border-amber-300/15 bg-amber-300/10 px-3 py-1.5 text-amber-100 hover:bg-amber-300/15"
          >
            Open original
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-5 p-4 lg:grid-cols-[minmax(340px,0.88fr)_minmax(480px,1.12fr)] lg:overflow-hidden sm:p-6">
        <Card className="min-h-0 border-slate-800/80 bg-slate-950/65 text-slate-100 shadow-2xl shadow-slate-950/30 lg:flex lg:flex-col">
          <CardHeader className="border-b border-slate-800/70 pb-4">
            <div className="flex items-center gap-3">
              <BookOpenText className="h-5 w-5 text-slate-300" />
              <CardTitle className="text-xl text-slate-50">Description</CardTitle>
            </div>
          </CardHeader>

          <CardContent className="space-y-6 p-5 lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
            <section className="space-y-3">
              <ProblemMarkdown content={codingRound.problem.statement} />
            </section>

            {codingRound.problem.input_spec && (
              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Input</h3>
                <ProblemMarkdown content={codingRound.problem.input_spec} />
              </section>
            )}

            {codingRound.problem.output_spec && (
              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Output</h3>
                <ProblemMarkdown content={codingRound.problem.output_spec} />
              </section>
            )}

            {codingRound.problem.samples.length > 0 && (
              <section className="space-y-4">
                <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Examples</h3>

                {codingRound.problem.samples.map((sample, index) => (
                  <article
                    key={`${sample.title}-${index}`}
                    className={cn(
                      "rounded-[1.4rem] border p-4 transition-colors",
                      selectedSampleIndex === index
                        ? "border-amber-300/35 bg-amber-300/10"
                        : "border-white/10 bg-white/5",
                    )}
                  >
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <h4 className="text-lg font-semibold text-white">Example {index + 1}</h4>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="border-slate-700 bg-slate-900/60 text-slate-100 hover:bg-slate-800"
                        onClick={() => setSelectedSampleIndex(index)}
                      >
                        Use For Run
                      </Button>
                    </div>

                    <div className="grid gap-3 xl:grid-cols-2">
                      <div className="space-y-2">
                        <p className="text-sm font-semibold text-slate-100">Input</p>
                        <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl bg-slate-950/90 p-4 font-mono text-xs leading-6 text-slate-200">
                          {displayValue(sample.input)}
                        </pre>
                      </div>

                      <div className="space-y-2">
                        <p className="text-sm font-semibold text-slate-100">Output</p>
                        <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl bg-slate-950/90 p-4 font-mono text-xs leading-6 text-emerald-200">
                          {displayValue(sample.output)}
                        </pre>
                      </div>
                    </div>
                  </article>
                ))}
              </section>
            )}

            {codingRound.problem.notes && (
              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Notes</h3>
                <ProblemMarkdown content={codingRound.problem.notes} />
              </section>
            )}

            {codingRound.problem.tags.length > 0 && (
              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {codingRound.problem.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="border-slate-700 bg-slate-900/70 text-slate-100">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </section>
            )}
          </CardContent>
        </Card>

        <Card className="min-h-0 border-slate-800/80 bg-slate-950/65 text-slate-100 shadow-2xl shadow-slate-950/30 lg:flex lg:flex-col">
          <CardContent className="flex min-h-0 flex-1 flex-col p-0">
            {shouldShowResultPanel ? (
              <>
                <div className="lg:hidden">
                  {renderEditorSurface()}
                  <div className="border-t border-slate-800/70">{renderResultSurface()}</div>
                </div>

                <div className="hidden min-h-0 flex-1 lg:flex">
                  <ResizablePanelGroup direction="vertical" className="min-h-0 flex-1">
                    <ResizablePanel defaultSize={62} minSize={42}>
                      {renderEditorSurface()}
                    </ResizablePanel>
                    <ResizableHandle withHandle className="bg-slate-800/70" />
                    <ResizablePanel defaultSize={38} minSize={24}>
                      {renderResultSurface()}
                    </ResizablePanel>
                  </ResizablePanelGroup>
                </div>
              </>
            ) : (
              renderEditorSurface()
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
