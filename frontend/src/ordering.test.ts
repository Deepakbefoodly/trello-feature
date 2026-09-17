/**
 * The optimistic reducer must agree with the server exactly.
 *
 * The cases below are the same ones backend/tests/test_ordering.py asserts, so
 * a divergence between client and server shows up here rather than as a card
 * visibly jumping when the real response lands.
 */

import { describe, expect, it } from "vitest";

import type { BoardDetail, Card } from "./api/types";
import { moveCard, moveList } from "./ordering";

function card(id: string, listId: string, position: number): Card {
  return {
    id,
    list_id: listId,
    title: id,
    description: null,
    position,
    created_at: "",
    updated_at: "",
  };
}

/** 'todo' holds c0..c3; 'done' is empty — mirrors the backend fixture. */
function makeBoard(): BoardDetail {
  return {
    id: "b",
    title: "Sprint",
    created_at: "",
    updated_at: "",
    lists: [
      {
        id: "todo",
        board_id: "b",
        title: "Todo",
        position: 0,
        cards: [0, 1, 2, 3].map((index) => card(`c${index}`, "todo", index)),
      },
      { id: "done", board_id: "b", title: "Done", position: 1, cards: [] },
    ],
  };
}

const titles = (board: BoardDetail, listIndex: number) =>
  board.lists[listIndex].cards.map((item) => item.title);

const positions = (board: BoardDetail, listIndex: number) =>
  board.lists[listIndex].cards.map((item) => item.position);

function expectContiguous(board: BoardDetail) {
  expect(board.lists.map((list) => list.position)).toEqual(
    board.lists.map((_, index) => index),
  );
  for (const list of board.lists) {
    expect(list.cards.map((item) => item.position)).toEqual(
      list.cards.map((_, index) => index),
    );
  }
}

describe("moveCard within a list", () => {
  it.each([
    ["down", "c0", 2, ["c1", "c2", "c0", "c3"]],
    ["up", "c3", 1, ["c0", "c3", "c1", "c2"]],
    ["to first", "c2", 0, ["c2", "c0", "c1", "c3"]],
    ["to last", "c0", 3, ["c1", "c2", "c3", "c0"]],
    ["to its own position", "c1", 1, ["c0", "c1", "c2", "c3"]],
  ])("moves %s", (_name, cardId, position, expected) => {
    const result = moveCard(makeBoard(), cardId as string, "todo", position as number);

    expect(titles(result, 0)).toEqual(expected);
    expectContiguous(result);
  });

  it("renumbers positions to stay contiguous", () => {
    const result = moveCard(makeBoard(), "c0", "todo", 2);

    expect(positions(result, 0)).toEqual([0, 1, 2, 3]);
  });
});

describe("moveCard across lists", () => {
  it("closes the gap in the source list", () => {
    const result = moveCard(makeBoard(), "c1", "done", 0);

    expect(titles(result, 0)).toEqual(["c0", "c2", "c3"]);
    expect(titles(result, 1)).toEqual(["c1"]);
    expectContiguous(result);
  });

  it.each([
    [0, ["c0", "d0", "d1"]],
    [1, ["d0", "c0", "d1"]],
    [2, ["d0", "d1", "c0"]],
  ])("inserts at index %i of a populated list", (position, expected) => {
    const board = makeBoard();
    board.lists[1].cards = [card("d0", "done", 0), card("d1", "done", 1)];

    const result = moveCard(board, "c0", "done", position as number);

    expect(titles(result, 1)).toEqual(expected);
    expect(titles(result, 0)).toEqual(["c1", "c2", "c3"]);
    expectContiguous(result);
  });

  it("rewrites the moved card's list_id", () => {
    const result = moveCard(makeBoard(), "c0", "done", 0);

    expect(result.lists[1].cards[0].list_id).toBe("done");
  });
});

describe("moveList", () => {
  it.each([
    [2, 0, ["Archive", "Todo", "Done"]],
    [0, 2, ["Done", "Archive", "Todo"]],
    [0, 1, ["Done", "Todo", "Archive"]],
  ])("moves list %i to %i", (from, to, expected) => {
    const board = makeBoard();
    board.lists.push({
      id: "archive",
      board_id: "b",
      title: "Archive",
      position: 2,
      cards: [],
    });

    const result = moveList(board, board.lists[from as number].id, to as number);

    expect(result.lists.map((list) => list.title)).toEqual(expected);
    expectContiguous(result);
  });

  it("carries the list's cards with it", () => {
    const result = moveList(makeBoard(), "todo", 1);

    expect(titles(result, 1)).toEqual(["c0", "c1", "c2", "c3"]);
  });
});

describe("purity", () => {
  it("does not mutate the board it is given", () => {
    const board = makeBoard();
    const snapshot = structuredClone(board);

    moveCard(board, "c0", "done", 0);
    moveList(board, "todo", 1);

    expect(board).toEqual(snapshot);
  });

  it("returns the board unchanged for an unknown card", () => {
    const board = makeBoard();

    expect(moveCard(board, "missing", "todo", 0)).toEqual(board);
    expect(moveList(board, "missing", 0)).toEqual(board);
  });
});
