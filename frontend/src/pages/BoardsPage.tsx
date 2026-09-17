import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { useBoards, useCreateBoard, useDeleteBoard } from "../api/queries";
import { useAuth } from "../auth/context";

export function BoardsPage() {
  const { user, signOut } = useAuth();
  const { data: boards, isPending, isError } = useBoards();
  const createBoard = useCreateBoard();
  const deleteBoard = useDeleteBoard();
  const [title, setTitle] = useState("");

  function handleCreate(event: FormEvent) {
    event.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) return;
    createBoard.mutate(trimmed, { onSuccess: () => setTitle("") });
  }

  return (
    <div className="page">
      <header className="page__header">
        <h1>Boards</h1>
        <div className="page__account">
          <span>{user?.email}</span>
          <button type="button" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>

      <form className="composer composer--inline" onSubmit={handleCreate}>
        <input
          aria-label="New board title"
          placeholder="New board title"
          maxLength={100}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <button type="submit" disabled={!title.trim() || createBoard.isPending}>
          Create board
        </button>
      </form>

      {isPending && <p className="state">Loading your boards…</p>}
      {isError && <p className="state state--error">Could not load your boards.</p>}

      {boards && boards.length === 0 && (
        <p className="state">No boards yet. Create your first one above.</p>
      )}

      {boards && boards.length > 0 && (
        <ul className="board-grid">
          {boards.map((board) => (
            <li key={board.id} className="board-card">
              <Link to={`/boards/${board.id}`}>{board.title}</Link>
              <button
                type="button"
                className="danger"
                onClick={() => {
                  if (confirm(`Delete "${board.title}" and everything on it?`)) {
                    deleteBoard.mutate(board.id);
                  }
                }}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
