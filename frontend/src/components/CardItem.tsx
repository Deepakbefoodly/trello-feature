import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import type { Card } from "../api/types";

export function CardItem({
  card,
  index,
  onOpen,
}: {
  card: Card;
  index: number;
  onOpen: (card: Card) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({
      id: card.id,
      // The drop handler reads these to work out which list was targeted and at
      // what index, without having to search the board for the card again.
      data: { type: "card", listId: card.list_id, index },
    });

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      className={`card${isDragging ? " card--dragging" : ""}`}
      {...attributes}
      {...listeners}
      onClick={() => onOpen(card)}
    >
      <span className="card__title">{card.title}</span>
      {card.description && <span className="card__badge" aria-label="Has description" />}
    </li>
  );
}
