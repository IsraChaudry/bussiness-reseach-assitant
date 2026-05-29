export interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
}

interface Props {
  sessions: ChatSession[];
  activeId: string;
  collapsed: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
}

function groupByDate(sessions: ChatSession[]) {
  const now = new Date();
  const today: ChatSession[] = [];
  const yesterday: ChatSession[] = [];
  const older: ChatSession[] = [];

  sessions.forEach((s) => {
    const days = (now.getTime() - s.createdAt.getTime()) / 86_400_000;
    if (days < 1)      today.push(s);
    else if (days < 2) yesterday.push(s);
    else               older.push(s);
  });

  return { today, yesterday, older };
}

function PlusIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5"  y1="12" x2="19" y2="12" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  );
}

export default function Sidebar({ sessions, activeId, collapsed, onSelect, onNew }: Props) {
  const { today, yesterday, older } = groupByDate(sessions);

  const renderItem = (s: ChatSession) => (
    <button
      key={s.id}
      className={`sidebar-item ${s.id === activeId ? "active" : ""}`}
      onClick={() => onSelect(s.id)}
      title={s.title}
    >
      <span className="sidebar-item-icon"><ChatIcon /></span>
      <span className="sidebar-item-text">{s.title}</span>
    </button>
  );

  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>

      {/* ── Logo strip ── */}
      <div className="sidebar-header">
        <div className="sidebar-logo">B</div>
        <div>
          <div className="sidebar-title">BizResearch</div>
          <div className="sidebar-subtitle">AI Assistant</div>
        </div>
      </div>

      {/* ── New chat ── */}
      <button className="new-chat-btn" onClick={onNew}>
        <PlusIcon /> New conversation
      </button>

      {/* ── History ── */}
      <div className="sidebar-list">
        {today.length > 0 && (
          <>
            <div className="sidebar-section-label">Today</div>
            {today.map(renderItem)}
          </>
        )}
        {yesterday.length > 0 && (
          <>
            <div className="sidebar-section-label">Yesterday</div>
            {yesterday.map(renderItem)}
          </>
        )}
        {older.length > 0 && (
          <>
            <div className="sidebar-section-label">Earlier</div>
            {older.map(renderItem)}
          </>
        )}
        {sessions.length === 0 && (
          <p style={{ fontSize: "0.78rem", color: "var(--sb-text-3)", padding: "10px 12px", lineHeight: 1.5 }}>
            No conversations yet.<br />Start one below.
          </p>
        )}
      </div>

      {/* ── Footer ── */}
      <div className="sidebar-footer">
        <div className="sidebar-footer-tag">
          <span className="status-dot" />
          Groq · Llama 3.3 70B
        </div>
      </div>

    </aside>
  );
}
