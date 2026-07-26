import { AlertCircle, LoaderCircle, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useAuth } from "@/auth/auth-state";
import { AppHeader } from "@/components/app-header";
import { AppSidebar } from "@/components/app-sidebar";
import { ChatWindow } from "@/components/chat/chat-window";
import type { ChatMessage, Conversation } from "@/components/chat/types";
import {
  deletePersistedConversation,
  getConversationApiError,
  getConversations,
  renamePersistedConversation,
  saveConversation,
} from "@/services/api";

function createConversation(): Conversation {
  return {
    id: crypto.randomUUID(),
    title: "New conversation",
    messages: [],
    updatedAt: Date.now(),
  };
}

function createConversationTitle(question: string) {
  const normalized = question.replace(/\s+/g, " ").trim();
  if (normalized.length <= 44) return normalized;
  const shortened = normalized.slice(0, 44);
  const lastSpace = shortened.lastIndexOf(" ");
  return `${shortened.slice(0, lastSpace > 28 ? lastSpace : 44).trim()}...`;
}

export function WorkspacePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { conversationId: routeConversationId } = useParams<{
    conversationId: string;
  }>();
  const [conversations, setConversations] = useState<Conversation[]>(() => [createConversation()]);
  const [activeConversationId, setActiveConversationId] = useState(() => conversations[0].id);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [persistenceError, setPersistenceError] = useState<string | null>(null);
  const persistenceQueues = useRef(new Map<string, Promise<void>>());
  const initialRouteConversationId = useRef(routeConversationId);
  const pendingLocalRouteId = useRef<string | null>(null);
  const activeConversation =
    conversations.find((conversation) => conversation.id === activeConversationId) ??
    conversations[0];
  const visibleConversations = useMemo(
    () => conversations.filter((conversation) => conversation.messages.length > 0),
    [conversations],
  );

  const enqueuePersistence = (conversationId: string, operation: () => Promise<unknown>) => {
    const previous = persistenceQueues.current.get(conversationId) ?? Promise.resolve();
    const next = previous
      .catch(() => undefined)
      .then(operation)
      .then(() => setPersistenceError(null))
      .catch((error: unknown) => setPersistenceError(getConversationApiError(error)));
    persistenceQueues.current.set(conversationId, next);
    void next.finally(() => {
      if (persistenceQueues.current.get(conversationId) === next) {
        persistenceQueues.current.delete(conversationId);
      }
    });
  };

  const updateMessages = (messages: ChatMessage[]) => {
    const firstQuestion = messages.find((message) => message.role === "user");
    const updatedConversation: Conversation = {
      ...activeConversation,
      messages,
      title:
        !activeConversation.titleCustomized && firstQuestion?.role === "user"
          ? createConversationTitle(firstQuestion.content)
          : activeConversation.title,
      updatedAt: Date.now(),
    };
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === activeConversationId ? updatedConversation : conversation,
      ),
    );
    if (messages.length > 0) {
      enqueuePersistence(updatedConversation.id, () => saveConversation(updatedConversation));
    }
  };

  const startNewChat = () => {
    setSearchQuery("");
    const existingEmpty = conversations.find((conversation) => conversation.messages.length === 0);
    if (existingEmpty) {
      pendingLocalRouteId.current = existingEmpty.id;
      setActiveConversationId(existingEmpty.id);
      navigate(`/chat/${encodeURIComponent(existingEmpty.id)}`);
    } else {
      const conversation = createConversation();
      pendingLocalRouteId.current = conversation.id;
      setConversations((current) => [conversation, ...current]);
      setActiveConversationId(conversation.id);
      navigate(`/chat/${encodeURIComponent(conversation.id)}`);
    }
    requestAnimationFrame(() =>
      document.querySelector<HTMLTextAreaElement>("#legal-question-input")?.focus(),
    );
  };

  const selectConversation = (conversationId: string) => {
    pendingLocalRouteId.current = conversationId;
    setActiveConversationId(conversationId);
    navigate(`/chat/${encodeURIComponent(conversationId)}`);
    setSidebarOpen(false);
  };

  const renameConversation = (conversationId: string, title: string) => {
    const normalizedTitle = title.replace(/\s+/g, " ").trim();
    if (!normalizedTitle) return;
    const conversation = conversations.find((item) => item.id === conversationId);
    if (!conversation) return;
    setConversations((current) =>
      current.map((item) =>
        item.id === conversationId
          ? { ...item, title: normalizedTitle, titleCustomized: true }
          : item,
      ),
    );
    enqueuePersistence(conversationId, () =>
      renamePersistedConversation(conversationId, normalizedTitle),
    );
  };

  const deleteConversation = (conversationId: string) => {
    enqueuePersistence(conversationId, () => deletePersistedConversation(conversationId));
    const remaining = conversations.filter((conversation) => conversation.id !== conversationId);
    if (remaining.length === 0) {
      const replacement = createConversation();
      pendingLocalRouteId.current = replacement.id;
      setActiveConversationId(replacement.id);
      setConversations([replacement]);
      navigate(`/chat/${encodeURIComponent(replacement.id)}`, { replace: true });
      return;
    }
    setConversations(remaining);
    if (conversationId === activeConversationId) {
      pendingLocalRouteId.current = remaining[0].id;
      setActiveConversationId(remaining[0].id);
      navigate(`/chat/${encodeURIComponent(remaining[0].id)}`, { replace: true });
    }
  };

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setLoadingConversations(true);
    void getConversations()
      .then((savedConversations) => {
        if (cancelled) return;
        const requestedConversation = initialRouteConversationId.current
          ? savedConversations.find(
              (conversation) => conversation.id === initialRouteConversationId.current,
            )
          : undefined;
        const blankConversation = requestedConversation ? undefined : createConversation();
        const loaded = blankConversation
          ? [blankConversation, ...savedConversations]
          : savedConversations;
        const selectedConversation = requestedConversation ?? blankConversation;
        if (!selectedConversation) return;
        pendingLocalRouteId.current = selectedConversation.id;
        setConversations(loaded);
        setActiveConversationId(selectedConversation.id);
        if (initialRouteConversationId.current !== selectedConversation.id) {
          navigate(`/chat/${encodeURIComponent(selectedConversation.id)}`, {
            replace: true,
          });
        }
        setPersistenceError(null);
      })
      .catch((error: unknown) => {
        if (!cancelled) setPersistenceError(getConversationApiError(error));
      })
      .finally(() => {
        if (!cancelled) setLoadingConversations(false);
      });
    return () => {
      cancelled = true;
    };
  }, [navigate, user]);

  useEffect(() => {
    if (loadingConversations || !routeConversationId) return;
    const requestedConversation = conversations.find(
      (conversation) => conversation.id === routeConversationId,
    );
    if (requestedConversation) {
      if (pendingLocalRouteId.current === routeConversationId) {
        pendingLocalRouteId.current = null;
      }
      if (requestedConversation.id !== activeConversationId) {
        setActiveConversationId(requestedConversation.id);
      }
      return;
    }
    if (pendingLocalRouteId.current === routeConversationId) return;
    navigate(`/chat/${encodeURIComponent(activeConversation.id)}`, {
      replace: true,
    });
  }, [
    activeConversation.id,
    activeConversationId,
    conversations,
    loadingConversations,
    navigate,
    routeConversationId,
  ]);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      const modifier = event.metaKey || event.ctrlKey;
      if (modifier && event.key.toLowerCase() === "k") {
        event.preventDefault();
        const searchInput = Array.from(
          document.querySelectorAll<HTMLInputElement>("[data-history-search]"),
        ).find((input) => input.offsetParent !== null);
        if (searchInput) {
          searchInput.focus();
        } else {
          document.querySelector<HTMLTextAreaElement>("#legal-question-input")?.focus();
        }
      }
      if (modifier && event.shiftKey && event.key.toLowerCase() === "n") {
        event.preventDefault();
        startNewChat();
      }
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  });

  return (
    <div className="h-dvh overflow-hidden bg-[radial-gradient(circle_at_85%_0%,rgba(45,212,191,0.2),transparent_28%),linear-gradient(135deg,#dce8e5_0%,#f3f5f1_48%,#d6e4e2_100%)] p-0 sm:p-4">
      <a href="#workspace" className="skip-link">
        Skip to legal assistant
      </a>
      <div className="mx-auto flex h-full min-h-0 max-w-[1560px] overflow-hidden bg-[#102c2a] shadow-[0_35px_90px_-35px_rgba(15,44,42,0.45)] sm:rounded-[32px]">
        <AppSidebar
          conversations={visibleConversations}
          activeConversationId={activeConversationId}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNewChat={startNewChat}
          onSelectConversation={selectConversation}
          onRenameConversation={renameConversation}
          onDeleteConversation={deleteConversation}
          onLogout={logout}
        />
        <main
          id="workspace"
          className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[#f5f8f7] sm:rounded-[28px]"
        >
          <AppHeader
            onOpenSidebar={() => setSidebarOpen(true)}
            userName={user?.name ?? "Profile"}
          />
          <div className="min-h-0 flex-1 p-2 sm:p-4 lg:p-5">
            <div className="relative h-full">
              {persistenceError ? (
                <div className="absolute left-1/2 top-3 z-30 flex w-[min(92%,620px)] -translate-x-1/2 items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50/95 px-4 py-3 text-xs text-amber-800 shadow-lg backdrop-blur">
                  <AlertCircle className="size-4 shrink-0" />
                  <span className="min-w-0 flex-1">{persistenceError}</span>
                  <button
                    type="button"
                    onClick={() => setPersistenceError(null)}
                    className="grid size-7 place-items-center rounded-lg hover:bg-amber-100"
                    aria-label="Dismiss synchronization error"
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
              ) : null}
              {loadingConversations ? (
                <div className="grid h-full min-h-[400px] place-items-center rounded-[24px] bg-white">
                  <div className="flex items-center gap-3 text-sm text-slate-500">
                    <LoaderCircle className="size-5 animate-spin text-teal-700" />
                    Loading your conversations
                  </div>
                </div>
              ) : (
                <ChatWindow
                  key={activeConversation.id}
                  messages={activeConversation.messages}
                  onMessagesChange={updateMessages}
                />
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
