import { useEffect, useState } from "react";

import { useAuth } from "@/auth/auth-context";
import { AppSidebar } from "@/components/app-sidebar";
import { AppHeader } from "@/components/app-header";
import { ChatWindow } from "@/components/chat/chat-window";
import type { ChatMessage, Conversation } from "@/components/chat/types";

function createConversation(): Conversation {
  return {
    id: crypto.randomUUID(),
    title: "New conversation",
    messages: [],
    updatedAt: Date.now(),
  };
}

export function WorkspacePage() {
  const { user, logout } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>(() => [createConversation()]);
  const [activeConversationId, setActiveConversationId] = useState(() => conversations[0].id);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const activeConversation =
    conversations.find((conversation) => conversation.id === activeConversationId) ?? conversations[0];

  const updateMessages = (messages: ChatMessage[]) => {
    setConversations((current) =>
      current.map((conversation) => {
        if (conversation.id !== activeConversationId) return conversation;
        const firstQuestion = messages.find((message) => message.role === "user");
        return {
          ...conversation,
          messages,
          title: firstQuestion?.role === "user" ? firstQuestion.content : "New conversation",
          updatedAt: Date.now(),
        };
      }),
    );
  };

  const startNewChat = () => {
    setSearchQuery("");
    const existingEmpty = conversations.find((conversation) => conversation.messages.length === 0);
    if (existingEmpty) {
      setActiveConversationId(existingEmpty.id);
    } else {
      const conversation = createConversation();
      setConversations((current) => [conversation, ...current]);
      setActiveConversationId(conversation.id);
    }
    requestAnimationFrame(() =>
      document.querySelector<HTMLTextAreaElement>("#legal-question-input")?.focus(),
    );
  };

  const selectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId);
    setSidebarOpen(false);
  };

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      const modifier = event.metaKey || event.ctrlKey;
      if (modifier && event.key.toLowerCase() === "k") {
        event.preventDefault();
        const searchInput = Array.from(
          document.querySelectorAll<HTMLInputElement>("[data-history-search]"),
        ).find((input) => input.offsetParent !== null);
        if (searchInput && searchInput.offsetParent !== null) {
          searchInput.focus();
        } else {
          document.querySelector<HTMLTextAreaElement>("#legal-question-input")?.focus();
        }
      }
      if (modifier && event.shiftKey && event.key.toLowerCase() === "n") {
        event.preventDefault();
        startNewChat();
        requestAnimationFrame(() =>
          document.querySelector<HTMLTextAreaElement>("#legal-question-input")?.focus(),
        );
      }
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  });

  return (
    <div className="min-h-dvh bg-[radial-gradient(circle_at_85%_0%,rgba(45,212,191,0.2),transparent_28%),linear-gradient(135deg,#dce8e5_0%,#f3f5f1_48%,#d6e4e2_100%)] p-0 sm:p-4 lg:h-dvh lg:overflow-hidden">
      <a href="#workspace" className="skip-link">Skip to legal assistant</a>
      <div className="mx-auto flex min-h-dvh max-w-[1560px] overflow-hidden bg-[#102c2a] shadow-[0_35px_90px_-35px_rgba(15,44,42,0.45)] sm:min-h-[calc(100dvh-2rem)] sm:rounded-[32px] lg:h-[calc(100dvh-2rem)] lg:min-h-0">
        <AppSidebar
          conversations={conversations.filter((conversation) => conversation.messages.length > 0)}
          activeConversationId={activeConversationId}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNewChat={startNewChat}
          onSelectConversation={selectConversation}
          onLogout={logout}
        />
        <main id="workspace" className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[#f5f8f7] sm:rounded-[28px]">
          <AppHeader
            onOpenSidebar={() => setSidebarOpen(true)}
            userName={user?.name ?? "Profile"}
          />
          <div className="min-h-0 flex-1 p-2 sm:p-4 lg:p-5">
            <ChatWindow
              key={activeConversation.id}
              messages={activeConversation.messages}
              onMessagesChange={updateMessages}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
