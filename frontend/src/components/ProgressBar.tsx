import { useIsBusy } from "../api/useIsBusy";
import { useDelayedFlag } from "./useDelayedFlag";

/**
 * A thin indeterminate bar across the top of the viewport while the app is
 * waiting on the API.
 *
 * Deliberately non-blocking: the board stays usable, which matters because
 * dragging is optimistic and must never be interrupted by a loading state.
 */
export function ProgressBar() {
  const isVisible = useDelayedFlag(useIsBusy());

  if (!isVisible) return null;

  return (
    <div className="progress" role="status" aria-label="Loading">
      <div className="progress__bar" />
    </div>
  );
}
