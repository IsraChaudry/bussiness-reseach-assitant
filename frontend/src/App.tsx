import { useState, useRef, useCallback, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import Sidebar, { ChatSession } from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import { Message } from "./components/MessageBubble";
import { sendMessage, getStatus } from "./api/chat";
import "./styles.css";

/* ── icon helpers ── */
const SendIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

const MenuIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="3" y1="6"  x2="21" y2="6" />
    <line x1="3" y1="12" x2="21" y2="12" />
    <line x1="3" y1="18" x2="21" y2="18" />
  </svg>
);

const SunIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <circle cx="12" cy="12" r="5"/>
    <line x1="12" y1="1"  x2="12" y2="3"/>  <line x1="12" y1="21" x2="12" y2="23"/>
    <line x1="4.22" y1="4.22"   x2="5.64" y2="5.64"/>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
    <line x1="1"  y1="12" x2="3"  y2="12"/> <line x1="21" y1="12" x2="23" y2="12"/>
    <line x1="4.22" y1="19.78"  x2="5.64" y2="18.36"/>
    <line x1="18.36" y1="5.64"  x2="19.78" y2="4.22"/>
  </svg>
);

const MoonIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
);

/* ── types ── */
interface FullSession extends ChatSession {
  messages: Message[];
}

function mkSession(): FullSession {
  return { id: uuidv4(), title: "New conversation", messages: [], createdAt: new Date() };
}

export default function App() {
  const [sessions, setSessions]     = useState<FullSession[]>(() => [mkSession()]);
  const [activeId, setActiveId]     = useState<string>(() => sessions[0].id);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [darkMode, setDarkMode]     = useState(true);
  const [input, setInput]           = useState("");
  const [isLoading, setIsLoading]     = useState(false);
  const [activeAgent, setActiveAgent]         = useState<string | null>(null);
  const [completedAgents, setCompletedAgents] = useState<string[]>([]);
  const textareaRef  = useRef<HTMLTextAreaElement>(null);
  const pollRef      = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevAgentRef = useRef<string | null>(null);

  /* theme */
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  /* active session helpers */
  const active = sessions.find((s) => s.id === activeId) ?? sessions[0];

  const appendMsg = useCallback((id: string, msg: Message) => {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== id) return s;
        const isFirstUser = msg.role === "user" && s.messages.filter((m) => m.role === "user").length === 0;
        return {
          ...s,
          title: isFirstUser ? msg.content.slice(0, 48) : s.title,
          messages: [...s.messages, msg],
        };
      })
    );
  }, []);

  /* auto-resize textarea */
  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  };

  /* send */
  const handleSend = useCallback(async (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
    if (!text || isLoading) return;

    const sessionId = active.id;
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    appendMsg(sessionId, { role: "user", content: text });

    // Reset agent state before starting
    setActiveAgent(null);
    setCompletedAgents([]);
    prevAgentRef.current = null;
    setIsLoading(true);

    // Poll /status every 800ms to track which agent is active
    pollRef.current = setInterval(async () => {
      try {
        const { active_agent } = await getStatus(sessionId);
        if (active_agent && active_agent !== prevAgentRef.current) {
          if (prevAgentRef.current) {
            const prev = prevAgentRef.current;
            setCompletedAgents((c: string[]) => (c.includes(prev) ? c : [...c, prev]));
          }
          prevAgentRef.current = active_agent;
          setActiveAgent(active_agent);
        }
      } catch {
        // silently ignore polling errors
      }
    }, 800);

    try {
      const res = await sendMessage(sessionId, text);
      if (res.needs_clarification && res.clarification_question) {
        appendMsg(sessionId, { role: "clarification", content: res.clarification_question });
      } else if (res.answer) {
        appendMsg(sessionId, {
          role: "assistant",
          content: res.answer,
          sources: res.sources?.filter((s) => s.url) ?? [],
        });
      }
    } catch {
      appendMsg(sessionId, { role: "assistant", content: "Something went wrong. Check that the backend is running and try again." });
    } finally {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      setActiveAgent(null);
      setCompletedAgents([]);
      prevAgentRef.current = null;
      setIsLoading(false);
      textareaRef.current?.focus();
    }
  }, [input, isLoading, active.id, appendMsg]);

  /* new chat */
  const handleNew = () => {
    const s = mkSession();
    setSessions((prev) => [s, ...prev]);
    setActiveId(s.id);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    textareaRef.current?.focus();
  };

  /* switch session */
  const handleSelect = (id: string) => {
    setActiveId(id);
  };

  /* keyboard */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="app">
      {/* ── Sidebar ── */}
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        collapsed={!sidebarOpen}
        onSelect={handleSelect}
        onNew={handleNew}
      />

      {/* ── Main ── */}
      <div className="main-area">
        {/* Topbar */}
        <div className="topbar">
          <div className="topbar-left">
            <button className="icon-btn" onClick={() => setSidebarOpen((v) => !v)} title="Toggle sidebar">
              <MenuIcon />
            </button>
            <span className="topbar-title">{active.title}</span>
          </div>
          <div className="topbar-right">
            <div className="model-badge">
              <span className="model-dot" /> llama-3.3-70b
            </div>
            <button className="icon-btn" onClick={() => setDarkMode((v) => !v)} title="Toggle theme">
              {darkMode ? <SunIcon /> : <MoonIcon />}
            </button>
          </div>
        </div>

        {/* Chat */}
        <ChatWindow
          messages={active.messages}
          isLoading={isLoading}
          activeAgent={activeAgent}
          completedAgents={completedAgents}
          onExampleClick={(text: string) => handleSend(text)}
          inputSlot={
            <div className="input-container">
              <textarea
                ref={textareaRef}
                className="chat-input"
                placeholder="Ask about a company…"
                value={input}
                onChange={(e) => { setInput(e.target.value); autoResize(); }}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                rows={1}
              />
              <button className="send-btn" onClick={() => handleSend()} disabled={isLoading || !input.trim()}>
                <SendIcon />
              </button>
            </div>
          }
        />

        {/* Footer input — only shown once conversation has started */}
        {(active.messages.length > 0 || isLoading) && (
          <footer className="footer">
            <div className="input-container">
              <textarea
                ref={textareaRef}
                className="chat-input"
                placeholder="Ask about a company…"
                value={input}
                onChange={(e) => { setInput(e.target.value); autoResize(); }}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                rows={1}
              />
              <button className="send-btn" onClick={() => handleSend()} disabled={isLoading || !input.trim()}>
                <SendIcon />
              </button>
            </div>
            <p className="footer-hint">Enter to send · Shift+Enter for new line</p>
          </footer>
        )}
      </div>
    </div>
  );
}
