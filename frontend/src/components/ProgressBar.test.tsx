/**
 * The loading bar's two rules:
 *   - it waits before appearing, so fast requests never flash it;
 *   - it ignores optimistic moves, which are already on screen.
 */

import { QueryClient, QueryClientProvider, useMutation } from "@tanstack/react-query";
import { act, fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MOVE_MUTATION_KEY } from "../api/useIsBusy";
import { ProgressBar } from "./ProgressBar";

/** Never settles, so whatever started it stays in flight for the whole test. */
const pending = () => new Promise<string>(() => {});

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

/** A button that fires a mutation, optionally tagged as a move. */
function MutationButton({ asMove }: { asMove?: boolean }) {
  const mutation = useMutation({
    mutationKey: asMove ? MOVE_MUTATION_KEY : ["something-else"],
    mutationFn: pending,
  });

  return (
    <button type="button" onClick={() => mutation.mutate()}>
      start
    </button>
  );
}

function renderWith(client: QueryClient, children?: ReactNode) {
  return render(
    <QueryClientProvider client={client}>
      <ProgressBar />
      {children}
    </QueryClientProvider>,
  );
}

const bar = () => screen.queryByRole("status", { name: "Loading" });

/** Advance timers, flushing the promise callbacks React Query queues between. */
async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ProgressBar", () => {
  it("shows nothing when the app is idle", async () => {
    renderWith(makeClient());

    await advance(2000);

    expect(bar()).not.toBeInTheDocument();
  });

  it("stays hidden while a request is still within the delay window", async () => {
    const client = makeClient();
    client.fetchQuery({ queryKey: ["slow"], queryFn: pending });

    renderWith(client);
    await advance(300);

    // A request this quick should read as instant, not as a flicker.
    expect(bar()).not.toBeInTheDocument();
  });

  it("appears once a request outlasts the delay", async () => {
    const client = makeClient();
    client.fetchQuery({ queryKey: ["slow"], queryFn: pending });

    renderWith(client);
    await advance(500);

    expect(bar()).toBeInTheDocument();
  });

  it("appears for a normal mutation", async () => {
    renderWith(makeClient(), <MutationButton />);

    fireEvent.click(screen.getByRole("button", { name: "start" }));
    await advance(500);

    expect(bar()).toBeInTheDocument();
  });

  it("never appears for an optimistic move", async () => {
    renderWith(makeClient(), <MutationButton asMove />);

    fireEvent.click(screen.getByRole("button", { name: "start" }));
    await advance(3000);

    // The board already shows the move; claiming it is still pending would
    // contradict what the user just watched happen.
    expect(bar()).not.toBeInTheDocument();
  });

  it("stays hidden while data already on screen is revalidated", async () => {
    const client = makeClient();
    // Seed the cache, then refetch it — the shape of what happens after every
    // mutation, including the invalidation a drag triggers on settling.
    client.setQueryData(["board"], "already here");
    client.fetchQuery({ queryKey: ["board"], queryFn: pending });

    renderWith(client);
    await advance(3000);

    expect(bar()).not.toBeInTheDocument();
  });

  it("disappears as soon as the work finishes", async () => {
    const client = makeClient();
    let settle: (value: string) => void = () => {};
    client.fetchQuery({
      queryKey: ["slow"],
      queryFn: () => new Promise<string>((resolve) => (settle = resolve)),
    });

    renderWith(client);
    await advance(500);
    expect(bar()).toBeInTheDocument();

    await act(async () => {
      settle("done");
    });
    // React Query batches its cache notifications through a scheduler, so the
    // resulting re-render lands on a later tick than the resolve itself.
    await advance(1);

    expect(bar()).not.toBeInTheDocument();
  });
});
