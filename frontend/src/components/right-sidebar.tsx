import { ArrowUpRight, BookMarked, ChevronDown, Clock3, FileText, MessageSquareText, Plus } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { UserChatMessage } from "@/components/chat/types";

const resources = [
  "Consumer Protection Act",
  "Industrial Relations Code",
  "Cyber Crime Portal",
  "Legal Awareness FAQ",
  "FIR Guide",
  "Complaint Procedure",
];

interface SidebarContentProps {
  questions: UserChatMessage[];
  onSelect: (id: string) => void;
  onNewChat: () => void;
  className?: string;
}

function SidebarContent({ questions, onSelect, onNewChat, className }: SidebarContentProps) {
  return (
    <div className={cn("space-y-5", className)}>
      <motion.div
        initial={{ opacity: 0, x: 14 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.45 }}
      >
        <Card className="bg-white/85">
          <CardHeader className="flex-row items-center justify-between p-5 pb-4 sm:p-6 sm:pb-4">
            <div>
              <p className="text-sm font-semibold text-slate-900">Conversation history</p>
              <p className="mt-1 text-xs text-slate-400">Your recent spaces</p>
            </div>
            <Button
              variant="outline"
              size="icon"
              aria-label="Start a new conversation"
              aria-keyshortcuts="Control+Shift+N Meta+Shift+N"
              title="New Chat (Ctrl/Command + Shift + N)"
              onClick={onNewChat}
            >
              <Plus className="size-4" />
            </Button>
          </CardHeader>
          <CardContent className="max-h-[330px] space-y-2 overflow-y-auto p-5 pt-0 sm:p-6 sm:pt-0">
            <AnimatePresence initial={false}>
            {questions.length === 0 ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-2xl bg-stone-50 px-4 py-6 text-center">
                <MessageSquareText className="mx-auto size-5 text-slate-300" />
                <p className="mt-2 text-xs font-medium text-slate-500">No conversations yet</p>
                <p className="mt-1 text-[10px] leading-4 text-slate-400">Your questions will appear here.</p>
              </motion.div>
            ) : [...questions].reverse().map((question) => (
              <motion.button
                key={question.id}
                type="button"
                layout
                initial={{ opacity: 0, x: 6 }}
                animate={{ opacity: 1, x: 0 }}
                onClick={() => onSelect(question.id)}
                title={question.content}
                className="flex w-full items-center gap-3 rounded-2xl p-3 text-left transition-all hover:-translate-y-0.5 hover:bg-[#edf7f3] hover:shadow-sm"
              >
                <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-white text-[#2d7b69] shadow-sm">
                  <Clock3 className="size-4" strokeWidth={1.7} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-medium text-slate-700">
                    {question.content}
                  </span>
                  <span className="mt-0.5 block text-[10px] text-slate-400">{question.timestamp}</span>
                </span>
              </motion.button>
            ))}
            </AnimatePresence>
            <Button variant="ghost" size="sm" onClick={onNewChat} className="mt-1 w-full gap-2 text-xs text-[#287461]">
              <Plus className="size-3.5" /> New Chat
            </Button>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 14 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.45, delay: 0.1 }}
      >
        <Card className="overflow-hidden border-[#cfe8df] bg-[#dff2ea]">
          <CardHeader className="p-5 pb-4 sm:p-6 sm:pb-4">
            <span className="mb-3 grid size-10 place-items-center rounded-2xl bg-white/80 text-[#216f5e] shadow-sm">
              <BookMarked className="size-5" strokeWidth={1.7} />
            </span>
            <p className="text-base font-semibold tracking-[-0.02em] text-[#164f44]">Legal Resources</p>
            <p className="text-xs leading-5 text-[#477b70]">A starting point for trusted legal material.</p>
          </CardHeader>
          <CardContent className="p-5 pt-0 sm:p-6 sm:pt-0">
            <div className="space-y-1.5">
              {resources.map((resource) => (
                <button
                  key={resource}
                  type="button"
                  className="group flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition-colors hover:bg-white/55"
                >
                  <FileText className="size-3.5 shrink-0 text-[#3a7d6e]" strokeWidth={1.7} />
                  <span className="min-w-0 flex-1 truncate text-[11px] font-medium text-[#285f54]">{resource}</span>
                  <ArrowUpRight className="size-3 text-[#6d998f] opacity-0 transition-opacity group-hover:opacity-100" />
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

type RightSidebarProps = Omit<SidebarContentProps, "className">;

export function RightSidebar(props: RightSidebarProps) {
  return (
    <>
      <aside className="hidden min-w-0 lg:sticky lg:top-[108px] lg:block lg:self-start" aria-label="Workspace sidebar">
        <SidebarContent {...props} />
      </aside>
      <details className="group rounded-3xl border border-white/80 bg-white/80 p-4 shadow-soft lg:hidden">
        <summary className="flex cursor-pointer list-none items-center justify-between text-sm font-semibold text-slate-800">
          History & legal resources
          <ChevronDown className="size-4 transition-transform group-open:rotate-180" />
        </summary>
        <SidebarContent {...props} className="mt-5" />
      </details>
    </>
  );
}
