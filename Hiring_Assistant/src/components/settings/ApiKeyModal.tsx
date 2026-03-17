import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ProviderConfig } from "@/types/chat";
import { Check } from "lucide-react";

interface ApiKeyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  provider: ProviderConfig;
  currentKey: string;
  onSave: (key: string) => void;
}

export function ApiKeyModal({
  open,
  onOpenChange,
  provider,
  currentKey,
  onSave,
}: ApiKeyModalProps) {
  const [key, setKey] = useState(currentKey);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    onSave(key);
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onOpenChange(false);
    }, 800);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border/40 bg-card/95 backdrop-blur-xl sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-foreground">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ backgroundColor: provider.color }}
            />
            {provider.name} API Key
          </DialogTitle>
          <DialogDescription>
            Your key is stored in memory only and will be cleared on refresh.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <Label htmlFor="api-key" className="text-muted-foreground">
            API Key
          </Label>
          <Input
            id="api-key"
            type="password"
            placeholder={provider.placeholder}
            value={key}
            onChange={(e) => setKey(e.target.value)}
            className="border-border/40 bg-background/60 font-mono text-sm"
          />
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!key.trim()}>
            {saved ? (
              <span className="flex items-center gap-1">
                <Check className="h-4 w-4" /> Saved
              </span>
            ) : (
              "Save Key"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
