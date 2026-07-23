import { FileText } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

import { LegalResourceModal, type LegalResource } from "@/components/legal-resource-modal";
import type { MessageSource } from "@/components/chat/types";

export function SourceCard({ title, category }: MessageSource) {
  const [selectedResource, setSelectedResource] = useState<LegalResource | null>(null);

  return (
    <>
      <motion.button
        type="button"
        whileHover={{ y: -2 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setSelectedResource({ title, category })}
        className="flex min-w-0 items-center gap-3 rounded-2xl border border-[#deebe6] bg-[#f5faf8] p-3.5 text-left transition-colors hover:border-[#c8dfd7] hover:bg-[#edf7f3] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
        aria-label={`Open ${title}`}
      >
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-white text-[#2c7968] shadow-sm">
          <FileText className="size-4" strokeWidth={1.7} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-xs font-semibold text-slate-700">{title}</span>
          {category ? (
            <span className="mt-0.5 block text-[10px] capitalize text-slate-400">
              {category.replaceAll("_", " ")}
            </span>
          ) : null}
        </span>
      </motion.button>
      <LegalResourceModal resource={selectedResource} onClose={() => setSelectedResource(null)} />
    </>
  );
}
