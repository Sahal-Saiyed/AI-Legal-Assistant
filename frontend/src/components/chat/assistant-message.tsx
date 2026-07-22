import { Clock3, Scale, ShieldCheck } from "lucide-react";
import { motion } from "framer-motion";

import { MessageBubble } from "@/components/chat/message-bubble";
import { MessageTimestamp } from "@/components/chat/message-timestamp";
import { SourceCard } from "@/components/chat/source-card";

export interface MessageSource {
  title: string;
  category?: string;
}

interface AssistantMessageProps {
  answer: string[];
  sources: MessageSource[];
  disclaimer: string;
  timestamp: string;
  generationTime?: number;
}

export function AssistantMessage({
  answer,
  sources,
  disclaimer,
  timestamp,
  generationTime,
}: AssistantMessageProps) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.08 }}
      className="flex items-start gap-3"
      aria-label="JuriGPT response"
    >
      <span className="mt-1 hidden size-9 shrink-0 place-items-center rounded-2xl bg-[#dff2ea] text-[#236f5f] shadow-sm sm:grid">
        <Scale className="size-4" strokeWidth={1.8} />
      </span>
      <div className="min-w-0 flex-1">
        <MessageBubble variant="assistant">
          <div className="space-y-3.5">
            {answer.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>

          {sources.length > 0 ? (
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
          ) : generationTime !== undefined ? (
            <div className="mt-5 flex items-center gap-1.5 text-[10px] font-medium text-slate-400">
              <Clock3 className="size-3" /> Generated in {generationTime.toFixed(2)} sec
            </div>
          ) : null}

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
        </MessageBubble>
        <MessageTimestamp value={timestamp} className="ml-3 mt-2 block" />
      </div>
    </motion.article>
  );
}
