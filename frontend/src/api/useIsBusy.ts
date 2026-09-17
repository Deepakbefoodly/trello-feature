import { useIsFetching, useIsMutating } from "@tanstack/react-query";

/**
 * Tags the two move mutations so the loading indicator can ignore them.
 *
 * A move is applied optimistically — the board updates before the request is
 * even sent — so as far as the user is concerned it has already finished.
 * Flashing a loading bar afterwards would claim otherwise. A move that fails
 * announces itself by rolling back and raising a toast, which is the honest
 * signal.
 */
export const MOVE_MUTATION_KEY = ["move"] as const;

/**
 * True while any request the user is actually waiting on is in flight.
 *
 * Reads TanStack Query's global counters rather than threading loading state
 * through components, so every current and future request is covered without
 * touching its call site.
 */
export function useIsBusy(): boolean {
  const fetching = useIsFetching({
    // Only count fetches with nothing to show yet. A background revalidation of
    // data already on screen is not something the user is waiting on — and
    // every mutation triggers one by invalidating its board, so counting those
    // would put the bar back up a second after a drag had visibly finished,
    // defeating the exclusion below.
    predicate: (query) => query.state.data === undefined,
  });

  const mutating = useIsMutating({
    predicate: (mutation) => mutation.options.mutationKey?.[0] !== MOVE_MUTATION_KEY[0],
  });

  return fetching + mutating > 0;
}
