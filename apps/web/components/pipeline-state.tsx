"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type StageTone = "neutral" | "success" | "attention" | "error" | "running";
export type PipelineStageState = { tone: StageTone; status: string };
const PipelineContext = createContext<{ stages: Record<number, PipelineStageState>; register: (number: number, state: PipelineStageState) => void } | null>(null);

export function PipelineStateProvider({ children }: { children: React.ReactNode }) {
  const [stages, setStages] = useState<Record<number, PipelineStageState>>({});
  const register = useCallback((number: number, state: PipelineStageState) => {
    setStages(current => current[number]?.tone === state.tone && current[number]?.status === state.status ? current : { ...current, [number]: state });
  }, []);
  return <PipelineContext.Provider value={{ stages, register }}>{children}</PipelineContext.Provider>;
}

export function usePipelineState() { return useContext(PipelineContext); }
export function useRegisterStage(number: number, tone: StageTone, status: string) {
  const register = usePipelineState()?.register;
  useEffect(() => { register?.(number, { tone, status }); }, [register, number, tone, status]);
}

export function navigateStage(number: number) {
  window.location.hash = `workflow-step-${number}`;
  window.dispatchEvent(new Event(`open-workflow-step-${number}`));
}
