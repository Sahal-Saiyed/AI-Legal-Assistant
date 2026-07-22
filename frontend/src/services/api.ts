import axios from "axios";

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

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export async function registerAccount(name: string, email: string, password: string) {
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/register", { name, email, password });
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
