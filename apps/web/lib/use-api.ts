"use client";

import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

interface State<T> {
  key: string | null;
  data: T | undefined;
  error: string | null;
  done: boolean;
}

/**
 * Minimal SWR-style loader: keeps showing the previous data while reloading.
 * Pass `null` as path to skip fetching.
 */
export function useApi<T>(path: string | null) {
  const [state, setState] = useState<State<T>>({ key: null, data: undefined, error: null, done: false });
  const [nonce, setNonce] = useState(0);
  // Learner data belongs to the signed-in account: refetch after login/logout instead of keeping the guest's.
  const account = useAuthStore((state) => state.user?.id ?? null);

  useEffect(() => {
    if (path === null) return;
    let cancelled = false;
    api<T>(path).then(
      (data) => {
        if (!cancelled) setState({ key: path, data, error: null, done: true });
      },
      (error: unknown) => {
        if (!cancelled) setState((prev) => ({ ...prev, key: path, error: errorMessage(error), done: true }));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [path, nonce, account]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const mutate = useCallback((updater: (prev: T | undefined) => T | undefined) => {
    setState((prev) => ({ ...prev, data: updater(prev.data) }));
  }, []);

  const loading = path !== null && (!state.done || state.key !== path) && state.data === undefined;
  return { data: state.data, error: state.error, loading, reload, mutate };
}
