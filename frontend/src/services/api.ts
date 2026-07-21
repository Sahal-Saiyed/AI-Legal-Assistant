import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 120_000,
});

export interface AskRequest {
  question: string;
}

export interface AskResponse {
  question: string;
  answer: string;
  sources: string[];
  generation_time: number;
  model_name: string;
  input_token_count: number | null;
  output_token_count: number | null;
  finish_reason: string | null;
  retrieved_chunks_count: number;
  processed_chunks_count: number;
}

export interface HealthResponse {
  status: string;
}

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
}

export async function askLegalQuestion(
  question: string,
  signal?: AbortSignal,
): Promise<AskResponse> {
  const response = await apiClient.post<AskResponse>(
    "/api/v1/ask",
    { question } satisfies AskRequest,
    { signal },
  );
  return response.data;
}

export async function getBackendHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>("/health", { signal });
  return response.data;
}

export function getFriendlyApiError(error: unknown): string {
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
