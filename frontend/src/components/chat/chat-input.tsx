import { ArrowUp } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { LanguageSelector } from "@/components/chat/language-selector";
import type { SupportedLanguage } from "@/lib/languages";

interface ChatInputProps {
  onSend?: (message: string) => void;
  disabled?: boolean;
  language: SupportedLanguage;
  onLanguageChange: (language: SupportedLanguage) => void;
}

export function ChatInput({
  onSend,
  disabled = false,
  language,
  onLanguageChange,
}: ChatInputProps) {
  const [message, setMessage] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 128)}px`;
  }, [message]);

  const submit = () => {
    const normalized = message.trim();
    if (!normalized || disabled) return;
    onSend?.(normalized);
    setMessage("");
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Escape") {
      event.currentTarget.blur();
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto w-full max-w-3xl">
      <div className="flex items-end gap-1.5 rounded-[26px] border border-stone-200/80 bg-white p-2 pl-2.5 shadow-float transition-[border-color,box-shadow] duration-200 focus-within:border-[#8bbcaf] focus-within:shadow-soft sm:gap-2 sm:p-2.5 sm:pl-3">
        <LanguageSelector
          value={language}
          onChange={onLanguageChange}
          disabled={disabled}
          className="self-end"
        />
        <textarea
          ref={inputRef}
          id="legal-question-input"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a legal question…"
          rows={1}
          disabled={disabled}
          maxLength={4000}
          aria-describedby="legal-question-hint"
          className="max-h-32 min-h-10 min-w-0 flex-1 resize-none self-end overflow-y-auto bg-transparent px-1 py-2.5 text-sm leading-5 text-slate-700 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label="Legal question"
        />
        <Button
          type="submit"
          size="icon"
          disabled={disabled || !message.trim()}
          aria-label="Send question"
          className="shrink-0 self-end"
        >
          <ArrowUp className="size-4" />
        </Button>
      </div>
      <p
        id="legal-question-hint"
        className="mt-2.5 text-center text-[10px] leading-4 text-slate-400"
      >
        JuriGPT provides legal information, not legal advice.
        <span className="ml-1 hidden sm:inline">Enter to send | Shift + Enter for a new line</span>
      </p>
    </form>
  );
}
