import { CheckCircle2, Download, FileText, LoaderCircle } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

import type { GeneratedDocument } from "@/components/chat/types";
import { downloadGeneratedDocument } from "@/services/api";

interface GeneratedDocumentCardProps {
  document: GeneratedDocument;
}

export function GeneratedDocumentCard({ document }: GeneratedDocumentCardProps) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const download = async () => {
    setDownloading(true);
    setError(null);
    try {
      await downloadGeneratedDocument(document);
    } catch (downloadError) {
      setError(
        downloadError instanceof Error
          ? downloadError.message
          : "The generated PDF could not be downloaded.",
      );
    } finally {
      setDownloading(false);
    }
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-5 overflow-hidden rounded-2xl border border-teal-100 bg-gradient-to-br from-teal-50 to-white"
      aria-label="Generated legal document"
    >
      <button
        type="button"
        onClick={() => void download()}
        disabled={downloading}
        className="flex w-full items-center gap-3 p-4 text-left transition hover:bg-teal-50/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-600 disabled:opacity-70"
      >
        <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-teal-700 text-white shadow-sm">
          <FileText className="size-5" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.13em] text-teal-700">
            <CheckCircle2 className="size-3.5" />
            Generated PDF
          </span>
          <span className="mt-1 block truncate text-xs font-semibold text-slate-800">
            {document.filename}
          </span>
          <span className="mt-0.5 block text-[10px] text-slate-500">
            {document.document_type} · {Math.max(1, Math.round(document.size_bytes / 1024))} KB
          </span>
        </span>
        {downloading ? (
          <LoaderCircle className="size-4 animate-spin text-teal-700" />
        ) : (
          <Download className="size-4 text-teal-700" />
        )}
      </button>
      {error ? (
        <p className="border-t border-rose-100 bg-rose-50 px-4 py-2 text-[10px] text-rose-700">
          {error}
        </p>
      ) : null}
    </motion.section>
  );
}
