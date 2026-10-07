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
 *
 * Learner data belongs to the signed-in account, so the account is part of the cache key: after login,
 * logout or switching users the previous account's data is never shown (not even while refetching or
 * after a failed refetch).
 */
export function useApi<T>(path: string | null) {
  const account = useAuthStore((state) => state.user?.id ?? "guest");
  const key = path === null ? null : `${account}|${path}`;
  const [state, setState] = useState<State<T>>({ key: null, data: undefined, error: null, done: false });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (path === null || key === null) return;
    let cancelled = false;
    api<T>(path).then(
      (data) => {
        if (!cancelled) setState({ key, data, error: null, done: true });
      },
      (error: unknown) => {
        if (!cancelled) {
          setState((prev) => ({
            key,
            data: prev.key?.startsWith(`${account}|`) ? prev.data : undefined, // same account: keep last good data
            error: errorMessage(error),
            done: true,
          }));
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [path, key, account, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const mutate = useCallback((updater: (prev: T | undefined) => T | undefined) => {
    setState((prev) => ({ ...prev, data: updater(prev.data) }));
  }, []);

  const sameAccount = state.key?.startsWith(`${account}|`) ?? false;
  const data = sameAccount ? state.data : undefined;
  const loading = path !== null && (!state.done || state.key !== key) && data === undefined;
  return { data, error: sameAccount ? state.error : null, loading, reload, mutate };
}
