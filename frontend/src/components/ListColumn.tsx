import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useState, type FormEvent } from "react";

import type { BoardList, Card } from "../api/types";
import { CardItem } from "./CardItem";

interface Props {
  list: BoardList;
  onOpenCard: (card: Card) => void;
  onAddCard: (listId: string, title: string) => void;
  onRenameList: (listId: string, title: string) => void;
  onDeleteList: (listId: string) => void;
}

export function ListColumn({
  list,
  onOpenCard,
  onAddCard,
  onRenameList,
  onDeleteList,
}: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: list.id, data: { type: "list" } });

  const [draftCard, setDraftCard] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [draftTitle, setDraftTitle] = useState(list.title);

  function submitCard(event: FormEvent) {
    event.preventDefault();
    const trimmed = draftCard.trim();
    if (!trimmed) return;
    onAddCard(list.id, trimmed);
    setDraftCard("");
  }

  function submitRename(event: FormEvent) {
    event.preventDefault();
    const trimmed = draftTitle.trim();
    if (trimmed && trimmed !== list.title) onRenameList(list.id, trimmed);
    setIsRenaming(false);
  }

  return (
    <section
      ref={setNodeRef}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      className={`list${isDragging ? " list--dragging" : ""}`}
    >
      <header className="list__header">
        {isRenaming ? (
          <form onSubmit={submitRename}>
            <input
              aria-label="List title"
              autoFocus
              maxLength={100}
              value={draftTitle}
              onChange={(event) => setDraftTitle(event.target.value)}
              onBlur={submitRename}
            />
          </form>
        ) : (
          <>
            {/* The drag handle is the title, not the whole column: the column
                contains the card list, and making it all draggable would swallow
                the cards' own drag gestures. */}
            <h2 {...attributes} {...listeners} className="list__grip">
              {list.title}
            </h2>
            <div className="list__actions">
              <button type="button" onClick={() => setIsRenaming(true)}>
                Rename
              </button>
              <button
                type="button"
                className="danger"
                onClick={() => {
                  if (confirm(`Delete "${list.title}" and its ${list.cards.length} card(s)?`)) {
                    onDeleteList(list.id);
                  }
                }}
              >
                Delete
              </button>
            </div>
          </>
        )}
      </header>

      <SortableContext
        items={list.cards.map((card) => card.id)}
        strategy={verticalListSortingStrategy}
      >
        <ul className="list__cards">
          {list.cards.map((card, index) => (
            <CardItem key={card.id} card={card} index={index} onOpen={onOpenCard} />
          ))}
        </ul>
      </SortableContext>

      {list.cards.length === 0 && <p className="list__empty">No cards yet.</p>}

      <form className="composer" onSubmit={submitCard}>
        <input
          aria-label={`New card in ${list.title}`}
          placeholder="Add a card"
          maxLength={200}
          value={draftCard}
          onChange={(event) => setDraftCard(event.target.value)}
        />
        <button type="submit" disabled={!draftCard.trim()}>
          Add
        </button>
      </form>
    </section>
  );
}
