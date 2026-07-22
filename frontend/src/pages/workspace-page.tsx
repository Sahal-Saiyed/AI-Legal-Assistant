import { useEffect, useState } from "react";

import { AppSidebar } from "@/components/app-sidebar";
import { AppHeader } from "@/components/app-header";
import { ChatWindow } from "@/components/chat/chat-window";
import type { ChatMessage } from "@/components/chat/types";

export function WorkspacePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const questions = messages.filter((message) => message.role === "user");

  const clearChat = () => {
    setMessages([]);
    setSearchQuery("");
    requestAnimationFrame(() =>
      document.querySelector<HTMLTextAreaElement>("#legal-question-input")?.focus(),
    );
  };

  const scrollToQuestion = (messageId: string) => {
    document.getElementById(`message-${messageId}`)?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  };

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      const modifier = event.metaKey || event.ctrlKey;
      if (modifier && event.key.toLowerCase() === "k") {
        event.preventDefault();
        const searchInput = document.querySelector<HTMLInputElement>("#history-search");
        if (searchInput && searchInput.offsetParent !== null) {
          searchInput.focus();
        } else {
          document.querySelector<HTMLTextAreaElement>("#legal-question-input")?.focus();
        }
      }
      if (modifier && event.shiftKey && event.key.toLowerCase() === "n") {
        event.preventDefault();
        clearChat();
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
          questions={questions}
          searchQuery={searchQuery}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNewChat={clearChat}
          onSelectQuestion={scrollToQuestion}
        />
        <main id="workspace" className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[#f5f8f7] sm:rounded-[28px]">
          <AppHeader
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onOpenSidebar={() => setSidebarOpen(true)}
          />
          <div className="min-h-0 flex-1 p-2 sm:p-4 lg:p-5">
            <ChatWindow messages={messages} onMessagesChange={setMessages} />
          </div>
        </main>
      </div>
    </div>
  );
}
