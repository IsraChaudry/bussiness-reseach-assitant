import { useEffect, useRef, ReactNode } from "react";
import MessageBubble, { Message } from "./MessageBubble";
import AgentProgressIndicator from "./AgentProgressIndicator";

const EXAMPLES = [
  "Research Tesla",
  "Tell me about Apple's competitors",
  "Compare Google and Microsoft AI",
  "What's OpenAI's latest news?",
];

interface Props {
  messages: Message[];
  isLoading: boolean;
  activeAgent: string | null;
  completedAgents: string[];
  onExampleClick: (text: string) => void;
  inputSlot: ReactNode;
}

export default function ChatWindow({ messages, isLoading, activeAgent, completedAgents, onExampleClick, inputSlot }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const isEmpty = messages.length === 0 && !isLoading;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="chat-window">

      {/* ── Empty / centered landing ── */}
      {isEmpty && (
        <div className="empty-state">
          <div className="empty-logo">🔍</div>
          <h2>Business Research Assistant</h2>
          <p>
            Ask me to research any company — I'll gather news, financials,
            competitors, and leadership using live web search.
          </p>
          <div className="examples">
            {EXAMPLES.map((ex) => (
              <button key={ex} className="example-chip" onClick={() => onExampleClick(ex)}>
                {ex}
              </button>
            ))}
          </div>

          {/* Input lives here when no messages */}
          <div className="empty-input-wrap">
            {inputSlot}
            <p className="footer-hint">Enter to send · Shift+Enter for new line</p>
          </div>
        </div>
      )}

      {/* ── Messages ── */}
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}

      {/* ── Loading indicator ── */}
      {isLoading && (
        <div className="message-row assistant-row">
          <div className="avatar avatar-bot">B</div>
          {activeAgent ? (
            <AgentProgressIndicator
              activeAgent={activeAgent}
              completedAgents={completedAgents}
              isVisible={true}
            />
          ) : (
            <div className="loading-bubble">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          )}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
