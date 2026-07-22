import { BookOpenText, FileText, LogOut, MessageSquareText, Plus, Search, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { BrandLogo } from "@/components/brand-logo";
import type { Conversation } from "@/components/chat/types";
import { Button } from "@/components/ui/button";
import { ThemedScrollArea } from "@/components/ui/themed-scroll-area";
import { cn } from "@/lib/utils";

const resources = [
  "Consumer Protection Act",
  "Industrial Relations Code",
  "Cyber Crime Portal",
  "Legal Awareness FAQ",
];

interface AppSidebarProps {
  conversations: Conversation[];
  activeConversationId: string;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  open: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  onLogout: () => void;
}

function SidebarContent(props: AppSidebarProps) {
  const { conversations, activeConversationId, searchQuery, onClose, onNewChat, onSelectConversation, onLogout } = props;
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const filteredConversations = conversations.filter((conversation) => {
    const searchableText = conversation.messages
      .map((message) =>
        message.role === "user" ? message.content : message.answer.join(" "),
      )
      .join(" ");
    return `${conversation.title} ${searchableText}`.toLowerCase().includes(normalizedSearch);
  });
  const startNewChat = () => {
    onNewChat();
    onClose();
  };
  const selectConversation = (id: string) => {
    onSelectConversation(id);
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

      <label className="relative mt-7 block">
        <span className="sr-only">Search messages in recent chats</span>
        <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-teal-100/40" />
        <input
          data-history-search
          type="search"
          value={searchQuery}
          onChange={(event) => props.onSearchChange(event.target.value)}
          placeholder="Search chats"
          className="h-10 w-full rounded-xl border border-white/[0.08] bg-white/[0.05] pl-10 pr-3 text-xs text-white outline-none transition placeholder:text-teal-100/30 focus:border-teal-400/40 focus:bg-white/[0.08] focus:ring-2 focus:ring-teal-400/10"
        />
      </label>

      <section className="mt-5 flex min-h-0 flex-1 flex-col" aria-labelledby="history-heading">
        <div className="flex items-center justify-between px-2">
          <h2 id="history-heading" className="flex items-center gap-2 text-xs font-semibold text-white/80">
            <MessageSquareText className="size-4 text-teal-400" /> Recents
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

        <ThemedScrollArea
          className="mt-3 flex-1"
          viewportClassName="space-y-1.5 pr-4"
          variant="dark"
        >
          <AnimatePresence initial={false}>
            {filteredConversations.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-2xl border border-white/[0.07] bg-white/[0.04] px-4 py-5 text-center"
              >
                <MessageSquareText className="mx-auto size-5 text-teal-100/40" />
                <p className="mt-2 text-xs font-medium text-white/60">
                  {conversations.length === 0 ? "No conversations yet" : "No matching conversations"}
                </p>
                <p className="mt-1 text-[10px] leading-4 text-teal-100/40">
                  {conversations.length === 0 ? "Your conversations will appear here." : "Try another search term."}
                </p>
              </motion.div>
            ) : (
              [...filteredConversations]
                .sort((left, right) => right.updatedAt - left.updatedAt)
                .map((conversation) => (
                <motion.button
                  layout
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  key={conversation.id}
                  type="button"
                  onClick={() => selectConversation(conversation.id)}
                  title={conversation.title}
                  aria-current={conversation.id === activeConversationId ? "true" : undefined}
                  className={cn(
                    "group flex w-full items-center rounded-2xl px-3 py-3 text-left text-white/70 transition-colors hover:bg-white/[0.08] hover:text-white focus-visible:bg-white/[0.08]",
                    conversation.id === activeConversationId && "bg-white/[0.08] text-white",
                  )}
                >
                  <span className="block min-w-0 flex-1 truncate text-xs font-medium">
                    {conversation.title}
                  </span>
                </motion.button>
              ))
            )}
          </AnimatePresence>
        </ThemedScrollArea>
      </section>

      <section className="relative mt-5 overflow-hidden rounded-[24px] border border-white/15 bg-gradient-to-br from-white/[0.14] to-teal-300/[0.07] p-5 shadow-[0_20px_55px_-30px_rgba(45,212,191,0.75)] backdrop-blur-xl" aria-labelledby="resources-heading">
        <div className="pointer-events-none absolute -right-8 -top-10 size-28 rounded-full bg-teal-300/15 blur-xl" />
        <div className="pointer-events-none absolute -bottom-10 -left-6 size-20 rounded-full bg-white/[0.06]" />
        <div className="relative flex items-center gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl border border-white/15 bg-white/10 text-teal-200 shadow-sm">
            <BookOpenText className="size-4" strokeWidth={1.8} />
          </span>
          <h2 id="resources-heading" className="text-sm font-semibold">Resource Documents</h2>
        </div>
        <p className="relative mt-3 text-[10px] leading-4 text-teal-50/60">
          Trusted legal references used by JuriGPT.
        </p>
        <div className="relative mt-3 space-y-1 rounded-2xl border border-white/[0.06] bg-slate-950/10 p-2.5">
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
        onClick={onLogout}
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
