/**
 * Optimistic reordering, applied to the cached board before the server replies.
 *
 * These must produce exactly the position vectors the server produces, or the
 * board will visibly jump when the real response arrives. The server shifts a
 * range of siblings by +/-1 (see backend/app/ordering.py); removing the item
 * and splicing it back in, then renumbering, is the same transformation
 * expressed more directly — and src/ordering.test.ts checks both against the
 * same cases the backend suite uses.
 *
 * Every function is pure and returns a new board, which is what lets TanStack
 * Query snapshot the previous value and roll back on error.
 */

import type { BoardDetail, Card } from "./api/types";

/** Renumber to 0..n-1, the server's contiguity invariant. */
function renumber<T extends { position: number }>(items: T[]): T[] {
  return items.map((item, index) => ({ ...item, position: index }));
}

function findCard(board: BoardDetail, cardId: string): Card | undefined {
  for (const list of board.lists) {
    const card = list.cards.find((candidate) => candidate.id === cardId);
    if (card) return card;
  }
  return undefined;
}

export function moveCard(
  board: BoardDetail,
  cardId: string,
  targetListId: string,
  position: number,
): BoardDetail {
  const card = findCard(board, cardId);
  const target = board.lists.find((list) => list.id === targetListId);

  // Unknown ids leave the board untouched rather than throwing: the drag
  // handler should never produce one, and a silent no-op is recoverable
  // whereas an exception inside an optimistic update is not.
  if (!card || !target) return board;

  // Detach from wherever it is, then insert. Done in that order so a move
  // within one list is not a special case.
  const lists = board.lists.map((list) => ({
    ...list,
    cards: list.cards.filter((candidate) => candidate.id !== cardId),
  }));

  const destination = lists.find((list) => list.id === targetListId)!;
  destination.cards.splice(position, 0, { ...card, list_id: targetListId });

  return {
    ...board,
    lists: lists.map((list) => ({ ...list, cards: renumber(list.cards) })),
  };
}

export function moveList(
  board: BoardDetail,
  listId: string,
  position: number,
): BoardDetail {
  const list = board.lists.find((candidate) => candidate.id === listId);
  if (!list) return board;

  const remaining = board.lists.filter((candidate) => candidate.id !== listId);
  remaining.splice(position, 0, list);

  return { ...board, lists: renumber(remaining) };
}
