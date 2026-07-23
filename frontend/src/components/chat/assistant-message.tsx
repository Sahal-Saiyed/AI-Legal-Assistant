import { Check, Clock3, Copy, ShieldCheck } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { memo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { BotAvatar } from "@/components/chat/bot-avatar";
import type { GeneratedDocument, MessageSource } from "@/components/chat/types";
import { MessageBubble } from "@/components/chat/message-bubble";
import { GeneratedDocumentCard } from "@/components/chat/generated-document-card";
import { MessageTimestamp } from "@/components/chat/message-timestamp";
import { SourceCard } from "@/components/chat/source-card";

interface AssistantMessageProps {
  answer: string[];
  sources: MessageSource[];
  disclaimer: string;
  timestamp: string;
  generationTime?: number;
  isStreaming?: boolean;
  document?: GeneratedDocument | null;
  documentError?: string | null;
}

export const AssistantMessage = memo(function AssistantMessage({
  answer,
  sources,
  disclaimer,
  timestamp,
  generationTime,
  isStreaming = false,
  document,
  documentError,
}: AssistantMessageProps) {
  const [copied, setCopied] = useState(false);
  const answerText = answer.join("\n\n");

  const copyResponse = async () => {
    const sourceText = sources.length
      ? `\n\nSources\n${sources.map((source) => `- ${source.title}`).join("\n")}`
      : "";
    const text = `${answerText}${sourceText}\n\nDisclaimer\n${disclaimer}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.08 }}
      className="flex items-start gap-3"
      aria-label="JuriGPT response"
    >
      <BotAvatar className="mt-1 hidden sm:grid" />
      <div className="min-w-0 flex-1">
        <MessageBubble variant="assistant">
          <div className="markdown-response">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ children, href }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-teal-700 underline decoration-teal-300 underline-offset-2"
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {answerText}
            </ReactMarkdown>
            {isStreaming ? (
              <motion.span
                className="ml-1 inline-block h-4 w-0.5 rounded-full bg-teal-600 align-middle"
                animate={{ opacity: [0.2, 1, 0.2] }}
                transition={{ duration: 0.8, repeat: Infinity }}
                aria-hidden="true"
              />
            ) : null}
          </div>

          {!isStreaming && sources.length > 0 ? (
            <section className="mt-6 border-t border-stone-100 pt-5" aria-label="Sources">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="text-xs font-semibold uppercase tracking-[0.13em] text-slate-500">
                  Sources
                </h3>
                {generationTime !== undefined ? (
                  <span className="flex items-center gap-1.5 text-[10px] font-medium text-slate-400">
                    <Clock3 className="size-3" /> {generationTime.toFixed(2)} sec
                  </span>
                ) : null}
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {sources.map((source) => (
                  <SourceCard key={source.title} {...source} />
                ))}
              </div>
            </section>
          ) : !isStreaming && generationTime !== undefined ? (
            <div className="mt-5 flex items-center gap-1.5 text-[10px] font-medium text-slate-400">
              <Clock3 className="size-3" /> Generated in {generationTime.toFixed(2)} sec
            </div>
          ) : null}

          {!isStreaming && document ? <GeneratedDocumentCard document={document} /> : null}
          {!isStreaming && documentError ? (
            <p className="mt-4 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-[10px] leading-4 text-amber-800">
              {documentError}
            </p>
          ) : null}

          {!isStreaming ? (
            <section className="mt-5 rounded-2xl bg-stone-50 p-4" aria-label="Disclaimer">
              <div className="flex items-start gap-2.5">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-[#438172]" strokeWidth={1.7} />
                <div>
                  <h3 className="text-[10px] font-semibold uppercase tracking-[0.13em] text-slate-500">
                    Disclaimer
                  </h3>
                  <p className="mt-1.5 text-[11px] leading-5 text-slate-500">{disclaimer}</p>
                </div>
              </div>
            </section>
          ) : null}

          {!isStreaming ? (
            <div className="mt-3 flex justify-end border-t border-stone-100 pt-3">
              <motion.button
                type="button"
                whileHover={{ y: -1 }}
                whileTap={{ scale: 0.96 }}
                onClick={() => void copyResponse()}
                className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-[10px] font-medium text-slate-400 transition hover:bg-teal-50 hover:text-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
                aria-label="Copy response"
              >
                <AnimatePresence mode="wait" initial={false}>
                  <motion.span
                    key={copied ? "copied" : "copy"}
                    initial={{ opacity: 0, y: 3 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -3 }}
                    className="flex items-center gap-1.5"
                  >
                    {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                    {copied ? "Copied" : "Copy response"}
                  </motion.span>
                </AnimatePresence>
              </motion.button>
            </div>
          ) : null}
        </MessageBubble>
        <MessageTimestamp value={timestamp} className="ml-3 mt-2 block" />
      </div>
    </motion.article>
  );
});
