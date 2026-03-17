import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "@/types/chat";
import { Bot, User } from "lucide-react";

interface MessageBubbleProps {
  message: ChatMessage;
}

function stripVisibleQuestionLabels(text: string): string {
  return (text || "")
    .replace(/\*\*Question\s*\d+\s*\/\s*\d+\s*:\*\*/gi, "")
    .replace(/\*\*Question\s*\d+\s*:\*\*/gi, "")
    .replace(/(?:^|\n)Question\s*\d+\s*\/\s*\d+\s*:\s*/gi, "\n")
    .replace(/\n\s*---\s*\n/g, "\n\n")
    .trim();
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const cleanAssistantContent = isUser ? message.content : stripVisibleQuestionLabels(message.content);

  return (
    <div
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser
            ? "bg-primary/20 text-primary"
            : "bg-accent text-accent-foreground"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Content */}
      <div
        className={`max-w-[75%] space-y-2 rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-primary text-primary-foreground rounded-br-md"
            : "bg-card/80 text-foreground border border-border/30 rounded-bl-md"
        }`}
      >
        {message.image && (
          <img
            src={message.image}
            alt="Uploaded CV"
            className="max-h-48 rounded-lg object-contain"
          />
        )}
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{cleanAssistantContent}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
