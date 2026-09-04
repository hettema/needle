import { createContext, useContext } from "react";
import type { WatercoolerLine } from "../types/watercooler";

export interface ProjectRef {
  slug: string;
  path: string;
  /** The watercooler's last line, shown on every card with hands on it (plan 07, item 2). */
  heard: WatercoolerLine | null;
}

export const ProjectContext = createContext<ProjectRef | null>(null);

export function useProject(): ProjectRef {
  const project = useContext(ProjectContext);
  if (!project) throw new Error("useProject needs a Board above it.");
  return project;
}
