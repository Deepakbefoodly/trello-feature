/**
 * TanStack Query hooks.
 *
 * Board mutations invalidate the board query so the server stays authoritative.
 * The two move hooks additionally apply the change optimistically and roll back
 * on error — without that rollback a rejected move would leave a card sitting
 * in a position the database does not have.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { moveCard, moveList } from "../ordering";
import { api } from "./client";
import { MOVE_MUTATION_KEY } from "./useIsBusy";
import type { Board, BoardDetail, BoardList, Card } from "./types";

const boardsKey = ["boards"] as const;
const boardKey = (boardId: string) => ["board", boardId] as const;

export function useBoards() {
  return useQuery({ queryKey: boardsKey, queryFn: () => api.get<Board[]>("/boards") });
}

export function useBoard(boardId: string) {
  return useQuery({
    queryKey: boardKey(boardId),
    queryFn: () => api.get<BoardDetail>(`/boards/${boardId}`),
  });
}

export function useCreateBoard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (title: string) => api.post<Board>("/boards", { title }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: boardsKey }),
  });
}

export function useDeleteBoard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (boardId: string) => api.remove(`/boards/${boardId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: boardsKey }),
  });
}

/** Invalidates one board — the shape every list and card mutation needs. */
function useBoardMutation<TVariables, TResult>(
  boardId: string,
  mutationFn: (variables: TVariables) => Promise<TResult>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: boardKey(boardId) }),
  });
}

export function useCreateList(boardId: string) {
  return useBoardMutation(boardId, (title: string) =>
    api.post<BoardList>(`/boards/${boardId}/lists`, { title }),
  );
}

export function useRenameList(boardId: string) {
  return useBoardMutation(boardId, ({ listId, title }: { listId: string; title: string }) =>
    api.patch<BoardList>(`/lists/${listId}`, { title }),
  );
}

export function useDeleteList(boardId: string) {
  return useBoardMutation(boardId, (listId: string) => api.remove(`/lists/${listId}`));
}

export function useCreateCard(boardId: string) {
  return useBoardMutation(boardId, ({ listId, title }: { listId: string; title: string }) =>
    api.post<Card>(`/lists/${listId}/cards`, { title }),
  );
}

export function useUpdateCard(boardId: string) {
  return useBoardMutation(
    boardId,
    ({
      cardId,
      ...changes
    }: {
      cardId: string;
      title?: string;
      description?: string | null;
    }) => api.patch<Card>(`/cards/${cardId}`, changes),
  );
}

export function useDeleteCard(boardId: string) {
  return useBoardMutation(boardId, (cardId: string) => api.remove(`/cards/${cardId}`));
}

/** Snapshot held between onMutate and onError so a failure can be undone. */
interface Rollback {
  previous: BoardDetail | undefined;
}

interface MoveCardVariables {
  cardId: string;
  targetListId: string;
  position: number;
}

export function useMoveCard(boardId: string, onError: (message: string) => void) {
  const queryClient = useQueryClient();
  const key = boardKey(boardId);

  return useMutation<BoardDetail, Error, MoveCardVariables, Rollback>({
    // Tagged so the global loading bar ignores it: the move is already visible
    // on screen, so announcing it as pending would contradict what the user
    // just saw happen.
    mutationKey: MOVE_MUTATION_KEY,
    mutationFn: ({ cardId, targetListId, position }) =>
      api.post<BoardDetail>(`/cards/${cardId}/move`, {
        target_list_id: targetListId,
        position,
      }),

    onMutate: async ({ cardId, targetListId, position }) => {
      // An in-flight refetch could otherwise land after the optimistic write
      // and overwrite it with pre-move data.
      await queryClient.cancelQueries({ queryKey: key });

      const previous = queryClient.getQueryData<BoardDetail>(key);
      if (previous) {
        queryClient.setQueryData(key, moveCard(previous, cardId, targetListId, position));
      }
      return { previous };
    },

    onError: (error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
      onError(error.message);
    },

    onSettled: () => queryClient.invalidateQueries({ queryKey: key }),
  });
}

interface MoveListVariables {
  listId: string;
  position: number;
}

export function useMoveList(boardId: string, onError: (message: string) => void) {
  const queryClient = useQueryClient();
  const key = boardKey(boardId);

  return useMutation<BoardDetail, Error, MoveListVariables, Rollback>({
    mutationKey: MOVE_MUTATION_KEY,
    mutationFn: ({ listId, position }) =>
      api.post<BoardDetail>(`/lists/${listId}/move`, { position }),

    onMutate: async ({ listId, position }) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<BoardDetail>(key);
      if (previous) {
        queryClient.setQueryData(key, moveList(previous, listId, position));
      }
      return { previous };
    },

    onError: (error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
      onError(error.message);
    },

    onSettled: () => queryClient.invalidateQueries({ queryKey: key }),
  });
}
