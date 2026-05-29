import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export interface Message {
  role: "user" | "assistant" | "clarification";
  content: string;
  sources?: { title: string; url: string }[];
}

interface Props {
  message: Message;
}

const BotAvatar = () => (
  <div className="avatar avatar-bot">B</div>
);

const WarnAvatar = () => (
  <div className="avatar avatar-warn">!</div>
);

export default function MessageBubble({ message }: Props) {
  const { role, content, sources } = message;

  if (role === "user") {
    return (
      <div className="message-row user-row">
        <div className="bubble-wrapper">
          <div className="bubble bubble-user">{content}</div>
        </div>
      </div>
    );
  }

  if (role === "clarification") {
    return (
      <div className="message-row clarification-row">
        <WarnAvatar />
        <div className="bubble-wrapper">
          <div className="bubble bubble-clarification">
            <div className="clarification-header">
              <span>⚠</span> Clarification needed
            </div>
            <p>{content}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message-row assistant-row">
      <BotAvatar />
      <div className="bubble-wrapper">
        <div className="bubble bubble-assistant">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content}
          </ReactMarkdown>
        </div>

        {sources && sources.length > 0 && (
          <div className="sources-card">
            <p className="sources-label">Sources</p>
            <ul className="sources-list">
              {sources.map((s, i) => (
                <li key={i} className="source-item">
                  <a href={s.url} target="_blank" rel="noreferrer">
                    <span className="source-dot" />
                    {s.title || s.url}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
