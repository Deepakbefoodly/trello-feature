import { useEffect, useState } from "react";

/** Below this, a request is treated as instant and shows nothing at all. */
export const APPEAR_AFTER_MS = 400;

/**
 * Turns `true` only once `active` has held for `delayMs`, and `false` at once.
 *
 * A request that completes in 80ms would otherwise flash the loading bar on and
 * off, which reads as a glitch rather than as progress. Waiting first means
 * quick requests stay silent while slow ones — a cold-started free-tier API,
 * say — still explain themselves.
 */
export function useDelayedFlag(active: boolean, delayMs = APPEAR_AFTER_MS): boolean {
  const [elapsed, setElapsed] = useState(false);

  useEffect(() => {
    if (!active) return;

    const timer = setTimeout(() => setElapsed(true), delayMs);
    return () => {
      clearTimeout(timer);
      // Reset so the next spell of activity waits out the delay again rather
      // than appearing instantly on a stale flag.
      setElapsed(false);
    };
  }, [active, delayMs]);

  // Derived rather than stored: when `active` drops, this is false on the very
  // next render with no extra state update to cascade through.
  return active && elapsed;
}
