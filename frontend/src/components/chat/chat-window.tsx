import {
  AlertCircle,
  ArrowUpRight,
  BookOpenText,
  BriefcaseBusiness,
  RotateCcw,
  ShieldCheck,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import { AssistantMessage } from "@/components/chat/assistant-message";
import { BrandLogo } from "@/components/brand-logo";
import { ChatInput } from "@/components/chat/chat-input";
import { TypingIndicator } from "@/components/chat/typing-indicator";
import { UserMessage } from "@/components/chat/user-message";
import type { ChatMessage } from "@/components/chat/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ThemedScrollArea } from "@/components/ui/themed-scroll-area";
import type { SupportedLanguage } from "@/lib/languages";
import {
  getFriendlyApiError,
  streamLegalQuestion,
  type ConversationContextMessage,
} from "@/services/api";

const suggestions = [
  { icon: ShieldCheck, label: "What are my rights if an online seller refuses a refund?" },
  { icon: BriefcaseBusiness, label: "Can an employer terminate me without notice?" },
  { icon: BookOpenText, label: "How do I file an FIR?" },
];

const defaultDisclaimer =
  "This response is based solely on the supplied legal documents and is intended for informational purposes only. It is not legal advice.";

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function currentTime() {
  return new Date().toISOString();
}

function parseAnswer(answer: string) {
  const lines = answer.split(/\r?\n/);
  const normalizedHeading = (line: string) =>
    line
      .trim()
      .replace(/^#{1,6}\s*/, "")
      .replaceAll("*", "")
      .replace(/:$/, "")
      .trim()
      .toLowerCase();
  const sourcesIndex = lines.findIndex((line) => normalizedHeading(line) === "sources");
  const disclaimerIndex = lines.findIndex((line) => normalizedHeading(line) === "disclaimer");
  const contentEnd = [sourcesIndex, disclaimerIndex]
    .filter((index) => index >= 0)
    .reduce((lowest, index) => Math.min(lowest, index), lines.length);
  const body = lines.slice(0, contentEnd).join("\n").trim();
  const disclaimer =
    disclaimerIndex >= 0
      ? lines
          .slice(disclaimerIndex + 1)
          .join("\n")
          .trim()
      : defaultDisclaimer;

  return {
    paragraphs: body
      .split(/\n\s*\n/)
      .map((paragraph) => paragraph.trim())
      .filter(Boolean),
    disclaimer: disclaimer || defaultDisclaimer,
  };
}

interface ChatWindowProps {
  messages: ChatMessage[];
  onMessagesChange: (messages: ChatMessage[]) => void;
}

interface ChatError {
  message: string;
  question: string;
}

export function ChatWindow({ messages, onMessagesChange }: ChatWindowProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [language, setLanguage] = useState<SupportedLanguage>("en");
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState<ChatError | null>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const conversationEnd = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    conversationEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading, streamingText]);

  useEffect(
    () => () => {
      activeRequest.current?.abort();
    },
    [],
  );

  const sendMessage = async (question: string, appendUserMessage = true) => {
    if (isLoading) return;
    setError(null);
    setStreamingText("");
    const pendingMessages: ChatMessage[] = appendUserMessage
      ? [
          ...messages,
          { id: createMessageId(), role: "user", content: question, timestamp: currentTime() },
        ]
      : messages;
    onMessagesChange(pendingMessages);
    setIsLoading(true);
    const controller = new AbortController();
    activeRequest.current = controller;

    try {
      let accumulatedAnswer = "";
      const conversationContext: ConversationContextMessage[] = pendingMessages
        .slice(0, -1)
        .map((message) =>
          message.role === "user"
            ? { role: "user", content: message.content }
            : { role: "assistant", content: message.answer.join("\n\n") },
        );
      const response = await streamLegalQuestion(
        question,
        language,
        (delta) => {
          accumulatedAnswer += delta;
          setStreamingText(accumulatedAnswer);
        },
        controller.signal,
        conversationContext,
      );
      const parsed = parseAnswer(response.answer);
      onMessagesChange([
        ...pendingMessages,
        {
          id: createMessageId(),
          role: "assistant",
          answer: parsed.paragraphs,
          sources: response.sources.map((title) => ({ title })),
          disclaimer: parsed.disclaimer,
          timestamp: currentTime(),
          generationTime: response.generation_time,
          language: response.language,
          document: response.document,
          documentError: response.document_error,
        },
      ]);
    } catch (requestError) {
      if (!controller.signal.aborted) {
        setError({ message: getFriendlyApiError(requestError), question });
      }
    } finally {
      if (activeRequest.current === controller) activeRequest.current = null;
      setStreamingText("");
      setIsLoading(false);
    }
  };

  return (
    <Card
      className="relative flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-[24px] border border-white bg-white shadow-[0_18px_55px_-36px_rgba(15,55,50,0.25)]"
      aria-busy={isLoading}
    >
      <div className="pointer-events-none absolute left-1/3 top-0 h-24 w-1/2 rounded-full bg-teal-100/45 blur-3xl" />
      <ThemedScrollArea
        className="flex-1"
        viewportClassName="px-4 py-5 scroll-smooth sm:px-7 sm:py-6"
        ariaLive="polite"
      >
        <AnimatePresence mode="wait">
          {messages.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mx-auto flex min-h-[360px] max-w-3xl flex-col items-center justify-center py-8 text-center"
            >
              <BrandLogo className="size-14 rounded-3xl bg-[#dff2ea] text-[#236f5f] shadow-sm" />
              <h2 className="mt-6 max-w-2xl text-balance text-3xl font-semibold tracking-[-0.04em] text-slate-900 sm:text-4xl">
                Welcome to JuriGPT
              </h2>
              <p className="mt-3 max-w-lg text-base font-medium leading-6 text-slate-600">
                Your AI-powered Legal Assistant
              </p>
              <p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">
                Ask a legal question to begin.
              </p>
              <div className="mt-8 grid w-full gap-2.5 sm:grid-cols-3 sm:gap-3">
                {suggestions.map(({ icon: Icon, label }) => (
                  <button
                    key={label}
                    type="button"
                    onClick={() => void sendMessage(label)}
                    disabled={isLoading}
                    className="group flex items-center gap-3 rounded-2xl border border-stone-200/80 bg-white p-3.5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-teal-200 hover:shadow-float active:translate-y-0 disabled:pointer-events-none disabled:opacity-50 sm:min-h-32 sm:flex-col sm:items-start sm:justify-between sm:p-4"
                  >
                    <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-[#dff2ea] text-[#2d7b69] transition-colors group-hover:bg-[#cdeade] sm:size-10">
                      <Icon className="size-5" strokeWidth={1.7} />
                    </span>
                    <span className="min-w-0 flex-1 text-sm font-medium leading-5 text-slate-600 group-hover:text-slate-900 sm:mt-4 sm:flex-none sm:text-xs">
                      {label}
                    </span>
                    <ArrowUpRight className="size-4 shrink-0 text-slate-300 transition-colors group-hover:text-teal-600 sm:hidden" />
                  </button>
                ))}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="conversation"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mx-auto max-w-3xl space-y-7"
            >
              <p className="pb-1 text-center text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                Today
              </p>
              <AnimatePresence initial={false}>
                {messages.map((message) => (
                  <motion.div
                    key={message.id}
                    id={message.role === "user" ? `message-${message.id}` : undefined}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="scroll-m-24"
                  >
                    {message.role === "user" ? (
                      <UserMessage
                        key={message.id}
                        message={message.content}
                        timestamp={message.timestamp}
                      />
                    ) : (
                      <AssistantMessage
                        key={message.id}
                        answer={message.answer}
                        sources={message.sources}
                        disclaimer={message.disclaimer}
                        timestamp={message.timestamp}
                        generationTime={message.generationTime}
                        document={message.document}
                        documentError={message.documentError}
                      />
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
              {isLoading && streamingText ? (
                <AssistantMessage
                  answer={[streamingText]}
                  sources={[]}
                  disclaimer=""
                  timestamp={currentTime()}
                  isStreaming
                />
              ) : null}
              {isLoading && !streamingText ? <TypingIndicator /> : null}
              <div ref={conversationEnd} />
            </motion.div>
          )}
        </AnimatePresence>
      </ThemedScrollArea>

      <footer className="relative border-t border-stone-100/80 bg-white/95 p-4 backdrop-blur sm:px-6 sm:py-5">
        <AnimatePresence>
          {error ? (
            <motion.div
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 3 }}
              className="mx-auto mb-3 flex min-h-16 max-w-3xl items-center gap-3 rounded-2xl border border-rose-100 bg-rose-50 px-5 py-3 text-xs text-rose-700"
              role="alert"
            >
              <AlertCircle className="size-4 shrink-0" />
              <span className="min-w-0 flex-1 break-words leading-5">{error.message}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => void sendMessage(error.question, false)}
                className="h-7 shrink-0 gap-1.5 px-2.5 text-[11px] text-rose-700 hover:bg-rose-100"
              >
                <RotateCcw className="size-3" /> Retry
              </Button>
              <button
                type="button"
                onClick={() => setError(null)}
                aria-label="Dismiss error"
                className="shrink-0 rounded-md p-1 hover:bg-rose-100"
              >
                <X className="size-4" />
              </button>
            </motion.div>
          ) : null}
        </AnimatePresence>
        <ChatInput
          onSend={(message) => void sendMessage(message)}
          disabled={isLoading}
          language={language}
          onLanguageChange={setLanguage}
        />
      </footer>
    </Card>
  );
}
