import { useState, useRef, useEffect, useCallback, useLayoutEffect, useId, type CSSProperties, type ReactNode } from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowUpRight, Camera, Check, ChevronDown, Gamepad2, Info, MessageCircle, Plus, RotateCcw, Sparkles, TriangleAlert, X, Grip } from "lucide-react";
import { favoriteSongPreview, resolveChatActions, type ChatDestination } from "./chatDestinations";
import "./chat.css";

type ChatStatus = "idle" | "loading" | "answered" | "refused" | "clarification" | "unavailable" | "error";
type ServiceStatus = "checking" | "online" | "offline";

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
  suggested_questions?: string[];
  normalized_query?: string;
  normalization_applied?: boolean;
  actions?: unknown;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  status?: ChatStatus;
  sources?: ChatSource[];
  suggestedQuestions?: string[];
  normalizedQuery?: string;
  normalizationApplied?: boolean;
  retryQuestion?: string;
  actions?: ChatDestination[];
}

interface PanelSize {
  width: number;
  height: number;
}

const DEFAULT_PANEL_SIZE: PanelSize = { width: 400, height: 600 };
const PANEL_SIZE_KEY = "ask-james-chat-size";

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
}

function createSessionId() {
  return typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `session-${Date.now()}`;
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
          {bulletItems.map((item, index) => <li key={index}>{renderInline(item)}</li>)}
        </ul>,
      );
      bulletItems = [];
    }
    if (numberedItems.length > 0) {
      elements.push(
        <ol key={`numbers-${elements.length}`} className="my-1 list-decimal space-y-1 pl-5">
          {numberedItems.map((item, index) => <li key={index}>{renderInline(item)}</li>)}
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
        {renderInline(trimmed)}
      </p>,
    );
  });
  flushLists();
  return <div className="space-y-1">{elements}</div>;
}

const API_URL = import.meta.env.VITE_CHAT_API_URL || "/api/chat";
const HEALTH_URL = API_URL.replace(/\/chat(?:\?.*)?$/, "/health?deep=true");
const CHATBOT_NAME = "JamChat";

function renderInline(text: string): ReactNode[] {
  return text.split(/(https?:\/\/[^\s)]+)/g).map((part, index) => (
    /^https?:\/\//.test(part)
      ? <a key={index} href={part} target="_blank" rel="noreferrer" className="jam-link">{part}</a>
      : <span key={index}>{part}</span>
  ));
}

function sourceExcerpt(source: ChatSource) {
  const title = source.title || source.label || "";
  const escapedTitle = title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const withoutHeading = title
    ? source.text.replace(new RegExp(`^#+\\s*${escapedTitle}\\s*`, "i"), "")
    : source.text.replace(/^#+\s*/, "");
  const text = withoutHeading.trim() || source.text.trim();
  return text.length > 240 ? `${text.slice(0, 240).trimEnd()}…` : text;
}

const STARTER_QUESTIONS = [
  { icon: Gamepad2, label: "Favorite games", question: "What is James's favorite game?" },
  { icon: Camera, label: "Camera setup", question: "What camera and lenses does James use?" },
  { icon: Sparkles, label: "Life & hobbies", question: "What does James do for fun?" },
  { icon: Info, label: "How it works", question: "How does this chat work?" },
];

function Disclosure({ label, children }: { label: string; children: ReactNode }) {
  const [expanded, setExpanded] = useState(false);
  const id = useId();
  const reduced = useReducedMotion();
  return <div className="jam-disclosure">
    <button type="button" aria-expanded={expanded} aria-controls={id} onClick={() => setExpanded(!expanded)}>
      {label}<ChevronDown size={14} aria-hidden="true" style={{ transform: expanded ? "rotate(180deg)" : undefined }} />
    </button>
    <AnimatePresence initial={false}>
      {expanded && <motion.div id={id} initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: reduced ? 0 : 0.18 }} className="jam-disclosure-body">
        <div>{children}</div>
      </motion.div>}
    </AnimatePresence>
  </div>;
}

function DestinationLink({ destination, onInternalClick }: { destination: ChatDestination; onInternalClick: () => void }) {
  const label = <>{destination.label}<ArrowUpRight size={14} aria-hidden="true" /></>;
  return destination.kind === "internal"
    ? <Link className="jam-destination-link" to={destination.href} onClick={onInternalClick}>{label}</Link>
    : <a className="jam-destination-link" href={destination.href} target="_blank" rel="noopener noreferrer" aria-label={`${destination.label} (opens in a new tab)`}>{label}</a>;
}

