import axios from "axios";

import type { ChatMessage, Conversation, GeneratedDocument } from "@/components/chat/types";
import type { SupportedLanguage } from "@/lib/languages";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 120_000,
});

const TOKEN_KEY = "jurigpt_access_token";

apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401 &&
      !error.config?.url?.includes("/auth/login")
    ) {
      sessionStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event("jurigpt:unauthorized"));
    }
    return Promise.reject(error);
  },
);

export interface AuthUser {
  id: string;
  name: string;
  email: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export async function registerAccount(name: string, email: string, password: string) {
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/register", {
    name,
    email,
    password,
  });
  sessionStorage.setItem(TOKEN_KEY, response.data.access_token);
  return response.data;
}

export async function loginAccount(email: string, password: string) {
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/login", { email, password });
  sessionStorage.setItem(TOKEN_KEY, response.data.access_token);
  return response.data;
}

export async function getCurrentUser() {
  const response = await apiClient.get<AuthUser>("/api/v1/auth/me");
  return response.data;
}

export function hasAuthToken() {
  return Boolean(sessionStorage.getItem(TOKEN_KEY));
}

export function clearAuthToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

export function getAuthError(error: unknown): string {
  if (!axios.isAxiosError<ApiErrorBody>(error)) return "Something went wrong. Please try again.";
  if (!error.response) return "Unable to reach JuriGPT. Please check that the backend is running.";
  if (typeof error.response.data?.detail === "string") return error.response.data.detail;
  const details = error.response.data?.detail;
  if (Array.isArray(details)) return details[0]?.msg ?? "Please check the information you entered.";
  return "Unable to complete authentication. Please try again.";
}

interface AskRequest {
  question: string;
  language?: SupportedLanguage;
  conversation_context?: ConversationContextMessage[];
}

export interface ConversationContextMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AskResponse {
  question: string;
  language: SupportedLanguage;
  answer: string;
  sources: string[];
  generation_time: number;
  model_name: string;
  input_token_count: number | null;
  output_token_count: number | null;
  finish_reason: string | null;
  retrieved_chunks_count: number;
  processed_chunks_count: number;
  document: GeneratedDocument | null;
  document_error: string | null;
}

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
}

type StreamEvent =
  | { type: "metadata" }
  | { type: "delta"; delta: string }
  | { type: "complete"; response: AskResponse }
  | { type: "error"; message: string };

