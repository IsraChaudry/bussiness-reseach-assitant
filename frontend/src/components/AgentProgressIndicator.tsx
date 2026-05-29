const AGENT_ORDER: { name: string; label: string }[] = [
  { name: "Clarity Agent",    label: "checking your query..."   },
  { name: "Research Agent",   label: "searching the web..."     },
  { name: "Validator Agent",  label: "reviewing results..."     },
  { name: "Synthesis Agent",  label: "writing your answer..."   },
];

export interface AgentProgressIndicatorProps {
  activeAgent: string | null;
  completedAgents: string[];
  isVisible: boolean;
}

export default function AgentProgressIndicator({
  activeAgent,
  completedAgents,
  isVisible,
}: AgentProgressIndicatorProps) {
  if (!isVisible) return null;

  return (
    <div className="agent-indicator">
      {AGENT_ORDER.map((agent) => {
        const isActive    = activeAgent === agent.name;
        const isDone      = completedAgents.includes(agent.name);
        const isPending   = !isActive && !isDone;

        return (
          <div
            key={agent.name}
            className={[
              "agent-row",
              isActive  ? "agent-row--active"  : "",
              isDone    ? "agent-row--done"    : "",
              isPending ? "agent-row--pending" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <span className="agent-icon" aria-hidden>
              {isDone ? "✓" : isActive ? "●" : "○"}
            </span>
            <span className="agent-name">{agent.name}</span>
            {isActive && (
              <span className="agent-status-label">{agent.label}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
