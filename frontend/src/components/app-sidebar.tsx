import { BookOpenText, ChevronRight, Clock3, FileText, LogOut, MessageSquareText, Plus, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { BrandLogo } from "@/components/brand-logo";
import type { UserChatMessage } from "@/components/chat/types";
import { Button } from "@/components/ui/button";

const resources = [
  "Consumer Protection Act",
  "Industrial Relations Code",
  "Cyber Crime Portal",
  "Legal Awareness FAQ",
];

interface AppSidebarProps {
  questions: UserChatMessage[];
  searchQuery: string;
  open: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onSelectQuestion: (id: string) => void;
}

function SidebarContent({ questions, searchQuery, onClose, onNewChat, onSelectQuestion }: AppSidebarProps) {
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const filteredQuestions = questions.filter((question) =>
    question.content.toLowerCase().includes(normalizedSearch),
  );
  const startNewChat = () => {
    onNewChat();
    onClose();
  };
  const selectQuestion = (id: string) => {
    onSelectQuestion(id);
    onClose();
  };

  return (
    <div className="flex h-full min-h-0 flex-col px-4 py-5 text-white sm:px-5 sm:py-6">
      <div className="flex items-center justify-between px-1">
        <div className="flex min-w-0 items-center gap-3">
          <BrandLogo className="size-10 rounded-xl bg-teal-500 shadow-none" />
          <div className="min-w-0">
            <p className="truncate text-lg font-semibold tracking-[-0.03em]">JuriGPT</p>
            <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-teal-100/60">
              Legal intelligence
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="text-white hover:bg-white/10 lg:hidden"
          aria-label="Close sidebar"
        >
          <X className="size-4" />
        </Button>
      </div>

      <section className="mt-8 flex min-h-0 flex-1 flex-col" aria-labelledby="history-heading">
        <div className="flex items-center justify-between px-2">
          <h2 id="history-heading" className="flex items-center gap-2 text-xs font-semibold text-white/80">
            <Clock3 className="size-4 text-teal-400" /> History
          </h2>
          <button
            type="button"
            onClick={startNewChat}
            className="grid size-8 place-items-center rounded-lg text-teal-100/50 transition hover:bg-white/[0.08] hover:text-white"
            aria-label="Start a new chat"
            title="New chat"
          >
            <Plus className="size-4" />
          </button>
        </div>

        <div className="mt-3 min-h-0 flex-1 space-y-1.5 overflow-y-auto pr-1 sidebar-scrollbar">
          <AnimatePresence initial={false}>
            {filteredQuestions.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-2xl border border-white/[0.07] bg-white/[0.04] px-4 py-5 text-center"
              >
                <MessageSquareText className="mx-auto size-5 text-teal-100/40" />
                <p className="mt-2 text-xs font-medium text-white/60">
                  {questions.length === 0 ? "No conversations yet" : "No matching questions"}
                </p>
                <p className="mt-1 text-[10px] leading-4 text-teal-100/40">
                  {questions.length === 0 ? "Your conversations will appear here." : "Try another search term."}
                </p>
              </motion.div>
            ) : (
              [...filteredQuestions].reverse().map((question) => (
                <motion.button
                  layout
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  key={question.id}
                  type="button"
                  onClick={() => selectQuestion(question.id)}
                  title={question.content}
                  className="group flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-white/70 transition-colors hover:bg-white/[0.08] hover:text-white focus-visible:bg-white/[0.08]"
                >
                  <Clock3 className="size-4 shrink-0 text-teal-300/70" strokeWidth={1.7} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-medium">{question.content}</span>
                    <span className="mt-0.5 block text-[10px] text-teal-100/40">{question.timestamp}</span>
                  </span>
                  <ChevronRight className="size-3.5 shrink-0 opacity-0 transition-opacity group-hover:opacity-60" />
                </motion.button>
              ))
            )}
          </AnimatePresence>
        </div>
      </section>

      <section className="relative mt-5 overflow-hidden rounded-[24px] border border-teal-200/20 bg-gradient-to-br from-teal-500 to-emerald-700 p-5 shadow-[0_20px_50px_-28px_rgba(20,184,166,0.8)]" aria-labelledby="resources-heading">
        <div className="pointer-events-none absolute -right-8 -top-10 size-28 rounded-full bg-white/10" />
        <div className="pointer-events-none absolute -bottom-10 -left-6 size-20 rounded-full bg-white/10" />
        <BookOpenText className="relative size-5 text-white" strokeWidth={1.8} />
        <h2 id="resources-heading" className="relative mt-3 text-sm font-semibold">Resource Documents</h2>
        <p className="relative mt-1 text-[10px] leading-4 text-teal-50/70">
          Trusted legal references used by JuriGPT.
        </p>
        <div className="relative mt-3 space-y-1.5">
          {resources.map((resource) => (
            <div key={resource} className="flex min-w-0 items-center gap-2 text-[10px] leading-4 text-teal-50/80">
              <FileText className="size-3 shrink-0" />
              <span className="truncate">{resource}</span>
            </div>
          ))}
        </div>
      </section>

      <button
        type="button"
        className="mt-4 flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-xs text-teal-100/50 transition hover:bg-white/[0.06] hover:text-white"
        title="Log out"
      >
        <LogOut className="size-4" /> Log out
      </button>
    </div>
  );
}

export function AppSidebar(props: AppSidebarProps) {
  return (
    <>
      <aside className="hidden h-full w-[286px] shrink-0 lg:block" aria-label="JuriGPT sidebar">
        <SidebarContent {...props} />
      </aside>
      <AnimatePresence>
        {props.open ? (
          <>
            <motion.button
              type="button"
              aria-label="Close sidebar"
              className="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-sm lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={props.onClose}
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 360, damping: 36 }}
              className="fixed inset-y-0 left-0 z-50 w-[min(86vw,300px)] bg-[#102c2a] shadow-2xl lg:hidden"
              aria-label="JuriGPT sidebar"
            >
              <SidebarContent {...props} />
            </motion.aside>
          </>
        ) : null}
      </AnimatePresence>
    </>
  );
}
