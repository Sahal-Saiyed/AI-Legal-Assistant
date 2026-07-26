import {
  Check,
  LogOut,
  MessageSquareText,
  MoreVertical,
  Pencil,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { BrandLogo } from "@/components/brand-logo";
import type { Conversation } from "@/components/chat/types";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { ThemedScrollArea } from "@/components/ui/themed-scroll-area";
import { cn } from "@/lib/utils";

interface AppSidebarProps {
  conversations: Conversation[];
  activeConversationId: string;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  open: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
  onDeleteConversation: (id: string) => void;
  onLogout: () => void;
}

interface ConversationMenuProps {
  conversation: Conversation;
  open: boolean;
  onToggle: () => void;
  onClose: () => void;
  onRename: () => void;
  onDelete: () => void;
}

const MENU_WIDTH = 168;
const MENU_HEIGHT = 92;

function ConversationMenu({
  conversation,
  open,
  onToggle,
  onClose,
  onRename,
  onDelete,
}: ConversationMenuProps) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);

  useLayoutEffect(() => {
    if (!open) {
      setPosition(null);
      return;
    }
    const update = () => {
      const trigger = triggerRef.current;
      if (!trigger) return;
      const rect = trigger.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const top = spaceBelow < MENU_HEIGHT + 12 ? rect.top - MENU_HEIGHT - 6 : rect.bottom + 6;
      const left = Math.max(
        8,
        Math.min(rect.right - MENU_WIDTH, window.innerWidth - MENU_WIDTH - 8),
      );
      setPosition({ top, left });
    };
    update();
    window.addEventListener("resize", update);
    // capture-phase so scrolling any ancestor (incl. the chat list) repositions the menu
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open]);

  return (
    <div className="relative shrink-0" data-conversation-menu>
      <button
        ref={triggerRef}
        type="button"
        onClick={onToggle}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Options for ${conversation.title}`}
        className={cn(
          "grid size-7 place-items-center rounded-lg text-teal-100/60 transition hover:bg-white/10 hover:text-white",
          "opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100",
          open && "bg-white/10 text-white opacity-100",
        )}
      >
        <MoreVertical className="size-3.5" />
      </button>
      {open && position
        ? createPortal(
            <>
              <button
                type="button"
                aria-label="Close menu"
                tabIndex={-1}
                onClick={onClose}
                className="fixed inset-0 z-[119] cursor-default"
              />
              <motion.div
                role="menu"
                data-conversation-menu
                initial={{ opacity: 0, y: 4, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.14, ease: "easeOut" }}
                style={{
                  position: "fixed",
                  top: position.top,
                  left: position.left,
                  width: MENU_WIDTH,
                }}
                className="z-[120] overflow-hidden rounded-xl border border-white/10 bg-[#123230] p-1 shadow-[0_18px_45px_-18px_rgba(0,0,0,0.75)]"
              >
                <button
                  type="button"
                  role="menuitem"
                  onClick={onRename}
                  className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-white/80 transition hover:bg-white/10 hover:text-white"
                >
                  <Pencil className="size-3.5 shrink-0" /> Rename
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={onDelete}
                  className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-red-300 transition hover:bg-red-400/10 hover:text-red-200"
                >
                  <Trash2 className="size-3.5 shrink-0" /> Delete
                </button>
              </motion.div>
            </>,
            document.body,
          )
        : null}
    </div>
  );
}

function SidebarContent(props: AppSidebarProps) {
  const {
    conversations,
    activeConversationId,
    searchQuery,
    onSearchChange,
    onClose,
    onNewChat,
    onSelectConversation,
    onRenameConversation,
    onDeleteConversation,
    onLogout,
  } = props;
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editedTitle, setEditedTitle] = useState("");
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [conversationPendingDeletion, setConversationPendingDeletion] =
    useState<Conversation | null>(null);
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const filteredConversations = useMemo(
    () =>
      conversations
        .filter((conversation) => {
          const searchableText = conversation.messages
            .map((message) =>
              message.role === "user" ? message.content : message.answer.join(" "),
            )
            .join(" ");
          return `${conversation.title} ${searchableText}`.toLowerCase().includes(normalizedSearch);
        })
        .sort((left, right) => right.updatedAt - left.updatedAt),
    [conversations, normalizedSearch],
  );
  useEffect(() => {
    if (!menuOpenId) return;
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest("[data-conversation-menu]")) setMenuOpenId(null);
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpenId(null);
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [menuOpenId]);

  const startNewChat = () => {
    onNewChat();
    onClose();
  };
  const selectConversation = (id: string) => {
    onSelectConversation(id);
    onClose();
  };
  const beginRename = (conversation: Conversation) => {
    setEditingId(conversation.id);
    setEditedTitle(conversation.title);
  };
  const finishRename = () => {
    if (editingId && editedTitle.trim()) onRenameConversation(editingId, editedTitle);
    setEditingId(null);
  };
  const deleteChat = (conversation: Conversation) => {
    setConversationPendingDeletion(conversation);
  };
  const confirmDeleteChat = () => {
    if (!conversationPendingDeletion) return;
    onDeleteConversation(conversationPendingDeletion.id);
    setConversationPendingDeletion(null);
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

      <label className="relative mt-5 block sm:mt-7">
        <span className="sr-only">Search messages in recent chats</span>
        <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-teal-100/40" />
        <input
          data-history-search
          type="search"
          value={searchQuery}
          onChange={(event) => props.onSearchChange(event.target.value)}
          placeholder="Search chats"
          className="sidebar-search h-10 w-full rounded-xl border border-white/[0.08] bg-white/[0.05] pl-10 pr-9 text-xs text-white outline-none transition placeholder:text-teal-100/30 focus:border-teal-400/40 focus:bg-white/[0.08] focus:ring-2 focus:ring-teal-400/10"
        />
        {searchQuery ? (
          <button
            type="button"
            onClick={() => onSearchChange("")}
            className="absolute right-2.5 top-1/2 grid size-6 -translate-y-1/2 place-items-center rounded-full text-teal-300 transition hover:bg-white/10 hover:text-teal-100"
            aria-label="Clear chat search"
          >
            <X className="size-3.5" />
          </button>
        ) : null}
      </label>

      <section
        className="mt-4 flex min-h-0 flex-1 flex-col sm:mt-5"
        aria-labelledby="history-heading"
      >
        <div className="flex items-center justify-between px-2">
          <h2
            id="history-heading"
            className="flex items-center gap-2 text-xs font-semibold text-white/80"
          >
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
                  {conversations.length === 0
                    ? "No conversations yet"
                    : "No matching conversations"}
                </p>
                <p className="mt-1 text-[10px] leading-4 text-teal-100/40">
                  {conversations.length === 0
                    ? "Your conversations will appear here."
                    : "Try another search term."}
                </p>
              </motion.div>
            ) : (
              filteredConversations.map((conversation) => (
                <motion.div
                  layout
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -8 }}
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                  key={conversation.id}
                  title={conversation.title}
                  aria-current={conversation.id === activeConversationId ? "true" : undefined}
                  className={cn(
                    "group flex w-full items-center gap-1 rounded-2xl px-2 py-2 text-left text-white/70 transition-colors hover:bg-white/[0.08] hover:text-white",
                    conversation.id === activeConversationId && "bg-white/[0.08] text-white",
                  )}
                >
                  {editingId === conversation.id ? (
                    <>
                      <input
                        value={editedTitle}
                        onChange={(event) => setEditedTitle(event.target.value)}
                        onBlur={finishRename}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") finishRename();
                          if (event.key === "Escape") setEditingId(null);
                        }}
                        autoFocus
                        maxLength={72}
                        className="min-w-0 flex-1 rounded-lg border border-teal-400/30 bg-slate-950/20 px-2 py-1.5 text-xs text-white outline-none ring-2 ring-teal-400/10"
                        aria-label="Conversation title"
                      />
                      <button
                        type="button"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={finishRename}
                        className="grid size-7 place-items-center rounded-lg text-teal-300 hover:bg-white/10"
                        aria-label="Save conversation title"
                      >
                        <Check className="size-3.5" />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => selectConversation(conversation.id)}
                        className="min-w-0 flex-1 truncate rounded-lg px-1 py-1.5 text-left text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-400"
                      >
                        {conversation.title}
                      </button>
                      <ConversationMenu
                        conversation={conversation}
                        open={menuOpenId === conversation.id}
                        onToggle={() =>
                          setMenuOpenId((current) =>
                            current === conversation.id ? null : conversation.id,
                          )
                        }
                        onClose={() => setMenuOpenId(null)}
                        onRename={() => {
                          beginRename(conversation);
                          setMenuOpenId(null);
                        }}
                        onDelete={() => {
                          deleteChat(conversation);
                          setMenuOpenId(null);
                        }}
                      />
                    </>
                  )}
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </ThemedScrollArea>
      </section>

      <button
        type="button"
        onClick={onLogout}
        className="mt-3 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-xs text-teal-100/50 transition hover:bg-white/[0.06] hover:text-white sm:mt-4 sm:py-2"
        title="Log out"
      >
        <LogOut className="size-4" /> Log out
      </button>
      <ConfirmationDialog
        open={conversationPendingDeletion !== null}
        title="Delete this conversation?"
        description={
          conversationPendingDeletion
            ? `“${conversationPendingDeletion.title}” and all of its messages will be permanently removed. This action cannot be undone.`
            : ""
        }
        confirmLabel="Delete chat"
        onConfirm={confirmDeleteChat}
        onCancel={() => setConversationPendingDeletion(null)}
      />
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
