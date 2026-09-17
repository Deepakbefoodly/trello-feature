"""The reindex algorithm — the only code permitted to write `position`.

Positions are contiguous, 0-based integers within their parent scope: a list
holding n cards holds exactly the positions 0..n-1, with no gaps, duplicates or
negatives (spec invariants 1-2). Every function here leaves that true.

Cards and lists are ordered identically — only the scoping column differs — so
one implementation serves both, driven by each model's `__scope_attr__`.

Trade-off: a move rewrites up to n sibling rows rather than the single row a
fractional-rank scheme would touch. At board scale that cost is irrelevant, and
plain integers stay readable and debuggable in the database.
"""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models.base import Positioned
from app.models.board import Board


def lock_board(session: Session, board_id: UUID) -> None:
    """Take a write lock on the board before any structural change.

    Every create, delete and move within a board contends on this one row, which
    serialises concurrent mutations from two tabs into a defined order. Locking
    the individual card instead would leave the shifted sibling range
    unprotected, and two interleaved moves could produce duplicate positions.

    Must be called before the mutation, inside the request's transaction.
    """
    session.execute(select(Board.id).where(Board.id == board_id).with_for_update())


def count_in_scope(session: Session, model: type[Positioned], scope_id: UUID) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(model).where(model.scope_column() == scope_id)
        )
        or 0
    )


def next_position(session: Session, model: type[Positioned], scope_id: UUID) -> int:
    """Position for a newly created child: the end of the scope."""
    return count_in_scope(session, model, scope_id)


def _shift(
    session: Session,
    model: type[Positioned],
    scope_id: UUID,
    delta: int,
    *,
    low: int,
    high: int | None = None,
) -> None:
    """Add `delta` to every position in [low, high] within one scope.

    `high=None` means unbounded. Issued as one bulk UPDATE, which is only safe
    because the (scope, position) unique constraint is DEFERRABLE: rows pass
    through transiently duplicated positions before the statement completes.

    synchronize_session=False because objects already loaded in the session are
    expired by `move` once the writes are done; trying to keep them in step
    statement-by-statement would cost a query per shift for no benefit.
    """
    conditions = [model.scope_column() == scope_id, model.position >= low]
    if high is not None:
        conditions.append(model.position <= high)

    session.execute(
        update(model)
        .where(*conditions)
        .values(position=model.position + delta)
        .execution_options(synchronize_session=False)
    )


def move(
    session: Session,
    entity: Positioned,
    target_scope_id: UUID,
    new_position: int,
) -> None:
    """Move `entity` to `new_position`, optionally into a different scope.

    The caller must already hold the board lock and must have verified that the
    target scope belongs to the same board — this function does not re-check
    ownership, only ordering.
    """
    model = type(entity)
    source_scope_id = entity.scope_id
    old_position = entity.position
    same_scope = source_scope_id == target_scope_id

    # Within its own scope the entity already occupies a slot, so the last valid
    # index is count-1. Moving into another scope adds a row, so index == count
    # is legal and means "append to the end".
    sibling_count = count_in_scope(session, model, target_scope_id)
    highest = sibling_count - 1 if same_scope else sibling_count
    if not 0 <= new_position <= highest:
        raise ApiError.validation(f"position must be between 0 and {highest}", field="position")

    if same_scope:
        if new_position == old_position:
            return  # No-op: touch nothing.
        if new_position > old_position:
            # Everything the entity jumps over slides down one slot.
            _shift(session, model, source_scope_id, -1, low=old_position + 1, high=new_position)
        else:
            # Everything the entity jumps back over slides up one slot.
            _shift(session, model, source_scope_id, +1, low=new_position, high=old_position - 1)
    else:
        # Close the hole the entity leaves behind, then open one for it.
        _shift(session, model, source_scope_id, -1, low=old_position + 1)
        _shift(session, model, target_scope_id, +1, low=new_position)
        entity.scope_id = target_scope_id

    # In every branch the shifted range excludes the entity's own row, so its
    # position is set here exactly once.
    entity.position = new_position
    session.flush()
    # Siblings were moved by bulk UPDATE, so any of them already loaded in this
    # session hold stale positions. Expiring forces a re-read on next access.
    session.expire_all()


def close_gap(
    session: Session,
    model: type[Positioned],
    scope_id: UUID,
    removed_position: int,
) -> None:
    """Restore contiguity after a row is deleted from the middle of a scope."""
    _shift(session, model, scope_id, -1, low=removed_position + 1)
    session.flush()
    session.expire_all()
