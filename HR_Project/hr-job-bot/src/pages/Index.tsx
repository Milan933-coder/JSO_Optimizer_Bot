import { useState, useRef, useEffect, useCallback } from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";
import ChatMessage from "@/components/ChatMessage";
import LoadingSpinner from "@/components/LoadingSpinner";

interface Message {
  id: string;
  role: "user" | "bot";
  content: string;
}

const formatResponse = (data: any) => {
  if (!data) return "No response from server.";
  if (data.error) return `Error: ${data.error}`;

  const lines: string[] = [];
  const qtype = data.query_type;

  if (qtype === "sql" || qtype === "stats") {
    if (data.explanation) lines.push(data.explanation);
    if (data.generated_sql) lines.push(`SQL: ${data.generated_sql}`);
    if (Array.isArray(data.rows) && data.rows.length > 0) {
      const columns = Array.isArray(data.columns) && data.columns.length
        ? data.columns
        : Object.keys(data.rows[0] ?? {});
      if (columns.length) {
        lines.push(columns.join(" | "));
        for (const row of data.rows.slice(0, 10)) {
          const rowLine = columns.map((c: string) => String(row?.[c] ?? "")).join(" | ");
          lines.push(rowLine);
        }
        if (data.rows.length > 10) lines.push(`...and ${data.rows.length - 10} more rows`);
      }
    } else if (typeof data.row_count === "number") {
      lines.push(`Rows found: ${data.row_count}`);
    }
  } else if (qtype === "semantic" || qtype === "hybrid") {
    if (data.summary) lines.push(data.summary);
    const candidates = Array.isArray(data.candidates) ? data.candidates : [];
    lines.push(`Found ${data.total_found ?? candidates.length} candidates`);
    for (const c of candidates.slice(0, 10)) {
      lines.push(
        `${c.full_name ?? "Candidate"} | Match: ${c.match_percent ?? "N/A"} | Exp: ${c.experience_years ?? "?"}yr | Location: ${c.location ?? "N/A"}`
      );
    }
    if (candidates.length > 10) lines.push(`...and ${candidates.length - 10} more candidates`);
  } else if (qtype === "compare") {
    lines.push("Candidate comparison:");
    const table = Array.isArray(data.comparison_table) ? data.comparison_table : [];
    for (const c of table) {
      lines.push(
        `${c.full_name ?? "Candidate"} | Match: ${c.match_percent ?? "N/A"} | Exp: ${c.experience_years ?? "?"}yr | GitHub: ${c.github_score ?? "?"}/10`
      );
    }
    if (data.recommendation) lines.push(`Recommendation: ${data.recommendation}`);
  } else if (qtype === "explain") {
    if (data.full_name) lines.push(`Candidate: ${data.full_name}`);
    if (data.briefing) lines.push(data.briefing);
    if (Array.isArray(data.skills) && data.skills.length) {
      lines.push(`Skills: ${data.skills.slice(0, 8).join(", ")}`);
    }
  }

  if (lines.length) return lines.join("\n");
  return typeof data === "string" ? data : JSON.stringify(data, null, 2);
};

const Index = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Check backend connectivity
  useEffect(() => {
    const check = async () => {
      try {
        await fetch("http://localhost:8000", { method: "HEAD", signal: AbortSignal.timeout(3000) });
        setIsConnected(true);
      } catch {
        setIsConnected(false);
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const sendMessage = useCallback(async () => {
    const query = input.trim();
    if (!query || isLoading) return;

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const data = await res.json();
      const responseText = formatResponse(data);

      const botMsg: Message = { id: crypto.randomUUID(), role: "bot", content: responseText };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      toast.error("Failed to reach backend. Is your server running on localhost:8000?");
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "bot",
        content: "⚠ Unable to connect to the backend. Please ensure the server is running on localhost:8000.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }, [input, isLoading]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-card">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold tracking-tight text-foreground">
            JD Query Pro
          </h1>
          <span className="text-xs text-muted-foreground font-mono">NL-SQL</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-primary"}`}
          />
          <span className="text-xs text-muted-foreground">
            {isConnected ? "Connected" : "Offline"}
          </span>
        </div>
      </header>

      {/* Chat Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-4">
              <div className="w-16 h-16 rounded-lg bg-primary/10 flex items-center justify-center">
                <span className="text-2xl font-bold text-primary font-mono">&gt;_</span>
              </div>
              <h2 className="text-xl font-semibold text-foreground">JD Query Pro</h2>
              <p className="text-muted-foreground text-sm max-w-md">
                Ask natural language questions to find relevant Job Descriptions from the HR database.
              </p>
              <div className="flex flex-wrap gap-2 justify-center mt-4">
                {[
                  "Find senior software engineer roles",
                  "Show JDs with Python requirement",
                  "List remote marketing positions",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      setInput(suggestion);
                      inputRef.current?.focus();
                    }}
                    className="text-xs px-3 py-1.5 rounded-md border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {isLoading && <LoadingSpinner />}
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-border bg-card p-4">
        <div className="max-w-3xl mx-auto flex gap-3">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about job descriptions..."
            disabled={isLoading}
            className="flex-1 bg-secondary text-foreground placeholder:text-muted-foreground px-4 py-3 rounded-md border border-border focus:outline-none focus:ring-1 focus:ring-primary text-sm font-sans disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="px-4 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Index;
