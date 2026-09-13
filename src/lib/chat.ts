export type AnswerStatus = "answered" | "refused" | "clarification" | "unavailable";

export interface ChatSource {
  chunk_id: string;
  text: string;
  category: string;
  title?: string;
  label?: string;
  source?: string;
}

export interface ChatResponse {
  status: AnswerStatus;
  answer: string;
  sources: ChatSource[];
  reason?: string;
  suggested_questions?: string[];
  normalized_query?: string;
  normalization_applied?: boolean;
  actions?: string[];
}

export class ChatRequestError extends Error {
  constructor(message: string, public readonly kind: "cancelled" | "busy" | "timeout" | "network" | "http" | "invalid", public readonly status?: number) {
    super(message);
  }
}

export function parseChatResponse(value: unknown): ChatResponse {
  const data = value as Partial<ChatResponse> | null;
  if (!data || !["answered", "refused", "clarification", "unavailable"].includes(data.status ?? "") || typeof data.answer !== "string" || !data.answer.trim()) {
    throw new ChatRequestError("The chat server returned an incomplete reply. Please try again.", "invalid");
  }
  const sources = Array.isArray(data.sources) ? data.sources.filter((source): source is ChatSource =>
    !!source && typeof source.chunk_id === "string" && typeof source.text === "string" && typeof source.category === "string",
  ).map((source) => ({
    chunk_id: source.chunk_id, text: source.text, category: source.category,
    title: typeof source.title === "string" ? source.title : undefined,
    label: typeof source.label === "string" ? source.label : undefined,
  })) : [];
  return {
    status: data.status as AnswerStatus, answer: data.answer,
    sources: data.status === "answered" ? sources : [],
    reason: typeof data.reason === "string" ? data.reason : undefined,
    suggested_questions: Array.isArray(data.suggested_questions) ? data.suggested_questions.filter((q): q is string => typeof q === "string" && q.length > 0 && q.length <= 500).slice(0, 3) : [],
    normalized_query: typeof data.normalized_query === "string" ? data.normalized_query : undefined,
    normalization_applied: data.normalization_applied === true,
    actions: data.status === "answered" && Array.isArray(data.actions)
      ? [...new Set(data.actions.filter((id): id is string => typeof id === "string" && /^[a-z0-9-]{1,64}$/.test(id)))].slice(0, 6) : [],
  };
}

/** One active request per widget. Cancellation also discards a late response
 * from transports that cannot abort an already-completed server operation. */
export class ChatClient {
  private active: AbortController | null = null;

  get busy() { return this.active !== null; }

  cancel() {
    this.active?.abort();
    this.active = null;
  }

  async send(url: string, question: string, sessionId: string, timeoutMs = 35000): Promise<ChatResponse> {
    if (this.busy) throw new ChatRequestError("A reply is already on its way.", "busy");
    const controller = new AbortController();
    this.active = controller;
    let timedOut = false;
    const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
    try {
      const response = await fetch(url, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: sessionId }), signal: controller.signal,
      });
      const body = await response.json().catch(() => null);
      if (this.active !== controller) throw new ChatRequestError("Request cancelled.", "cancelled");
      if (timedOut) throw new ChatRequestError("The reply took too long. Please try again.", "timeout");
      if (!response.ok) {
        throw new ChatRequestError(
          typeof body?.answer === "string" ? body.answer : response.status === 429
            ? "Too many requests right now. Please wait a moment and try again."
            : "The chatbot is temporarily unavailable. Please try again.",
          "http", response.status,
        );
      }
      return parseChatResponse(body);
    } catch (error) {
      if (this.active !== controller) throw new ChatRequestError("Request cancelled.", "cancelled");
      if (timedOut) throw new ChatRequestError("The reply took too long. Please try again.", "timeout");
      if (error instanceof ChatRequestError) throw error;
      throw new ChatRequestError("I couldn't reach the chat server. Please try again.", "network");
    } finally {
      clearTimeout(timeout);
      if (this.active === controller) this.active = null;
    }
  }
}

export function healthUrl(apiUrl: string): string {
  return apiUrl.replace(/\/chat\/?(?:\?.*)?$/, "/health?deep=true");
}

export function sourceExcerpt(source: ChatSource, limit = 180): string {
  const title = source.title || source.label || "";
  const escaped = title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const text = source.text.replace(new RegExp(`^#+\\s*${escaped}\\s*`, "i"), "").trim();
  return text.length > limit ? `${text.slice(0, limit).trimEnd()}…` : text;
}

export function trimLinkPunctuation(url: string): [string, string] {
  const trimmed = url.replace(/[.,!?;:]+$/, "");
  return [trimmed, url.slice(trimmed.length)];
}
