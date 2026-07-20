import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import type { Repository } from "../types";

export function useRepositoryPolling(id: string | null, intervalMs = 3000) {
  const [repo, setRepo] = useState<Repository | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetch = useCallback(async () => {
    if (!id) return;
    try {
      const data = await api.getRepository(id);
      setRepo(data);
      if (data.status === "ready" || data.status === "failed") {
        if (ref.current) clearInterval(ref.current);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to fetch");
      if (ref.current) clearInterval(ref.current);
    }
  }, [id]);

  useEffect(() => {
    if (!id) return;
    fetch();
    ref.current = setInterval(fetch, intervalMs);
    return () => { if (ref.current) clearInterval(ref.current); };
  }, [id, fetch, intervalMs]);

  return { repo, error };
}

export function useRepositories() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true); setError(null);
    try { setRepos(await api.listRepositories()); }
    catch (err: any) { setError(err?.response?.data?.detail ?? "Failed to fetch"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);
  return { repos, loading, error, refetch: fetch };
}
