import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, X } from "lucide-react";
import { useEffect } from "react";
import { createPortal } from "react-dom";

interface SuccessToastProps {
  open: boolean;
  message: string;
  onClose: () => void;
  duration?: number;
}

export function SuccessToast({ open, message, onClose, duration = 4000 }: SuccessToastProps) {
  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(onClose, duration);
    return () => window.clearTimeout(timer);
  }, [duration, onClose, open]);

  return createPortal(
    <AnimatePresence>
      {open ? (
        <motion.div
          role="status"
          aria-live="polite"
          initial={{ opacity: 0, y: -12, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.98 }}
          className="fixed right-4 top-4 z-[120] flex w-[min(calc(100vw-2rem),360px)] items-center gap-3 rounded-2xl border border-emerald-100 bg-white px-4 py-3.5 text-sm text-slate-700 shadow-[0_20px_55px_-24px_rgba(6,78,59,0.55)] sm:right-6 sm:top-6"
        >
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-600">
            <CheckCircle2 className="size-5" />
          </span>
          <span className="min-w-0 flex-1 font-medium">{message}</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Dismiss notification"
            className="grid size-8 shrink-0 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
          >
            <X className="size-4" />
          </button>
        </motion.div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}
