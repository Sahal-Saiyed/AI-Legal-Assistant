import { useEffect, useState } from "react";

import { ChatWindow } from "@/components/chat/chat-window";
import type { ChatMessage } from "@/components/chat/types";
import { RightSidebar } from "@/components/right-sidebar";
import { TopNavigation } from "@/components/top-navigation";

export function WorkspacePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const questions = messages.filter((message) => message.role === "user");

  const clearChat = () => {
    setMessages([]);
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
        document.querySelector<HTMLTextAreaElement>("#legal-question-input")?.focus();
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
    <div className="min-h-screen bg-background">
      <a href="#workspace" className="skip-link">Skip to legal assistant</a>
      <TopNavigation />
      <main id="workspace" className="mx-auto grid max-w-[1480px] min-w-0 grid-cols-1 gap-4 px-3 pb-5 pt-4 sm:gap-5 sm:px-6 sm:pb-6 sm:pt-5 lg:grid-cols-[minmax(0,1fr)_320px] lg:px-8 xl:grid-cols-[minmax(0,1fr)_340px]">
        <ChatWindow messages={messages} onMessagesChange={setMessages} onClear={clearChat} />
        <RightSidebar
          questions={questions}
          onSelect={scrollToQuestion}
          onNewChat={clearChat}
        />
      </main>
    </div>
  );
}
