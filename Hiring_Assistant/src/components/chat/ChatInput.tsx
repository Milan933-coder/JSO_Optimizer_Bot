import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FileText, ImagePlus, Mic, Send, Square, X } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void | Promise<void>;
  onSendVoice?: (audioBlob: Blob) => Promise<void>;
  onSendCv?: (cvFile: File) => Promise<void>;
  disabled?: boolean;
}

function getSupportedAudioMimeType(): string {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
  ];
  for (const type of candidates) {
    if (MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return "";
}

function isSupportedCvFile(file: File): boolean {
  const type = file.type.toLowerCase();
  return type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

export function ChatInput({ onSend, onSendVoice, onSendCv, disabled }: ChatInputProps) {
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [cvFile, setCvFile] = useState<File | null>(null);

  const fileRef = useRef<HTMLInputElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const stopStream = () => {
    if (!streamRef.current) return;
    for (const track of streamRef.current.getTracks()) {
      track.stop();
    }
    streamRef.current = null;
  };

  useEffect(() => {
    return () => {
      if (recorderRef.current && recorderRef.current.state !== "inactive") {
        recorderRef.current.stop();
      }
      stopStream();
    };
  }, []);

  const clearCvSelection = () => {
    setCvFile(null);
  };

  const handleFile = (file: File) => {
    if (!isSupportedCvFile(file)) return;
    setCvFile(file);
  };

  const handleSend = async () => {
    const msg = text.trim();
    if (!msg && !cvFile) return;

    if (cvFile && onSendCv) {
      await onSendCv(cvFile);
      clearCvSelection();
    }

    if (msg) {
      await onSend(msg);
      setText("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const startRecording = async () => {
    if (disabled || !onSendVoice || isRecording) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = getSupportedAudioMimeType();
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const audioType = recorder.mimeType || "audio/webm";
        const audioBlob = new Blob(chunksRef.current, { type: audioType });
        chunksRef.current = [];
        setIsRecording(false);
        recorderRef.current = null;
        stopStream();

        if (audioBlob.size > 0) {
          await onSendVoice(audioBlob);
        }
      };

      recorder.start();
      recorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      setIsRecording(false);
      stopStream();
    }
  };

  const stopRecording = () => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      setIsRecording(false);
      stopStream();
      return;
    }
    recorder.stop();
  };

  return (
    <div
      className="border-t border-border/20 bg-card/30 px-4 py-3 backdrop-blur-xl"
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
    >
      {cvFile && (
        <div className="mb-2 flex items-start gap-2">
          <div className="relative">
            <div className="flex h-20 w-44 items-center gap-2 rounded-lg border border-border/30 bg-background/50 px-3 text-xs text-muted-foreground">
              <FileText className="h-4 w-4" />
              <span className="truncate">{cvFile.name}</span>
            </div>
            <button
              onClick={clearCvSelection}
              className="absolute -right-2 -top-2 rounded-full bg-destructive p-0.5 text-destructive-foreground shadow"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        </div>
      )}

      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => fileRef.current?.click()}
          className="shrink-0 text-muted-foreground hover:text-foreground"
          disabled={disabled}
          title="Upload CV (PDF)"
        >
          <ImagePlus className="h-5 w-5" />
        </Button>

        <Button
          variant={isRecording ? "destructive" : "ghost"}
          size="icon"
          onClick={isRecording ? stopRecording : startRecording}
          className={`shrink-0 ${isRecording ? "animate-pulse" : "text-muted-foreground hover:text-foreground"}`}
          disabled={isRecording ? false : (disabled || !onSendVoice)}
          title={isRecording ? "Stop recording" : "Record voice message"}
        >
          {isRecording ? <Square className="h-4 w-4" /> : <Mic className="h-5 w-5" />}
        </Button>

        <input
          ref={fileRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
            e.target.value = "";
          }}
        />

        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isRecording
              ? "Recording... click stop to send voice."
              : "Type a message, ask recommendations with GitHub link, or upload CV (PDF)."
          }
          disabled={disabled || isRecording}
          rows={1}
          className="max-h-32 min-h-[2.5rem] flex-1 resize-none border-border/30 bg-background/40 text-sm placeholder:text-muted-foreground/60"
        />

        <Button
          size="icon"
          onClick={() => void handleSend()}
          disabled={disabled || isRecording || (!text.trim() && !cvFile)}
          className="shrink-0"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
