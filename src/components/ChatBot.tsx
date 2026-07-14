import { useState, useRef, useEffect, useCallback, type ReactNode } from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";

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

function renderAssistantContent(content: string) {
  const lines = content.split("\n");
  const elements: ReactNode[] = [];
  let bulletItems: string[] = [];
  let numberedItems: string[] = [];

  const flushLists = () => {
    if (bulletItems.length > 0) {
      elements.push(
        <ul key={`bullets-${elements.length}`} className="my-1 list-disc space-y-1 pl-5">
          {bulletItems.map((item, index) => <li key={index}>{item}</li>)}
        </ul>,
      );
      bulletItems = [];
    }
    if (numberedItems.length > 0) {
      elements.push(
        <ol key={`numbers-${elements.length}`} className="my-1 list-decimal space-y-1 pl-5">
          {numberedItems.map((item, index) => <li key={index}>{item}</li>)}
        </ol>,
      );
      numberedItems = [];
    }
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    const bullet = trimmed.match(/^[-•]\s+(.+)$/);
    const numbered = trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (bullet) {
      if (numberedItems.length > 0) flushLists();
      bulletItems.push(bullet[1]);
      return;
    }
    if (numbered) {
      if (bulletItems.length > 0) flushLists();
      numberedItems.push(numbered[1]);
      return;
    }
    flushLists();
    if (!trimmed) return;
    elements.push(
      <p key={`line-${index}`} className={trimmed.endsWith(":") ? "font-semibold" : undefined}>
        {trimmed}
      </p>,
    );
  });
  flushLists();
  return <div className="space-y-1">{elements}</div>;
}

const API_URL = import.meta.env.VITE_CHAT_API_URL || "/api/chat";

const STARTER_QUESTIONS = [
  { icon: "🎮", label: "Favorite games", question: "What is James's favorite game?" },
  { icon: "📷", label: "Camera setup", question: "What camera and lenses does James use?" },
  { icon: "⚡", label: "Hobbies", question: "What does James do for fun?" },
  { icon: "🧪", label: "Projects", question: "What projects has James built?" },
];

