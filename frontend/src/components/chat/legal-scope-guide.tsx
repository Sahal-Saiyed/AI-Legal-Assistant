import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowUpRight,
  BadgeAlert,
  BriefcaseBusiness,
  Building2,
  HeartHandshake,
  ShieldCheck,
  ShoppingBag,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

interface LegalTopic {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
  prompts: string[];
}

const legalTopics: LegalTopic[] = [
  {
    id: "consumer",
    title: "Consumer Rights",
    description: "Refunds, defective products, online purchases, and consumer complaints.",
    icon: ShoppingBag,
    prompts: [
      "What are my rights if an online seller refuses a refund?",
      "How can I file a consumer complaint for a defective product?",
      "What can I do about a misleading advertisement?",
    ],
  },
  {
    id: "cybercrime",
    title: "Cybercrime & Online Safety",
    description: "Online fraud, cybercrime reporting, digital evidence, and online safety.",
    icon: ShieldCheck,
    prompts: [
      "What should I do immediately after an online payment fraud?",
      "How do I report cybercrime in India?",
      "What evidence should I preserve after online harassment?",
    ],
  },
  {
    id: "employment",
    title: "Employment & Labour",
    description: "Wages, termination, workplace safety, and social security.",
    icon: BriefcaseBusiness,
    prompts: [
      "Can an employer terminate me without notice?",
      "What can I do if my employer has not paid my salary?",
      "What workplace safety duties does an employer have?",
    ],
  },
  {
    id: "family",
    title: "Family Law",
    description: "Marriage, domestic violence, maintenance, children, and family courts.",
    icon: HeartHandshake,
    prompts: [
      "How can someone seek protection from domestic violence?",
      "Who can claim maintenance under Indian law?",
      "What is the process for registering a marriage?",
    ],
  },
  {
    id: "police",
    title: "Police, FIR & Bail",
    description: "FIRs, complaints, arrest, bail, criminal procedure, and legal aid.",
    icon: BadgeAlert,
    prompts: [
      "How do I file an FIR?",
      "What rights does a person have when arrested?",
      "How can someone apply for free legal aid?",
    ],
  },
  {
    id: "property",
    title: "Property & Land",
    description: "Property transfers, registration, stamp duty, RERA, and land matters.",
    icon: Building2,
    prompts: [
      "What documents are needed to register a property sale?",
      "What legal checks should I make before buying a property?",
      "How can a homebuyer file a complaint under RERA?",
    ],
  },
];

interface LegalTopicExplorerProps {
  onAsk: (question: string) => void;
}

export function LegalTopicExplorer({ onAsk }: LegalTopicExplorerProps) {
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const selectedTopic = legalTopics.find((topic) => topic.id === selectedTopicId) ?? null;

  return (
    <div className="mt-6 w-full">
      <AnimatePresence mode="wait" initial={false}>
        {selectedTopic ? (
          <motion.div
            key={selectedTopic.id}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            className="mx-auto max-w-2xl"
          >
            <div className="flex items-center gap-3 text-left">
              <button
                type="button"
                onClick={() => setSelectedTopicId(null)}
                className="grid size-9 shrink-0 place-items-center rounded-xl border border-slate-200 text-slate-500 transition hover:border-teal-200 hover:bg-teal-50 hover:text-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
                aria-label="Back to legal areas"
              >
                <ArrowLeft className="size-4" />
              </button>
              <div>
                <p className="text-sm font-semibold text-slate-900">{selectedTopic.title}</p>
                <p className="mt-0.5 text-xs leading-5 text-slate-500">
                  Choose an example or write your own question below.
                </p>
              </div>
            </div>
            <div className="mt-3 grid gap-2">
              {selectedTopic.prompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => onAsk(prompt)}
                  className="group flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left text-sm leading-5 text-slate-600 shadow-sm transition hover:-translate-y-0.5 hover:border-teal-200 hover:text-slate-900 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
                >
                  <span className="min-w-0 flex-1">{prompt}</span>
                  <ArrowUpRight className="size-4 shrink-0 text-slate-300 transition group-hover:text-teal-600" />
                </button>
              ))}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="topics"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 8 }}
            className="grid grid-cols-2 gap-2.5 sm:grid-cols-3"
          >
            {legalTopics.map(({ id, title, description, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setSelectedTopicId(id)}
                className="group flex min-h-24 flex-col items-start rounded-2xl border border-stone-200/80 bg-white p-3.5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-teal-200 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 sm:min-h-28 sm:p-4"
              >
                <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-[#dff2ea] text-[#2d7b69] transition group-hover:bg-[#cdeade] sm:size-9">
                  <Icon className="size-4 sm:size-[18px]" strokeWidth={1.8} />
                </span>
                <span className="mt-3 text-xs font-semibold leading-4 text-slate-700 group-hover:text-slate-950">
                  {title}
                </span>
                <span className="sr-only">{description}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface LegalScopeModalProps {
  open: boolean;
  onClose: () => void;
  onAsk: (question: string) => void;
}

export function LegalScopeModal({ open, onClose, onAsk }: LegalScopeModalProps) {
  useEffect(() => {
    if (!open) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };

    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose, open]);

  return createPortal(
    <AnimatePresence>
      {open ? (
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
            aria-labelledby="legal-scope-title"
            initial={{ opacity: 0, y: 18, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 360, damping: 30 }}
            className="max-h-[min(88vh,760px)] w-full max-w-2xl overflow-y-auto rounded-3xl border border-white/70 bg-[#fbfdfc] p-5 shadow-2xl sm:p-7"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-700">
                  JuriGPT coverage
                </p>
                <h2
                  id="legal-scope-title"
                  className="mt-1 text-2xl font-semibold tracking-[-0.03em] text-slate-950"
                >
                  What can I ask?
                </h2>
                <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">
                  Select one of the six supported areas to see example questions.
                </p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="grid size-9 shrink-0 place-items-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
                aria-label="Close supported legal areas"
              >
                <X className="size-4" />
              </button>
            </div>
            <LegalTopicExplorer
              onAsk={(question) => {
                onClose();
                onAsk(question);
              }}
            />
            <p className="mt-5 text-center text-[11px] leading-5 text-slate-400">
              JuriGPT provides legal information based on its trusted resources, not legal advice.
            </p>
          </motion.section>
        </motion.div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}