function DestinationCards({ actions, onInternalClick }: { actions: ChatDestination[]; onInternalClick: () => void }) {
  const [imageFailed, setImageFailed] = useState(false);
  const songActions = actions.filter(action => action.subject === "song");
  const otherActions = actions.filter(action => action.subject !== "song");
  const preview = songActions.length ? favoriteSongPreview() : undefined;
  if (!actions.length) return null;
  return <div className="jam-destinations" aria-label="Explore related links">
    {songActions.length > 0 && <div className="jam-song-card">
      {preview && !imageFailed && <img src={preview.image} alt={preview.alt} loading="lazy" onError={() => setImageFailed(true)} />}
      <div className="jam-song-info">
        <span className="jam-destination-eyebrow">James’s favorite song</span>
        <strong>{preview?.title ?? "Favorite song"}</strong>
        {preview?.subtitle && <span>{preview.subtitle}</span>}
        <div className="jam-song-links">{songActions.map(action => <DestinationLink key={action.id} destination={action} onInternalClick={onInternalClick} />)}</div>
      </div>
    </div>}
    {otherActions.length > 0 && <div className="jam-destination-list">{otherActions.map(action => <DestinationLink key={action.id} destination={action} onInternalClick={onInternalClick} />)}</div>}
  </div>;
}

