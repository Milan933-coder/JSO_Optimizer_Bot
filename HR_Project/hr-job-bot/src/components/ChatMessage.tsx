interface Message {
  id: string;
  role: "user" | "bot";
  content: string;
}

interface ChatMessageProps {
  message: Message;
}

const ChatMessage = ({ message }: ChatMessageProps) => {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl border border-primary/15 bg-primary px-4 py-3 text-primary-foreground shadow-sm">
          <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl border border-border bg-card px-4 py-3 shadow-sm">
        <p className="whitespace-pre-wrap text-sm leading-6 text-foreground">{message.content}</p>
      </div>
    </div>
  );
};

export default ChatMessage;
