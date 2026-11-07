import { useEffect, useRef, useState } from "react";
import { wsUrl } from "../api.jsx";

/**
 * Manage the server-side market snapshot WebSocket.
 *
 * The configured provider (Yahoo Finance) has no licensed realtime NSE feed,
 * so this socket carries polled snapshots. The hook reconnects with
 * exponential backoff and exposes connection state so the UI can be honest
 * about data freshness.
 */
export default function useMarketStream(symbol, timeframe = "1d", { enabled = true } = {}) {
  const [snapshot, setSnapshot] = useState(null);
  const [state, setState] = useState("idle"); // idle | connecting | open | reconnecting | closed
  const attemptRef = useRef(0);

  useEffect(() => {
    setSnapshot(null);
    if (!enabled || !symbol || import.meta.env.MODE === "test") {
      setState("idle");
      return undefined;
    }

    let cancelled = false;
    let socket = null;
    let retryTimer = null;

    const connect = () => {
      if (cancelled) return;
      setState(attemptRef.current === 0 ? "connecting" : "reconnecting");
      try {
        socket = new WebSocket(
          wsUrl(`/api/market/stream/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}`)
        );
      } catch {
        setState("closed");
        return;
      }

      socket.onopen = () => {
        if (cancelled) return;
        attemptRef.current = 0;
        setState("open");
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload?.type === "quote") setSnapshot(payload);
        } catch {
          /* ignore malformed frames */
        }
      };

      socket.onerror = () => {
        /* onclose drives retry */
      };

      socket.onclose = () => {
        if (cancelled) return;
        setState("reconnecting");
        const delay = Math.min(20000, 1000 * 2 ** Math.min(attemptRef.current, 4));
        attemptRef.current += 1;
        retryTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [symbol, timeframe, enabled]);

  return { snapshot, state, attempt: attemptRef.current };
}
