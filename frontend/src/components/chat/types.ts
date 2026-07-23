import type { SupportedLanguage } from "@/lib/languages";

export interface MessageSource {
  title: string;
  category?: string;
}

export interface GeneratedDocument {
  id: string;
  filename: string;
  document_type: string;
  media_type: "application/pdf";
  size_bytes: number;
  created_at: string;
  download_url: string;
}

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
  language?: SupportedLanguage;
  document?: GeneratedDocument | null;
  documentError?: string | null;
}

export type ChatMessage = UserChatMessage | AssistantChatMessage;

export interface Conversation {
  id: string;
  title: string;
  titleCustomized?: boolean;
  messages: ChatMessage[];
  updatedAt: number;
}