export async function streamLegalQuestion(
  question: string,
  language: SupportedLanguage,
  onDelta: (delta: string) => void,
  signal?: AbortSignal,
  conversationContext: ConversationContextMessage[] = [],
): Promise<AskResponse> {
  const baseUrl = String(apiClient.defaults.baseURL ?? "").replace(/\/$/, "");
  const token = sessionStorage.getItem(TOKEN_KEY);
  const response = await fetch(`${baseUrl}/api/v1/ask/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/x-ndjson",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      question,
      language,
      conversation_context: conversationContext.slice(-20),
    } satisfies AskRequest),
    signal,
  });

  if (response.status === 401) {
    sessionStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event("jurigpt:unauthorized"));
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : `The legal assistant returned HTTP ${response.status}.`,
    );
  }
  if (!response.body) throw new Error("The browser did not provide a response stream.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completedResponse: AskResponse | null = null;

  const processLine = (line: string) => {
    if (!line.trim()) return;
    const event = JSON.parse(line) as StreamEvent;
    if (event.type === "delta") onDelta(event.delta);
    if (event.type === "complete") completedResponse = event.response;
    if (event.type === "error") throw new Error(event.message);
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    lines.forEach(processLine);
    if (done) break;
  }
  processLine(buffer);
  if (!completedResponse) throw new Error("The response stream ended before completion.");
  return completedResponse;
}

interface PersistedUserMessage {
  id: string;
  role: "user";
  content: string;
  timestamp: string;
}

interface PersistedAssistantMessage {
  id: string;
  role: "assistant";
  answer: string[];
  sources: Array<{ title: string; category?: string | null }>;
  disclaimer: string;
  timestamp: string;
  generation_time: number;
  language?: SupportedLanguage;
  document?: GeneratedDocument | null;
  document_error?: string | null;
}

type PersistedMessage = PersistedUserMessage | PersistedAssistantMessage;

interface PersistedConversation {
  id: string;
  title: string;
  title_customized: boolean;
  messages: PersistedMessage[];
  created_at: string;
  updated_at: string;
}

function toPersistedMessage(message: ChatMessage): PersistedMessage {
  if (message.role === "user") return message;
  return {
    id: message.id,
    role: message.role,
    answer: message.answer,
    sources: message.sources,
    disclaimer: message.disclaimer,
    timestamp: message.timestamp,
    generation_time: message.generationTime,
    language: message.language ?? "en",
    document: message.document ?? null,
    document_error: message.documentError ?? null,
  };
}

function fromPersistedConversation(conversation: PersistedConversation): Conversation {
  return {
    id: conversation.id,
    title: conversation.title,
    titleCustomized: conversation.title_customized,
    messages: conversation.messages.map((message) =>
      message.role === "user"
        ? message
        : {
            id: message.id,
            role: message.role,
            answer: message.answer,
            sources: message.sources.map((source) => ({
              title: source.title,
              category: source.category ?? undefined,
            })),
            disclaimer: message.disclaimer,
            timestamp: message.timestamp,
            generationTime: message.generation_time,
            language: message.language ?? "en",
            document: message.document ?? null,
            documentError: message.document_error ?? null,
          },
    ),
    updatedAt: new Date(conversation.updated_at).getTime(),
  };
}

export async function getConversations(): Promise<Conversation[]> {
  const response = await apiClient.get<PersistedConversation[]>("/api/v1/conversations");
  return response.data.map(fromPersistedConversation);
}

export async function saveConversation(conversation: Conversation): Promise<Conversation> {
  const response = await apiClient.put<PersistedConversation>(
    `/api/v1/conversations/${encodeURIComponent(conversation.id)}`,
    {
      title: conversation.title,
      title_customized: conversation.titleCustomized ?? false,
      messages: conversation.messages.map(toPersistedMessage),
      updated_at: new Date(conversation.updatedAt).toISOString(),
    },
  );
  return fromPersistedConversation(response.data);
}

export async function renamePersistedConversation(
  conversationId: string,
  title: string,
): Promise<Conversation> {
  const response = await apiClient.patch<PersistedConversation>(
    `/api/v1/conversations/${encodeURIComponent(conversationId)}`,
    { title },
  );
  return fromPersistedConversation(response.data);
}

export async function deletePersistedConversation(conversationId: string): Promise<void> {
  await apiClient.delete(`/api/v1/conversations/${encodeURIComponent(conversationId)}`);
}

export function getConversationApiError(error: unknown): string {
  if (!axios.isAxiosError<ApiErrorBody>(error)) {
    return "Conversation changes could not be saved.";
  }
  if (!error.response) {
    return "Conversation sync is unavailable. Check your connection and try again.";
  }
  if (typeof error.response.data?.detail === "string") {
    return error.response.data.detail;
  }
  return "Conversation changes could not be saved.";
}

export async function downloadGeneratedDocument(document: GeneratedDocument): Promise<void> {
  const baseUrl = String(apiClient.defaults.baseURL ?? "").replace(/\/$/, "");
  const token = sessionStorage.getItem(TOKEN_KEY);
  const response = await fetch(`${baseUrl}${document.download_url}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (response.status === 401) {
    sessionStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event("jurigpt:unauthorized"));
  }
  if (!response.ok) throw new Error("The generated PDF could not be downloaded.");
  const objectUrl = URL.createObjectURL(await response.blob());
  const link = window.document.createElement("a");
  link.href = objectUrl;
  link.download = document.filename;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1_000);
}

export function getFriendlyApiError(error: unknown): string {
  if (error instanceof Error && !axios.isAxiosError(error) && error.message) {
    return error.message;
  }
  if (!axios.isAxiosError<ApiErrorBody>(error)) {
    return "Something unexpected happened. Please try again.";
  }

  if (error.code === "ERR_CANCELED") {
    return "The request was cancelled.";
  }
  if (!error.response) {
    return "JuriGPT could not reach the legal service. Please check that the backend is running.";
  }

  const { status, data } = error.response;
  if (status === 422 || status === 400) {
    return "Please enter a clear, non-empty legal question.";
  }
  if (status === 502) {
    return "The legal assistant is temporarily unavailable. Please try again in a moment.";
  }

  if (typeof data?.detail === "string" && data.detail.trim()) {
    return data.detail;
  }
  return "We could not process your question right now. Please try again.";
}
