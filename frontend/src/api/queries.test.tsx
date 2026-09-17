/**
 * The optimistic move must be undone when the server rejects it.
 *
 * Without the rollback the UI keeps showing a card in a position the database
 * does not have, which is the most confusing possible failure for this product.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "./client";
import { useMoveCard } from "./queries";
import type { BoardDetail } from "./types";

const BOARD_ID = "b";
const boardKey = ["board", BOARD_ID];

function makeBoard(): BoardDetail {
  return {
    id: BOARD_ID,
    title: "Sprint",
    created_at: "",
    updated_at: "",
    lists: [
      {
        id: "todo",
        board_id: BOARD_ID,
        title: "Todo",
        position: 0,
        cards: [0, 1, 2].map((index) => ({
          id: `c${index}`,
          list_id: "todo",
          title: `c${index}`,
          description: null,
          position: index,
          created_at: "",
          updated_at: "",
        })),
      },
    ],
  };
}

function setup() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  queryClient.setQueryData(boardKey, makeBoard());

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

const titles = (board: BoardDetail) => board.lists[0].cards.map((card) => card.title);

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("useMoveCard", () => {
  it("applies the move to the cache before the server replies", async () => {
    const { queryClient, wrapper } = setup();
    // Never settles, so the cache is observed mid-flight.
    vi.spyOn(api, "post").mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useMoveCard(BOARD_ID, vi.fn()), { wrapper });
    result.current.mutate({ cardId: "c0", targetListId: "todo", position: 2 });

    await waitFor(() => {
      expect(titles(queryClient.getQueryData<BoardDetail>(boardKey)!)).toEqual([
        "c1",
        "c2",
        "c0",
      ]);
    });
  });

  it("restores the previous board when the server rejects the move", async () => {
    const { queryClient, wrapper } = setup();
    const before = queryClient.getQueryData<BoardDetail>(boardKey)!;
    vi.spyOn(api, "post").mockRejectedValue(
      new ApiError(400, "VALIDATION_ERROR", "position must be between 0 and 2"),
    );
    const onError = vi.fn();

    const { result } = renderHook(() => useMoveCard(BOARD_ID, onError), { wrapper });
    result.current.mutate({ cardId: "c0", targetListId: "todo", position: 9 });

    await waitFor(() => expect(onError).toHaveBeenCalled());
    expect(queryClient.getQueryData<BoardDetail>(boardKey)).toEqual(before);
  });

  it("reports the server's message so the rollback can be explained", async () => {
    const { wrapper } = setup();
    vi.spyOn(api, "post").mockRejectedValue(
      new ApiError(400, "VALIDATION_ERROR", "position must be between 0 and 2"),
    );
    const onError = vi.fn();

    const { result } = renderHook(() => useMoveCard(BOARD_ID, onError), { wrapper });
    result.current.mutate({ cardId: "c0", targetListId: "todo", position: 9 });

    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith("position must be between 0 and 2"),
    );
  });
});
