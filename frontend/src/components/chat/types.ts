import type { MessageSource } from "@/components/chat/assistant-message";

export interface UserChatMessage {
  id: string;
  role: "user";
  content: string;
  timestamp: string;
}

export interface AssistantChatMessage {
  id: string;
  role: "assistant";
  answer: string[];
  sources: MessageSource[];
  disclaimer: string;
  timestamp: string;
  generationTime: number;
}

export type ChatMessage = UserChatMessage | AssistantChatMessage;

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  updatedAt: number;
}
