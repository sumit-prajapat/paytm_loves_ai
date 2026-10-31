import {
  BadgeIndianRupee, Crown, Database, Ear, GraduationCap, ListOrdered, Map, Search, ShieldCheck, Stethoscope,
  UserRoundCheck, Zap, type LucideIcon,
} from "lucide-react";
import type { AgentName, TraceStep } from "@/types/contracts";

export interface AgentMeta {
  name: AgentName;
  label: string;
  color: string;
  icon: LucideIcon;
  group: "care" | "travel" | "safety";
}

export const AGENTS: AgentMeta[] = [
  { name: "captain", label: "Captain", color: "#0A2463", icon: Crown, group: "safety" },
  { name: "listener", label: "Listener", color: "#7C3AED", icon: Ear, group: "care" },
  { name: "context", label: "Context", color: "#0891B2", icon: Database, group: "care" },
  { name: "diagnostician", label: "Diagnose", color: "#EA580C", icon: Stethoscope, group: "care" },
  { name: "action", label: "Action", color: "#16A34A", icon: Zap, group: "care" },
  { name: "offer", label: "Offer", color: "#DB2777", icon: BadgeIndianRupee, group: "care" },
  { name: "planner", label: "Planner", color: "#2563EB", icon: Map, group: "travel" },
  { name: "search", label: "Search", color: "#0EA5E9", icon: Search, group: "travel" },
  { name: "ranker", label: "Ranker", color: "#CA8A04", icon: ListOrdered, group: "travel" },
  { name: "guardian", label: "Guardian", color: "#DC2626", icon: ShieldCheck, group: "safety" },
  { name: "handoff", label: "Handoff", color: "#475569", icon: UserRoundCheck, group: "safety" },
  { name: "learner", label: "Learner", color: "#65A30D", icon: GraduationCap, group: "safety" },
];

export const AGENT_BY_NAME: Record<AgentName, AgentMeta> = Object.fromEntries(AGENTS.map((a) => [a.name, a])) as any;

/** Map a backend trace step to one of the 12 crew nodes shown in the UI. */
export function crewAgentFor(step: Pick<TraceStep, "agent" | "tool">): AgentName {
  if (step.tool === "match_playbook") return "learner";
  switch (step.agent) {
    case "llm_gateway":
      return step.tool === "llm_summarize" ? "handoff" : "listener";
    case "pulse":
      return "action";
    default:
      return (AGENT_BY_NAME as any)[step.agent] ? (step.agent as AgentName) : "captain";
  }
}

export const AGENT_VERB: Partial<Record<AgentName, string>> = {
  listener: "aapki baat samajh raha hai",
  context: "aapka account dekh raha hai",
  diagnostician: "check kar raha hai",
  guardian: "safety check kar raha hai",
  action: "jawab taiyaar kar raha hai",
  handoff: "team ko bhej raha hai",
  offer: "offer check kar raha hai",
  planner: "plan bana raha hai",
  search: "flights dhoondh raha hai",
  ranker: "options tol raha hai",
  learner: "pichhle cases dekh raha hai",
  captain: "kaam baant raha hai",
};
