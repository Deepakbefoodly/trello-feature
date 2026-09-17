import { useEffect, useState, type FormEvent } from "react";

import type { Card } from "../api/types";

interface Props {
  card: Card;
  onSave: (changes: { title: string; description: string | null }) => void;
  onDelete: () => void;
  onClose: () => void;
}

export function CardModal({ card, onSave, onDelete, onClose }: Props) {
  const [title, setTitle] = useState(card.title);
  const [description, setDescription] = useState(card.description ?? "");

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) return;
    // Empty description is sent as null, matching how the server stores it.
    onSave({ title: trimmed, description: description.trim() ? description : null });
  }

  return (
    <div className="modal__backdrop" onClick={onClose}>
      <form
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Card details"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <label htmlFor="card-title">Title</label>
        <input
          id="card-title"
          autoFocus
          required
          maxLength={200}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />

        <label htmlFor="card-description">Description</label>
        <textarea
          id="card-description"
          rows={6}
          maxLength={5000}
          placeholder="Add more detail…"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />

        <div className="modal__actions">
          <button type="submit" disabled={!title.trim()}>
            Save
          </button>
          <button type="button" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="danger"
            onClick={() => {
              if (confirm("Delete this card?")) onDelete();
            }}
          >
            Delete
          </button>
        </div>
      </form>
    </div>
  );
}
