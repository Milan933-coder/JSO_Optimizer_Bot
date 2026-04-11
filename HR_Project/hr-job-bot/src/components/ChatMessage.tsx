import { useEffect, useState } from "react";

interface Message {
  id: string;
  role: "user" | "bot";
  content: string;
}

interface ChatMessageProps {
  message: Message;
}

const ChatMessage = ({ message }: ChatMessageProps) => {
  const [visibleLines, setVisibleLines] = useState<string[]>([]);
  const lines = message.content.split("\n").filter((l) => l.length > 0);

  useEffect(() => {
    if (message.role === "user") {
      setVisibleLines(lines);
      return;
    }

    // Line-by-line reveal for bot messages
    setVisibleLines([]);
    let i = 0;
    const timer = setInterval(() => {
      if (i < lines.length) {
        setVisibleLines((prev) => [...prev, lines[i]]);
        i++;
      } else {
        clearInterval(timer);
      }
    }, 120);

    return () => clearInterval(timer);
  }, [message.id]);

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-card border-l-2 border-primary px-4 py-3 rounded-md">
          <p className="text-sm text-foreground">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] bg-card px-4 py-3 rounded-md space-y-1">
        {visibleLines.map((line, idx) => (
          <p
            key={idx}
            className="text-sm text-foreground font-mono animate-line-fade-in"
            style={{ animationDelay: `${idx * 50}ms` }}
          >
            {line}
          </p>
        ))}
      </div>
    </div>
  );
};

export default ChatMessage;
