import { AnimatePresence, motion } from "framer-motion";
import { BookOpenText, FileText, X } from "lucide-react";
import { useEffect } from "react";
import { createPortal } from "react-dom";

export interface LegalResource {
  title: string;
  category?: string;
  description?: string;
}

interface LegalResourceModalProps {
  resource: LegalResource | null;
  onClose: () => void;
}

export function LegalResourceModal({ resource, onClose }: LegalResourceModalProps) {
  useEffect(() => {
    if (!resource) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose, resource]);

  return createPortal(
    <AnimatePresence>
      {resource ? (
        <motion.div
          className="fixed inset-0 z-[80] grid place-items-center bg-slate-950/45 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          role="presentation"
          onMouseDown={(event) => {
            if (event.currentTarget === event.target) onClose();
          }}
        >
          <motion.section
            role="dialog"
            aria-modal="true"
            aria-labelledby="resource-modal-title"
            initial={{ opacity: 0, y: 18, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 360, damping: 30 }}
            className="w-full max-w-lg overflow-hidden rounded-3xl border border-white/70 bg-white shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4 bg-gradient-to-br from-[#e6f5f0] to-white p-6">
              <div className="flex min-w-0 items-center gap-4">
                <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-[#d6eee6] text-[#236f5f]">
                  <BookOpenText className="size-5" />
                </span>
                <div className="min-w-0">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-700">
                    Legal resource
                  </p>
                  <h2
                    id="resource-modal-title"
                    className="mt-1 text-xl font-semibold text-slate-950"
                  >
                    {resource.title}
                  </h2>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="grid size-9 shrink-0 place-items-center rounded-full text-slate-500 transition hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
                aria-label="Close resource"
              >
                <X className="size-4" />
              </button>
            </div>
            <div className="p-6">
              {resource.category ? (
                <span className="inline-flex rounded-full bg-teal-50 px-3 py-1 text-[10px] font-semibold capitalize text-teal-700">
                  {resource.category.replaceAll("_", " ")}
                </span>
              ) : null}
              <p className="mt-4 text-sm leading-6 text-slate-600">
                {resource.description ??
                  "This source is part of JuriGPT's trusted legal knowledge base and may be used to ground legal answers."}
              </p>
              <div className="mt-5 flex items-start gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4 text-xs leading-5 text-slate-500">
                <FileText className="mt-0.5 size-4 shrink-0 text-teal-700" />
                Full document viewing will be available when the backend exposes a secure document
                endpoint.
              </div>
            </div>
          </motion.section>
        </motion.div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}
