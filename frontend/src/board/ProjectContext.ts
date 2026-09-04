import { createContext, useContext } from "react";

export interface ProjectRef {
  slug: string;
  path: string;
}

export const ProjectContext = createContext<ProjectRef | null>(null);

export function useProject(): ProjectRef {
  const project = useContext(ProjectContext);
  if (!project) throw new Error("useProject needs a Board above it.");
  return project;
}
