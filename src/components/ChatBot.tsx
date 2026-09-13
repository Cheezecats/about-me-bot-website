import { useState, useRef, useEffect, useLayoutEffect, useCallback, type CSSProperties } from "react";
import { useLocation } from "react-router-dom";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { MessageCircle, X, Info, RotateCcw, ArrowUp, ArrowDown, Maximize2, Minimize2, Camera, Code2, Compass, BookOpen, Copy, Check } from "lucide-react";
import { ChatClient, ChatRequestError, healthUrl, sourceExcerpt, type ChatResponse } from "../lib/chat";
import { isNearBottom } from "../lib/chat-format";
import ChatContent from "./ChatContent";
import ChatDestinations from "./ChatDestinations";
import "./chat.css";

type Message = { role: "user" | "assistant"; content: string; response?: ChatResponse; retry?: string };
type ServiceStatus = "checking" | "online" | "limited" | "offline";
const API_URL = import.meta.env.VITE_CHAT_API_URL || "/api/chat";
const STARTERS = [
  { label: "Projects & ideas", question: "What projects has James built?", icon: Code2, path: "/" },
  { label: "Behind the lens", question: "What camera and lenses does James use?", icon: Camera, path: "/photography" },
  { label: "Life beyond code", question: "What does James do for fun?", icon: Compass, path: "/hobbies" },
  { label: "Research & writing", question: "What has James written or researched?", icon: BookOpen, path: "/essays" },
];
const sessionId = () => crypto.randomUUID?.() ?? `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;

function CopyAnswer({ text }: { text: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  useEffect(() => {
    if (state === "idle") return;
    const timer = setTimeout(() => setState("idle"), 2500);
    return () => clearTimeout(timer);
  }, [state]);
  return <button type="button" className="chat-copy" aria-label={state === "copied" ? "Answer copied" : "Copy answer"} onClick={async () => {
    try { await navigator.clipboard.writeText(text); setState("copied"); } catch { setState("failed"); }
  }}>{state === "copied" ? <Check size={14} /> : <Copy size={14} />}<span role="status">{state === "copied" ? "Copied" : state === "failed" ? "Select text to copy" : "Copy"}</span></button>;
}

export default function ChatBot() {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [about, setAbout] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [slow, setSlow] = useState(false);
  const [service, setService] = useState<ServiceStatus>("checking");
  const [showJump, setShowJump] = useState(false);
  const [viewportStyle, setViewportStyle] = useState<CSSProperties>({});
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const launcher = useRef<HTMLButtonElement>(null);
  const scroll = useRef<HTMLDivElement>(null);
  const lastMessage = useRef<HTMLElement>(null);
  const followTail = useRef(true);
  const readingPosition = useRef(0);
  const client = useRef(new ChatClient());
  const session = useRef(sessionId());
  const healthRequest = useRef<AbortController | null>(null);
  const wasOpen = useRef(false);
  const closingForNavigation = useRef(false);
  const reduceMotion = useReducedMotion();
  const { pathname } = useLocation();
  const starters = [...STARTERS].sort((a, b) => Number(b.path === pathname) - Number(a.path === pathname));

  useEffect(() => () => { client.current.cancel(); healthRequest.current?.abort(); }, []);
  useEffect(() => {
    if (!open) {
      if (wasOpen.current && !closingForNavigation.current) launcher.current?.focus();
      closingForNavigation.current = false;
      wasOpen.current = false;
      return;
    }
    wasOpen.current = true;
    const frame = requestAnimationFrame(() => {
      // Keep the welcome screen visible on touch devices without opening the keyboard.
      if (matchMedia("(pointer: fine)").matches) inputRef.current?.focus();
    });
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") { setOpen(false); setAbout(false); } };
    window.addEventListener("keydown", escape);
    return () => { cancelAnimationFrame(frame); window.removeEventListener("keydown", escape); };
  }, [open]);

  useEffect(() => {
    if (!open || !window.visualViewport) return;
    const viewport = window.visualViewport;
    const update = () => setViewportStyle({ "--chat-viewport-height": `${viewport.height}px`, "--chat-viewport-top": `${viewport.offsetTop}px` } as CSSProperties);
    update();
    viewport.addEventListener("resize", update);
    viewport.addEventListener("scroll", update);
    return () => { viewport.removeEventListener("resize", update); viewport.removeEventListener("scroll", update); };
  }, [open]);

  useLayoutEffect(() => {
    const textarea = inputRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 112)}px`;
  }, [input, open, about]);

  const revealLatest = useCallback(() => {
    const container = scroll.current, last = lastMessage.current;
    if (!container) return;
    if (last && messages.at(-1)?.role === "assistant") {
      const top = last.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop - 20;
      container.scrollTo({ top, behavior: "instant" });
    } else container.scrollTop = container.scrollHeight;
    setShowJump(false);
  }, [messages]);

  useLayoutEffect(() => {
    if (about || !open) return;
    if (followTail.current) revealLatest();
    else {
      if (scroll.current) scroll.current.scrollTop = readingPosition.current;
      setShowJump(true);
    }
  }, [messages, loading, open, about, revealLatest]);

  useEffect(() => {
    setSlow(false);
    if (!loading) return;
    const timer = setTimeout(() => setSlow(true), 8000);
    return () => clearTimeout(timer);
  }, [loading]);

  const checkHealth = useCallback(async () => {
    healthRequest.current?.abort();
    const controller = new AbortController();
    healthRequest.current = controller;
    const timer = setTimeout(() => controller.abort(), 4000);
    try {
      const response = await fetch(healthUrl(API_URL), { signal: controller.signal });
      const body = await response.json();
      if (healthRequest.current === controller) setService(response.ok && body?.bm25_loaded ? body.status === "ok" ? "online" : "limited" : "offline");
    } catch { if (healthRequest.current === controller) setService("offline"); }
    finally { clearTimeout(timer); }
  }, []);
  useEffect(() => { if (open) void checkHealth(); }, [open, checkHealth]);

  const reset = () => {
    client.current.cancel();
    session.current = sessionId();
    setMessages([]); setInput(""); setLoading(false); setAbout(false); setShowJump(false);
    followTail.current = true;
    inputRef.current?.focus();
  };
  const send = async (preset?: string) => {
    const question = (preset ?? input).trim();
    if (!question || client.current.busy) return;
    followTail.current = true;
    setMessages(previous => [...previous, { role: "user", content: question }]);
    setInput(""); setAbout(false); setLoading(true); setShowJump(false);
    try {
      const response = await client.current.send(API_URL, question, session.current);
      setMessages(previous => [...previous, { role: "assistant", content: response.answer, response, retry: response.status === "unavailable" ? question : undefined }]);
      setLoading(false);
      if (response.status === "unavailable") setService("limited");
      else if (service !== "online") void checkHealth();
    } catch (error) {
      if (error instanceof ChatRequestError && ["cancelled", "busy"].includes(error.kind)) return;
      setMessages(previous => [...previous, { role: "assistant", content: error instanceof Error ? error.message : "I couldn't reach the chat server. Please try again.", retry: question }]);
      setLoading(false);
      if (error instanceof ChatRequestError && error.kind === "network") setService("offline");
    }
  };
  const transition = { duration: reduceMotion ? 0 : 0.2, ease: [0.25, 1, 0.5, 1] as const };
  const lastAnswer = messages.at(-1);

  return <div className="jamchat" style={viewportStyle}>
    {!open && <button ref={launcher} type="button" className="chat-launcher" aria-label="Open JamChat — ask about James" aria-expanded={false} aria-controls="jamchat-panel" onClick={() => setOpen(true)}>
      <MessageCircle size={21} aria-hidden="true" /><span>Ask James<span className="chat-launcher-caption">with JamChat</span></span>
    </button>}
    <AnimatePresence>
      {open && <motion.section id="jamchat-panel" role="dialog" aria-label="JamChat conversation" aria-modal="false" className={`chat-panel ${expanded ? "chat-expanded" : ""}`} initial={reduceMotion ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: reduceMotion ? 0 : 8 }} transition={transition}>
        <header className="chat-header">
          <div className="chat-identity"><span className="chat-mark" aria-hidden="true"><MessageCircle size={23} strokeWidth={1.7} /></span><div><h2>JamChat<span className="chat-ai">AI</span></h2><p>Get to know James</p></div></div>
          <div className="chat-tools">
            <button className="chat-icon-button chat-expand" type="button" onClick={() => setExpanded(v => !v)} aria-label={expanded ? "Compact chat" : "Expand chat"} title={expanded ? "Compact chat" : "Expand chat"}>{expanded ? <Minimize2 size={18} /> : <Maximize2 size={18} />}</button>
            <button className="chat-icon-button" type="button" onClick={() => setAbout(v => !v)} aria-label={about ? "Back to conversation" : "About this chat"} aria-expanded={about} title="About this chat"><Info size={18} /></button>
            <button className="chat-icon-button" type="button" onClick={reset} aria-label="Start a new chat" title="New chat"><RotateCcw size={18} /></button>
            <button className="chat-icon-button" type="button" onClick={() => { setOpen(false); setAbout(false); }} aria-label="Close chat" title="Close chat"><X size={20} /></button>
          </div>
        </header>
        {about ? <div className="chat-about">
          <p className="chat-eyebrow">A guide to James’s world</p><h3>Curious? Start here.</h3>
          <p>Ask about James’s projects, photography, research, sports, and interests. You can ask follow-up questions, too.</p>
          <dl><dt>Grounded in his public profile</dt><dd>Answers use James’s curated information. Open the sources beneath a reply to see supporting excerpts.</dd><dt>Honest about the gaps</dt><dd>JamChat doesn’t search the web. If a detail isn’t documented, it should say so. AI can still misunderstand a question.</dd><dt>A short conversation memory</dt><dd>Recent answered questions help it follow the conversation. New chat starts fresh; old sessions expire after an hour of inactivity.</dd></dl>
          <button className="chat-text-button" onClick={() => void send('How does this chat work?')}>Explore how JamChat works</button>
          <button className="chat-secondary" onClick={() => setAbout(false)}>Back to conversation</button>
        </div> : <>
          <div ref={scroll} className="chat-transcript" role="log" aria-label="Conversation messages" aria-live="polite" aria-relevant="additions" onScroll={() => { const el = scroll.current; if (el) { readingPosition.current = el.scrollTop; followTail.current = isNearBottom(el.scrollTop, el.scrollHeight, el.clientHeight); if (followTail.current) setShowJump(false); } }}>
            {messages.length === 0 && <div className="chat-welcome">
              <p className="chat-eyebrow">Tech, motion & perspective</p><h3>More than a bio.</h3><p>Discover what James makes,<br />captures, and cares about.</p>
              <div className="chat-starters">{starters.map(({ label, question, icon: Icon }) => <button key={label} type="button" onClick={() => void send(question)}><Icon size={19} strokeWidth={1.6} aria-hidden="true" /><span>{label}</span><ArrowUp size={15} className="chat-starter-arrow" aria-hidden="true" /></button>)}</div>
              <p className="chat-welcome-hint">Pick a starting point, or ask in your own words.</p>
            </div>}
            {messages.map((message, index) => <article ref={index === messages.length - 1 ? lastMessage : undefined} key={index} className={`chat-message chat-${message.role}`} aria-label={message.role === "user" ? "Your question" : "JamChat reply"}>
              {message.role === "user" ? <p>{message.content}</p> : <>
                <p className="chat-speaker">JamChat</p>
                <ChatContent content={message.content} />
                <ChatDestinations ids={message.response?.actions} onNavigate={() => { closingForNavigation.current = true; setOpen(false); setAbout(false); }} />
                {message.response?.sources.length ? <details className="chat-sources"><summary>{message.response.sources.length === 1 ? "1 source" : `${message.response.sources.length} sources`}</summary><ul>{message.response.sources.map(source => <li key={source.chunk_id}><strong>{source.label || source.title || source.category}</strong><p>{sourceExcerpt(source, Infinity)}</p></li>)}</ul></details> : null}
                {message.response?.normalization_applied && message.response.normalized_query && <details className="chat-interpretation"><summary>Question understood as</summary><p>{message.response.normalized_query}</p></details>}
                <div className="chat-answer-actions"><CopyAnswer text={message.content} />{message.retry && <button className="chat-secondary" disabled={loading} onClick={() => void send(message.retry)}>Try again</button>}</div>
              </>}
            </article>)}
            {loading && <div className="chat-thinking" role="status"><span className="chat-thinking-dot" aria-hidden="true" /><span>{slow ? "Still working on your reply…" : "Preparing your reply…"}</span></div>}
            {!loading && lastAnswer?.response?.suggested_questions?.length ? <div className="chat-followups"><p className="chat-eyebrow">Keep exploring</p>{lastAnswer.response.suggested_questions.map(question => <button key={question} type="button" onClick={() => void send(question)}>{question}<ArrowUp size={14} aria-hidden="true" /></button>)}</div> : null}
          </div>
          {showJump && <button className="chat-jump" onClick={() => { followTail.current = true; revealLatest(); }}><ArrowDown size={15} />Latest reply</button>}
          <form className="chat-composer" onSubmit={event => { event.preventDefault(); void send(); }}>
            {(service === "offline" || service === "limited") && <div className="chat-service" role="status"><span>{service === "offline" ? "Connection unavailable. You can try again." : "Profile facts are available; longer replies may need a retry."}</span><button type="button" onClick={() => void checkHealth()}>Check connection</button></div>}
            <div className="chat-input-wrap"><textarea ref={inputRef} rows={1} aria-label="Ask about James" aria-describedby="chat-input-help" value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) { event.preventDefault(); void send(); } }} maxLength={500} placeholder="Ask about James…" /><button type="submit" aria-label="Send message" title="Send message" disabled={loading || !input.trim()}><ArrowUp size={21} /></button></div>
            <div className="chat-composer-note"><span id="chat-input-help">{input.length >= 400 ? `${input.length}/500 characters` : 'Public profile · AI-assisted answers'}</span><span className="chat-key-hint">Shift + Enter for a new line</span></div>
          </form>
        </>}
      </motion.section>}
    </AnimatePresence>
  </div>;
}