export default function ChatBot() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const reduceMotion = useReducedMotion();
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

  const send = useCallback(async (presetQuestion?: string) => {
    const question = (presetQuestion ?? input).trim();
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
      <motion.button
        onClick={() => setOpen(!open)}
        whileHover={reduceMotion ? undefined : { scale: 1.08, rotate: 3 }}
        whileTap={reduceMotion ? undefined : { scale: 0.92 }}
        animate={{ rotate: open ? 90 : 0, scale: open ? 0.94 : 1 }}
        className="group fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white shadow-xl shadow-neutral-900/20 dark:bg-white dark:text-neutral-900"
        aria-label="Toggle chat"
      >
        {!open && !reduceMotion && (
          <motion.span
            aria-hidden="true"
            className="absolute inset-0 rounded-full border border-neutral-400/40"
            animate={{ scale: [1, 1.22, 1], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: "easeOut" }}
          />
        )}
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={open ? "close" : "open"}
            initial={{ opacity: 0, scale: 0.4, rotate: -45 }}
            animate={{ opacity: 1, scale: 1, rotate: 0 }}
            exit={{ opacity: 0, scale: 0.4, rotate: 45 }}
            transition={{ duration: reduceMotion ? 0 : 0.18 }}
            className="relative text-xl"
          >
            {open ? "✕" : "💬"}
          </motion.span>
        </AnimatePresence>
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 32, scale: 0.88, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: 24, scale: 0.9, filter: "blur(6px)" }}
            transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 340, damping: 28, mass: 0.72 }}
            className="fixed bottom-24 right-4 z-50 flex h-[min(32rem,calc(100vh-8rem))] w-[calc(100vw-2rem)] max-w-[22rem] flex-col overflow-hidden rounded-3xl border border-neutral-200/80 bg-white/95 shadow-2xl shadow-neutral-900/20 backdrop-blur-xl dark:border-neutral-700/80 dark:bg-neutral-900/95"
          >
            <div className="relative overflow-hidden border-b border-neutral-200/80 px-4 py-3 dark:border-neutral-700/80">
              {!reduceMotion && (
                <motion.div
                  aria-hidden="true"
                  className="pointer-events-none absolute -top-16 right-0 h-32 w-32 rounded-full bg-violet-400/20 blur-3xl dark:bg-violet-500/20"
                  animate={{ x: [30, -18, 30], y: [0, 10, 0] }}
                  transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
                />
              )}
              <div className="relative flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <motion.span
                    aria-hidden="true"
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-neutral-900 text-xs text-white dark:bg-white dark:text-neutral-900"
                    animate={status === "loading" && !reduceMotion ? { rotate: [0, 12, -12, 0] } : { rotate: 0 }}
                    transition={{ duration: 1.4, repeat: status === "loading" && !reduceMotion ? Infinity : 0 }}
                  >
                    ✦
                  </motion.span>
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900 dark:text-white">Ask James</h3>
                    <motion.span
                      key={status === "loading" ? "thinking" : "ready"}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-[10px] uppercase tracking-[0.16em] text-neutral-500"
                    >
                      {status === "loading" ? "Thinking" : "AI-powered"}
                    </motion.span>
                  </div>
                </div>
                <span className="flex items-center gap-1.5 text-[10px] text-neutral-500">
                  <motion.span
                    className={`h-1.5 w-1.5 rounded-full ${status === "loading" ? "bg-violet-500" : "bg-emerald-500"}`}
                    animate={status === "loading" && !reduceMotion ? { scale: [1, 1.5, 1], opacity: [0.6, 1, 0.6] } : { scale: 1, opacity: 1 }}
                    transition={{ duration: 1, repeat: status === "loading" && !reduceMotion ? Infinity : 0 }}
                  />
                  {status === "loading" ? "working" : "online"}
                </span>
              </div>
            </div>

            <div ref={scrollRef} aria-live="polite" className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
              <AnimatePresence initial={false}>
                {messages.length === 0 && status !== "loading" && (
                  <motion.div
                    key="welcome"
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: reduceMotion ? 0 : 0.3 }}
                    className="pt-3"
                  >
                    <div className="mb-4 text-center">
                      <motion.div
                        aria-hidden="true"
                        className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-neutral-900 text-xl text-white shadow-lg dark:bg-white dark:text-neutral-900"
                        animate={!reduceMotion ? { y: [0, -5, 0], rotate: [0, 2, 0] } : undefined}
                        transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
                      >
                        ✦
                      </motion.div>
                      <p className="text-sm font-medium text-neutral-800 dark:text-neutral-100">Explore James's world</p>
                      <p className="mt-1 text-xs leading-relaxed text-neutral-500">
                        Choose a prompt or ask something in your own words.
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {STARTER_QUESTIONS.map((starter, index) => (
                        <motion.button
                          key={starter.label}
                          type="button"
                          onClick={() => void send(starter.question)}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: reduceMotion ? 0 : 0.08 * index, duration: reduceMotion ? 0 : 0.25 }}
                          whileHover={reduceMotion ? undefined : { y: -3, scale: 1.02 }}
                          whileTap={reduceMotion ? undefined : { scale: 0.97 }}
                          className="group rounded-2xl border border-neutral-200 bg-white/80 px-3 py-3 text-left shadow-sm transition-colors hover:border-neutral-400 hover:bg-white dark:border-neutral-700 dark:bg-neutral-800/80 dark:hover:border-neutral-500 dark:hover:bg-neutral-800"
                        >
                          <span className="mb-2 block text-base transition-transform group-hover:scale-110">{starter.icon}</span>
                          <span className="block text-xs font-semibold text-neutral-800 dark:text-neutral-100">{starter.label}</span>
                          <span className="mt-1 block text-[10px] leading-snug text-neutral-500 dark:text-neutral-400">{starter.question}</span>
                        </motion.button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              <AnimatePresence initial={false} mode="popLayout">
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  layout
                  initial={{ opacity: 0, y: 12, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={{ duration: reduceMotion ? 0 : 0.24 }}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${
                      msg.role === "user"
                        ? "bg-neutral-900 text-white shadow-md shadow-neutral-900/10 dark:bg-white dark:text-neutral-900"
                        : msg.status === "error" || msg.status === "unavailable"
                        ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                        : msg.status === "refused" || msg.status === "clarification"
                        ? "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200"
                        : "bg-neutral-100 text-neutral-900 shadow-sm dark:bg-neutral-800 dark:text-neutral-100"
                    }`}
                  >
                    {msg.role === "assistant" ? renderAssistantContent(msg.content) : (
                      <span className="whitespace-pre-line">{msg.content}</span>
                    )}
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
                </motion.div>
              ))}
              </AnimatePresence>
              {status === "loading" && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  className="flex justify-start"
                >
                  <div className="rounded-2xl bg-neutral-100 px-3 py-2.5 text-sm shadow-sm dark:bg-neutral-800">
                    <div className="mb-1 flex items-center gap-2 text-[10px] text-neutral-500">
                      <span>James is thinking</span>
                      <span className="inline-flex gap-1">
                        {[0, 1, 2].map((dot) => (
                          <motion.span
                            key={dot}
                            className="h-1.5 w-1.5 rounded-full bg-violet-500"
                            animate={reduceMotion ? undefined : { y: [0, -4, 0], opacity: [0.45, 1, 0.45] }}
                            transition={{ duration: 0.8, repeat: Infinity, delay: dot * 0.14 }}
                          />
                        ))}
                      </span>
                    </div>
                    {!reduceMotion && (
                      <div className="h-1 w-20 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-700">
                        <motion.div
                          className="h-full w-1/2 rounded-full bg-gradient-to-r from-violet-400 to-fuchsia-500"
                          animate={{ x: ["-100%", "200%"] }}
                          transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
                        />
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </div>

            <div className="border-t border-neutral-200/80 bg-white/70 p-3 dark:border-neutral-700/80 dark:bg-neutral-900/70">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  maxLength={500}
                  placeholder="Type a question..."
                  className="flex-1 rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm outline-none transition-shadow focus:border-neutral-400 focus:ring-2 focus:ring-violet-400/20 dark:border-neutral-700 dark:bg-neutral-800 dark:text-white"
                />
                <motion.button
                  onClick={() => void send()}
                  whileHover={reduceMotion ? undefined : { scale: 1.04 }}
                  whileTap={reduceMotion ? undefined : { scale: 0.96 }}
                  disabled={status === "loading" || !input.trim()}
                  className="rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white shadow-md transition-colors hover:bg-neutral-700 disabled:opacity-40 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
                >
                  Send
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
