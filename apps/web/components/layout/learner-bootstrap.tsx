"use client";

import { useEffect } from "react";
import { useLearnerStore } from "@/lib/learner-store";
import { purgeLegacySecrets } from "@/lib/settings";

export function LearnerBootstrap() {
  useEffect(() => {
    const { refresh, loadAiStatus } = useLearnerStore.getState();
    void refresh();
    void loadAiStatus();
    purgeLegacySecrets();
    // keep streak / due counts fresh when the learner returns to the tab
    const onFocus = () => {
      if (document.visibilityState === "visible") void useLearnerStore.getState().refresh();
    };
    document.addEventListener("visibilitychange", onFocus);
    return () => document.removeEventListener("visibilitychange", onFocus);
  }, []);
  return null;
}
