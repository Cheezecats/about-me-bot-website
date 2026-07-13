import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";

type ChatStatus = "idle" | "loading" | "answered" | "refused" | "clarification" | "unavailable" | "error";

interface ChatSource {
  chunk_id: string;
  text: string;
  category: string;
  title?: string;
  label?: string;
  source?: string;
}

interface ChatResponse {
  status: string;
  answer: string;
  confidence: number;
  sources: ChatSource[];
  fallback_used: boolean;
  reason?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  status?: ChatStatus;
  sources?: ChatSource[];
}

const API_URL = import.meta.env.VITE_CHAT_API_URL || "/api/chat";

export default function ChatBot() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const scrollRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef(
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `session-${Date.now()}`,
  );

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const send = useCallback(async () => {
    const question = input.trim();
    if (!question || status === "loading") return;

    const userMsg: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStatus("loading");

    try {
      const resp = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: sessionIdRef.current }),
      });

      if (!resp.ok) {
        const errorPayload = await resp.json().catch(() => null);
        throw new Error(
          typeof errorPayload?.answer === "string"
            ? errorPayload.answer
            : resp.status === 429
            ? "Too many requests right now. Please wait a moment and try again."
            : "The chatbot is temporarily unavailable.",
        );
      }

      const data: ChatResponse = await resp.json();
      const assistantMsg: Message = {
        role: "assistant",
        content: data.answer,
        status: data.status as ChatStatus,
        sources: data.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setStatus(
        data.status === "answered"
          ? "answered"
          : data.status === "refused"
          ? "refused"
          : data.status === "clarification"
          ? "clarification"
          : data.status === "unavailable"
          ? "unavailable"
          : "error",
      );
    } catch (error) {
      const errorMsg: Message = {
        role: "assistant",
        content: "Sorry, I couldn't reach the server. Please try again later.",
        status: "error",
      };
      if (error instanceof Error && error.message !== "") {
        errorMsg.content = error.message;
      }
      setMessages((prev) => [...prev, errorMsg]);
      setStatus("error");
    }
  }, [input, status]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white shadow-lg transition-all hover:scale-105 dark:bg-white dark:text-neutral-900"
        aria-label="Toggle chat"
      >
        {open ? "✕" : "💬"}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-24 right-6 z-50 flex h-[28rem] w-[22rem] flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl dark:border-neutral-700 dark:bg-neutral-900"
          >
            <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3 dark:border-neutral-700">
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-white">Ask James</h3>
              <span className="text-xs text-neutral-500">AI-powered</span>
            </div>

            <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {messages.length === 0 && (
                <p className="text-sm text-neutral-500 text-center mt-8">
                  Ask me anything about James — his projects, hobbies, sports, or favorites!
                </p>
              )}
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${
                      msg.role === "user"
                        ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                        : msg.status === "error" || msg.status === "unavailable"
                        ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                        : msg.status === "refused" || msg.status === "clarification"
                        ? "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200"
                        : "bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100"
                    }`}
                  >
                    <span className="whitespace-pre-line">{msg.content}</span>
                    {msg.sources && msg.sources.length > 0 && msg.status === "answered" && (
                      <details className="mt-2 text-xs opacity-70">
                        <summary className="cursor-pointer">Sources ({msg.sources.length})</summary>
                        <ul className="mt-1 space-y-1">
                          {msg.sources.map((source) => (
                            <li key={source.chunk_id}>
                              <span className="font-medium">{source.label || source.title || source.category}</span>
                              <span className="ml-1">{source.text.replace(/^#+\s*[^\n]+\s*/, "").slice(0, 140)}...</span>
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                </div>
              ))}
              {status === "loading" && (
                <div className="flex justify-start">
                  <div className="rounded-2xl bg-neutral-100 px-3 py-2 text-sm dark:bg-neutral-800">
                    <span className="inline-flex gap-1">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400" style={{ animationDelay: "0ms" }} />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400" style={{ animationDelay: "150ms" }} />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400" style={{ animationDelay: "300ms" }} />
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-neutral-200 p-3 dark:border-neutral-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  maxLength={500}
                  placeholder="Type a question..."
                  className="flex-1 rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm outline-none focus:border-neutral-400 dark:border-neutral-700 dark:bg-neutral-800 dark:text-white"
                />
                <button
                  onClick={send}
                  disabled={status === "loading" || !input.trim()}
                  className="rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-700 disabled:opacity-40 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
                >
                  Send
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
