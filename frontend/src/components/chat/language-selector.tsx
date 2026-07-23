import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown, Languages } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { SUPPORTED_LANGUAGES, type SupportedLanguage } from "@/lib/languages";
import { cn } from "@/lib/utils";
import { ThemedScrollArea } from "@/components/ui/themed-scroll-area";

interface LanguageSelectorProps {
  value: SupportedLanguage;
  onChange: (language: SupportedLanguage) => void;
  disabled?: boolean;
  className?: string;
  showIcon?: boolean;
}

export function LanguageSelector({
  value,
  onChange,
  disabled = false,
  className,
  showIcon = true,
}: LanguageSelectorProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const selectedIndex = SUPPORTED_LANGUAGES.findIndex((language) => language.code === value);
  const selectedLanguage = SUPPORTED_LANGUAGES[selectedIndex] ?? SUPPORTED_LANGUAGES[0];

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      triggerRef.current?.focus();
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    requestAnimationFrame(() => optionRefs.current[selectedIndex]?.focus());
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open, selectedIndex]);

  const selectLanguage = (language: SupportedLanguage) => {
    onChange(language);
    setOpen(false);
    requestAnimationFrame(() => triggerRef.current?.focus());
  };

  const focusAdjacentOption = (currentIndex: number, direction: 1 | -1) => {
    const nextIndex =
      (currentIndex + direction + SUPPORTED_LANGUAGES.length) % SUPPORTED_LANGUAGES.length;
    optionRefs.current[nextIndex]?.focus();
  };

  return (
    <div ref={containerRef} className={cn("relative inline-flex w-fit shrink-0", className)}>
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Response language: ${selectedLanguage.label}`}
        title="Response language"
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true);
          }
        }}
        className="inline-flex h-9 w-auto items-center gap-1.5 whitespace-nowrap rounded-xl border border-teal-100/80 bg-teal-50 px-2.5 text-[10px] font-semibold text-teal-800 shadow-sm transition hover:border-teal-200 hover:bg-teal-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {showIcon ? <Languages className="size-3.5 shrink-0 text-teal-700" /> : null}
        <span>{selectedLanguage.nativeLabel}</span>
        <ChevronDown className={cn("size-3 shrink-0 transition-transform", open && "rotate-180")} />
      </button>

      <AnimatePresence>
        {open ? (
          <motion.div
            role="listbox"
            aria-label="Response language"
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 5, scale: 0.98 }}
            transition={{ duration: 0.16, ease: "easeOut" }}
            className="absolute bottom-full left-0 z-50 mb-2 w-56 overflow-hidden rounded-2xl border border-teal-100 bg-white/95 p-1.5 shadow-[0_22px_55px_-24px_rgba(15,70,62,0.45)] backdrop-blur-xl"
          >
            <ThemedScrollArea className="h-64" viewportClassName="space-y-0.5 pr-3">
              {SUPPORTED_LANGUAGES.map((language, index) => {
                const selected = language.code === value;
                return (
                  <button
                    key={language.code}
                    ref={(element) => {
                      optionRefs.current[index] = element;
                    }}
                    type="button"
                    role="option"
                    aria-selected={selected}
                    onClick={() => selectLanguage(language.code)}
                    onKeyDown={(event) => {
                      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                        event.preventDefault();
                        focusAdjacentOption(index, event.key === "ArrowDown" ? 1 : -1);
                      }
                      if (event.key === "Home") {
                        event.preventDefault();
                        optionRefs.current[0]?.focus();
                      }
                      if (event.key === "End") {
                        event.preventDefault();
                        optionRefs.current[SUPPORTED_LANGUAGES.length - 1]?.focus();
                      }
                    }}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600",
                      selected
                        ? "bg-teal-50 text-teal-900"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                    )}
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block text-xs font-semibold">{language.nativeLabel}</span>
                      {language.nativeLabel !== language.label ? (
                        <span className="mt-0.5 block text-[9px] text-slate-400">
                          {language.label}
                        </span>
                      ) : null}
                    </span>
                    {selected ? <Check className="size-3.5 shrink-0 text-teal-700" /> : null}
                  </button>
                );
              })}
            </ThemedScrollArea>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
