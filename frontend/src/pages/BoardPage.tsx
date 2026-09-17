import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  horizontalListSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import { useCallback, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import {
  useBoard,
  useCreateCard,
  useCreateList,
  useDeleteCard,
  useDeleteList,
  useMoveCard,
  useMoveList,
  useRenameList,
  useUpdateCard,
} from "../api/queries";
import type { Card } from "../api/types";
import { CardModal } from "../components/CardModal";
import { ListColumn } from "../components/ListColumn";
import { Toast } from "../components/Toast";

export function BoardPage() {
  const { boardId = "" } = useParams();
  const { data: board, isPending, error } = useBoard(boardId);

  const [toast, setToast] = useState<string | null>(null);
  const [openCard, setOpenCard] = useState<Card | null>(null);
  const [draftList, setDraftList] = useState("");

  const showError = useCallback((message: string) => setToast(message), []);

  const moveCard = useMoveCard(boardId, showError);
  const moveList = useMoveList(boardId, showError);
  const createList = useCreateList(boardId);
  const renameList = useRenameList(boardId);
  const deleteList = useDeleteList(boardId);
  const createCard = useCreateCard(boardId);
  const updateCard = useUpdateCard(boardId);
  const deleteCard = useDeleteCard(boardId);

  const sensors = useSensors(
    // A small distance threshold so a plain click still opens the card instead
    // of being swallowed as the start of a drag.
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    // Keyboard dragging is part of dnd-kit and is deliberately left enabled.
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragEnd({ active, over }: DragEndEvent) {
    if (!over || !board) return;

    const dragged = active.data.current;
    const target = over.data.current;
    if (!dragged) return;

    if (dragged.type === "list") {
      // A list can be dropped over another list, or over a card inside one.
      const targetListId =
        target?.type === "list" ? String(over.id) : (target?.listId as string | undefined);
      if (!targetListId || targetListId === active.id) return;

      const position = board.lists.findIndex((list) => list.id === targetListId);
      if (position >= 0) moveList.mutate({ listId: String(active.id), position });
      return;
    }

    const sourceListId = dragged.listId as string;
    const targetListId =
      target?.type === "card" ? (target.listId as string) : String(over.id);
    const targetList = board.lists.find((list) => list.id === targetListId);
    if (!targetList) return;

    const sameList = sourceListId === targetListId;

    // Dropped on a card: take that card's slot. Dropped on the column itself:
    // append. Within its own list the card already occupies a slot, so the last
    // index is one lower — the same rule the server enforces.
    const position =
      target?.type === "card"
        ? (target.index as number)
        : Math.max(0, targetList.cards.length - (sameList ? 1 : 0));

    if (sameList && position === dragged.index) return;

    moveCard.mutate({ cardId: String(active.id), targetListId, position });
  }

  function handleAddList(event: FormEvent) {
    event.preventDefault();
    const trimmed = draftList.trim();
    if (!trimmed) return;
    createList.mutate(trimmed, { onSuccess: () => setDraftList("") });
  }

  if (isPending) return <p className="state">Loading board…</p>;

  if (error) {
    const missing = error instanceof ApiError && error.status === 404;
    return (
      <div className="state state--error">
        <p>{missing ? "That board does not exist." : "Could not load this board."}</p>
        <Link to="/boards">Back to your boards</Link>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <Link to="/boards" className="back">
            ← Boards
          </Link>
          <h1>{board.title}</h1>
        </div>
      </header>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragEnd={handleDragEnd}
      >
        <div className="board">
          <SortableContext
            items={board.lists.map((list) => list.id)}
            strategy={horizontalListSortingStrategy}
          >
            {board.lists.map((list) => (
              <ListColumn
                key={list.id}
                list={list}
                onOpenCard={setOpenCard}
                onAddCard={(listId, title) => createCard.mutate({ listId, title })}
                onRenameList={(listId, title) => renameList.mutate({ listId, title })}
                onDeleteList={(listId) => deleteList.mutate(listId)}
              />
            ))}
          </SortableContext>

          <form className="composer composer--list" onSubmit={handleAddList}>
            {board.lists.length === 0 && (
              <p className="list__empty">This board is empty — add your first list.</p>
            )}
            <input
              aria-label="New list title"
              placeholder="Add a list"
              maxLength={100}
              value={draftList}
              onChange={(event) => setDraftList(event.target.value)}
            />
            <button type="submit" disabled={!draftList.trim()}>
              Add list
            </button>
          </form>
        </div>
      </DndContext>

      {openCard && (
        <CardModal
          card={openCard}
          onSave={(changes) => {
            updateCard.mutate({ cardId: openCard.id, ...changes });
            setOpenCard(null);
          }}
          onDelete={() => {
            deleteCard.mutate(openCard.id);
            setOpenCard(null);
          }}
          onClose={() => setOpenCard(null)}
        />
      )}

      <Toast message={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