export default function ChatBot() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus>("checking");
  const [showAbout, setShowAbout] = useState(false);
  const [showLatest, setShowLatest] = useState(false);
  const [viewport, setViewport] = useState<{ height: number; top: number } | null>(null);
  const [panelSize, setPanelSize] = useState<PanelSize>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(PANEL_SIZE_KEY) || "null");
      if (!Number.isFinite(saved?.width) || !Number.isFinite(saved?.height)) return DEFAULT_PANEL_SIZE;
      return { width: clamp(saved.width, 300, 560), height: clamp(saved.height, 400, 760) };
    } catch { return DEFAULT_PANEL_SIZE; }
  });
  const reduceMotion = useReducedMotion();
  const scrollRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef(createSessionId());
  const activeRequest = useRef<AbortController | null>(null);
  const composing = useRef(false);
  const nearBottom = useRef(true);
  const resizeCleanup = useRef<(() => void) | null>(null);

  const scrollToLatest = useCallback((smooth = false) => {
    const scroller = scrollRef.current;
    if (!scroller) return;
    nearBottom.current = true;
    scroller.scrollTo({ top: scroller.scrollHeight, behavior: smooth && !reduceMotion ? "smooth" : "auto" });
    setShowLatest(false);
  }, [reduceMotion]);

  useLayoutEffect(() => {
    const field = inputRef.current;
    if (field) {
      field.style.height = "0px";
      field.style.height = `${Math.min(field.scrollHeight, 96)}px`;
    }
  }, [input, open, showAbout, panelSize.width, viewport?.height]);

  useLayoutEffect(() => {
    if (!open || showAbout) return;
    if (nearBottom.current) scrollToLatest();
    else setShowLatest(true);
  }, [messages, status, open, showAbout, scrollToLatest]);

  useEffect(() => {
    if (!open || showAbout || !contentRef.current) return;
    const observer = new ResizeObserver(() => {
      if (nearBottom.current) scrollToLatest();
    });
    observer.observe(contentRef.current);
    return () => observer.disconnect();
  }, [open, showAbout, scrollToLatest]);

  useEffect(() => {
    try { localStorage.setItem(PANEL_SIZE_KEY, JSON.stringify(panelSize)); } catch { /* Optional persistence. */ }
  }, [panelSize]);

  useEffect(() => {
    if (!open) return;
    const visual = window.visualViewport;
    const update = () => setViewport({ height: visual?.height ?? window.innerHeight, top: visual?.offsetTop ?? 0 });
    update();
    visual?.addEventListener("resize", update);
    visual?.addEventListener("scroll", update);
    window.addEventListener("resize", update);
    return () => {
      visual?.removeEventListener("resize", update);
      visual?.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => {
      // Opening the mobile sheet should not summon the keyboard immediately.
      if (window.matchMedia("(min-width: 640px)").matches) inputRef.current?.focus({ preventScroll: true });
      else panelRef.current?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [open]);

  const closeChat = useCallback(() => {
    resizeCleanup.current?.();
    setOpen(false);
    requestAnimationFrame(() => launcherRef.current?.focus({ preventScroll: true }));
  }, []);

  const followDestination = useCallback(() => {
    resizeCleanup.current?.();
    setOpen(false);
  }, []);

  useEffect(() => {
    if (!open) return;
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !event.isComposing) closeChat();
    };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [open, closeChat]);

  useEffect(() => () => {
    activeRequest.current?.abort();
    activeRequest.current = null;
    resizeCleanup.current?.();
  }, []);

  const resetChat = () => {
    activeRequest.current?.abort();
    activeRequest.current = null;
    sessionIdRef.current = createSessionId();
    nearBottom.current = true;
    setShowLatest(false);
    setMessages([]);
    setInput("");
    setStatus("idle");
    setShowAbout(false);
    requestAnimationFrame(() => inputRef.current?.focus({ preventScroll: true }));
  };

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 4000);
    let disposed = false;
    void fetch(HEALTH_URL, { signal: controller.signal }).then(async response => {
      const body = await response.json().catch(() => null);
      if (!disposed) setServiceStatus(response.ok && body?.status === "ok" ? "online" : "offline");
    }).catch(() => { if (!disposed) setServiceStatus("offline"); }).finally(() => clearTimeout(timeout));
    return () => { disposed = true; clearTimeout(timeout); controller.abort(); };
  }, [open]);

  const beginResize = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (window.matchMedia("(max-width: 639px)").matches) return;
    event.preventDefault();
    resizeCleanup.current?.();
    const { clientX, clientY } = event;
    const start = panelRef.current?.getBoundingClientRect();
    const onMove = (move: PointerEvent) => setPanelSize({
      width: clamp((start?.width ?? panelSize.width) + clientX - move.clientX, 300, Math.min(560, window.innerWidth - 48)),
      height: clamp((start?.height ?? panelSize.height) + clientY - move.clientY, 400, Math.max(400, Math.min(760, window.innerHeight - 120))),
    });
    const cleanup = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", cleanup);
      window.removeEventListener("pointercancel", cleanup);
      resizeCleanup.current = null;
    };
    resizeCleanup.current = cleanup;
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", cleanup);
    window.addEventListener("pointercancel", cleanup);
  };

  const send = async (preset?: string) => {
    const question = (preset ?? input).trim();
    if (!question || activeRequest.current || composing.current) return;
    const controller = new AbortController();
    activeRequest.current = controller;
    const session = sessionIdRef.current;
    const isCurrent = () => activeRequest.current === controller && sessionIdRef.current === session;
    nearBottom.current = true;
    setShowAbout(false);
    setMessages(previous => [...previous, { role: "user", content: question }]);
    setInput("");
    setStatus("loading");
    const timeout = window.setTimeout(() => controller.abort(), 35000);
    try {
      const response = await fetch(API_URL, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: session }), signal: controller.signal,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(typeof payload?.answer === "string" ? payload.answer : response.status === 429
          ? "Too many requests. Please wait a moment and try again."
          : "I couldn't reach the chat server. Please try again.");
      }
      const data: ChatResponse = await response.json();
      if (!isCurrent()) return;
      if (typeof data.answer !== "string") throw new Error("The response couldn't be read. Please try again.");
      const nextStatus: ChatStatus = ["answered", "refused", "clarification", "unavailable"].includes(data.status) ? data.status as ChatStatus : "error";
      setMessages(previous => [...previous, {
        role: "assistant", content: data.answer, status: nextStatus,
        sources: data.sources ?? [], suggestedQuestions: data.suggested_questions ?? [],
        normalizedQuery: data.normalized_query, normalizationApplied: data.normalization_applied,
        actions: nextStatus === "answered" ? resolveChatActions(data.actions) : [],
        retryQuestion: nextStatus === "unavailable" || nextStatus === "error" ? question : undefined,
      }]);
      setStatus(nextStatus);
      setServiceStatus("online");
    } catch (error) {
      if (!isCurrent()) return;
      setMessages(previous => [...previous, {
        role: "assistant", status: "error", retryQuestion: question,
        content: controller.signal.aborted ? "That took longer than expected. Please try again."
          : error instanceof Error ? error.message : "I couldn't reach the chat server. Please try again.",
      }]);
      setStatus("error");
      setServiceStatus("offline");
    } finally {
      clearTimeout(timeout);
      if (isCurrent()) activeRequest.current = null;
    }
  };

  const duration = reduceMotion ? 0 : 0.18;
  const panelStyle = {
    "--jam-width": `${panelSize.width}px`, "--jam-height": `${panelSize.height}px`,
    ...(viewport ? { "--jam-viewport": `${viewport.height}px`, "--jam-top": `${viewport.top}px` } : {}),
  } as CSSProperties;

  return <div className="jam-chat">
    <motion.button ref={launcherRef} className={`jam-launcher ${open ? "is-open" : ""}`} aria-label={open ? "Close JamChat" : "Open JamChat"}
      aria-expanded={open} aria-controls="jam-panel" onClick={() => open ? closeChat() : setOpen(true)}
      whileHover={reduceMotion ? undefined : { y: -2 }} whileTap={reduceMotion ? undefined : { scale: 0.96 }}>
      {open ? <X size={22} /> : <MessageCircle size={23} />}<span>Ask James</span>
    </motion.button>
    <AnimatePresence>
      {open && <motion.div ref={panelRef} id="jam-panel" role="dialog" aria-label="JamChat" tabIndex={-1} className="jam-panel" style={panelStyle}
        initial={{ opacity: 0, y: reduceMotion ? 0 : 14, scale: reduceMotion ? 1 : 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: reduceMotion ? 0 : 10, transition: { duration } }}
        transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 380, damping: 34, mass: 0.8 }}>
        <header className="jam-header">
          <div className="jam-identity"><span className="jam-mark"><MessageCircle size={19} aria-hidden="true" /></span><div><h2>{CHATBOT_NAME}</h2><p>A little more about James</p></div></div>
          <div className="jam-tools">
            <button className="jam-icon" aria-label={showAbout ? "Back to conversation" : "About this chat"} title="About this chat" aria-pressed={showAbout} onClick={() => setShowAbout(!showAbout)}><Info size={18} /></button>
            <button className="jam-icon" aria-label="Start a new chat" title="New chat" onClick={resetChat}><Plus size={20} /></button>
            <button className="jam-icon" aria-label="Close chat" title="Close chat" onClick={closeChat}><X size={19} /></button>
          </div>
        </header>
        {serviceStatus === "offline" && <div className="jam-connection" role="status"><TriangleAlert size={13} aria-hidden="true" /> Connection unavailable. You can try again.</div>}
        <div className="jam-scroll" ref={scrollRef} onScroll={() => {
          const node = scrollRef.current;
          if (!node) return;
          nearBottom.current = node.scrollHeight - node.scrollTop - node.clientHeight < 64;
          if (nearBottom.current) setShowLatest(false);
        }}>
          <div ref={contentRef}>
            <AnimatePresence mode="wait" initial={false}>
              {showAbout ? <motion.section key="about" className="jam-about" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration }}>
                <span className="jam-eyebrow">A grounded conversation</span><h3>Get to know James.</h3>
                <p>Ask about his projects, interests, and experiences. JamChat answers from his reviewed public profile.</p>
                <div className="jam-about-item"><Check size={17} /><div><h4>Facts, with sources</h4><p>Open the sources beneath an answer to see where it came from.</p></div></div>
                <div className="jam-about-item"><MessageCircle size={17} /><div><h4>Room for a follow-up</h4><p>The conversation remembers recent questions. Start a new chat for a fresh beginning.</p></div></div>
                <div className="jam-about-item"><Info size={17} /><div><h4>Honest about the gaps</h4><p>It doesn’t browse the web or guess private details. If something isn’t documented, it says so.</p></div></div>
                <button className="jam-pill" onClick={() => { setShowAbout(false); requestAnimationFrame(() => inputRef.current?.focus({ preventScroll: true })); }}>Back to conversation</button>
              </motion.section> : <motion.div key="conversation" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration }}>
                <AnimatePresence mode="wait" initial={false}>
                  {messages.length === 0 ? <motion.section key="welcome" className="jam-welcome" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration }}>
                    <span className="jam-eyebrow">Curiosity welcome</span><h3>Ask about James.</h3><p>The projects, the passions,<br />and everything in between.</p>
                    <div className="jam-starters">{STARTER_QUESTIONS.map(({ icon: Icon, label, question }) => <button key={label} onClick={() => void send(question)}><Icon size={19} strokeWidth={1.65} aria-hidden="true" /><span>{label}</span><ArrowUpRight className="jam-starter-arrow" size={14} aria-hidden="true" /></button>)}</div>
                    <p className="jam-welcome-note">Pick a starting point, or make it your own.</p>
                  </motion.section> : <motion.div key="messages" className="jam-messages" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration }} role="log" aria-label="Conversation" aria-live="polite" aria-relevant="additions">
                    {messages.map((message, index) => <motion.article key={index} className={`jam-message jam-${message.role}`}
                      initial={{ opacity: 0, y: reduceMotion ? 0 : 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration }} aria-label={message.role === "user" ? "You" : "JamChat"}>
                      {message.role === "assistant" && <div className="jam-message-label">{message.status === "error" || message.status === "unavailable" ? <TriangleAlert size={14} className="jam-error-icon" /> : <span className="jam-mini-mark"><MessageCircle size={12} /></span>} JamChat</div>}
                      <div className="jam-message-text">{message.role === "assistant" ? renderAssistantContent(message.content) : message.content}</div>
                      {message.status === "answered" && !!message.actions?.length && <DestinationCards actions={message.actions} onInternalClick={followDestination} />}
                      {message.sources && message.sources.length > 0 && message.status === "answered" && <Disclosure label={`Sources · ${message.sources.length}`}><ul className="jam-sources">{message.sources.map(source => <li key={source.chunk_id}><strong>{source.label || source.title || source.category}</strong><p>{sourceExcerpt(source)}</p></li>)}</ul></Disclosure>}
                      {message.normalizationApplied && message.normalizedQuery && <Disclosure label="Question details"><p>Interpreted as: {message.normalizedQuery}</p></Disclosure>}
                      {index === messages.length - 1 && message.status === "answered" && !!message.suggestedQuestions?.length && <div className="jam-suggestions">{message.suggestedQuestions.map(question => <button key={question} disabled={status === "loading"} onClick={() => void send(question)}>{question}<ArrowUpRight size={13} aria-hidden="true" /></button>)}</div>}
                      {message.retryQuestion && <button className="jam-pill" disabled={status === "loading"} onClick={() => void send(message.retryQuestion)}><RotateCcw size={14} />Try again</button>}
                    </motion.article>)}
                  </motion.div>}
                </AnimatePresence>
                {status === "loading" && <div className="jam-waiting" role="status"><span className="jam-sr-only">JamChat is thinking</span>{[0, 1, 2].map(dot => <motion.span aria-hidden="true" key={dot} animate={reduceMotion ? undefined : { opacity: [0.3, 0.8, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay: dot * 0.16 }} />)}</div>}
              </motion.div>}
            </AnimatePresence>
          </div>
        </div>
        {showLatest && !showAbout && <div className="jam-latest-wrap"><button className="jam-latest jam-pill" onClick={() => scrollToLatest(true)}><ArrowDown size={14} />Latest message</button></div>}
        <footer className="jam-footer">
          <form className="jam-composer" onSubmit={event => { event.preventDefault(); void send(); }}>
            <textarea ref={inputRef} value={input} rows={1} maxLength={500} aria-label="Message JamChat" placeholder="Ask anything about James…"
              onChange={event => setInput(event.target.value)} onCompositionStart={() => { composing.current = true; }} onCompositionEnd={() => { composing.current = false; }}
              onKeyDown={event => {
                if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.nativeEvent.keyCode !== 229 && !composing.current) {
                  event.preventDefault(); void send();
                }
              }} />
            <motion.button type="submit" aria-label="Send message" disabled={status === "loading" || !input.trim()} whileTap={reduceMotion ? undefined : { scale: 0.94 }}><ArrowUp size={20} /></motion.button>
          </form>
          <div className="jam-footer-note"><span>Grounded in James’s public profile</span><span>{input.length > 400 ? `${input.length}/500` : ""}</span></div>
        </footer>
        <button className="jam-resize" aria-label="Resize chat window" title="Drag to resize; use arrow keys when focused" onPointerDown={beginResize} onKeyDown={event => {
          if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) return;
          event.preventDefault();
          setPanelSize(size => ({ width: clamp(size.width + (event.key === "ArrowLeft" ? 20 : event.key === "ArrowRight" ? -20 : 0), 300, 560), height: clamp(size.height + (event.key === "ArrowUp" ? 20 : event.key === "ArrowDown" ? -20 : 0), 400, 760) }));
        }}><Grip size={14} aria-hidden="true" /></button>
      </motion.div>}
    </AnimatePresence>
  </div>;
}
