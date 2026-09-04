import { createContext, useContext } from "react";
import type { Place } from "../types/card";
import type { Lift, StepKey } from "./dnd";

export interface LiftController {
  lift: Lift | null;
  start: (number: number, from: Place, by: Lift["by"]) => void;
  retarget: (target: Place) => void;
  step: (key: StepKey) => void;
  drop: () => void;
  cancel: () => void;
}

export const LiftContext = createContext<LiftController | null>(null);

export function useLift(): LiftController {
  const controller = useContext(LiftContext);
  if (!controller) throw new Error("useLift needs a Board above it.");
  return controller;
}
