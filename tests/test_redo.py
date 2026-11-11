"""Redo: restoring undone moves, alone and with save/load, promotion and the computer."""

import json

import pytest

from session import Session


def snapshot(session: Session) -> tuple[str, list[str], list[str], str]:
    """Everything the player sees: board, move list, captured pieces and turn."""
    view = session.view()
    return json.dumps(view["board"], sort_keys=True), view["moves"], view["captured"], view["turn"]


def play_capture(session: Session) -> None:
    session.play("e2", "e4")
    session.play("d7", "d5")
    session.play("e4", "d5")


def capture_promotions(session: Session) -> None:
    """Both sides capture a rook while promoting, to a knight and a bishop."""
    session.dispatch({"action": "promotion-setup"})
    session.dispatch({"action": "move", "source": "b7", "target": "a8", "promotion": "N"})
    session.dispatch({"action": "move", "source": "g2", "target": "h1", "promotion": "B"})


def play_computer_game(session: Session) -> None:
    """Two moves for each side against the computer, so White is to move."""
    for source, target in (("e2", "e4"), ("d2", "d4")):
        session.dispatch({"action": "move", "source": source, "target": target})
        session.dispatch({"action": "computer-move"})


def save_and_load(session: Session) -> Session:
    """Save through JSON, as the browser does, and load into a fresh session."""
    game = json.loads(json.dumps(session.dispatch({"action": "save"})["game"]))
    loaded = Session()
    loaded.dispatch({"action": "load", "game": game})
    return loaded


def test_redo_restores_a_capture() -> None:
    session = Session()
    play_capture(session)
    before = snapshot(session)
    session.dispatch({"action": "undo"})
    view = session.dispatch({"action": "redo"})
    assert snapshot(session) == before
    assert view["captured"] == ["bP"] and view["moves"][-1] == "e4xd5"
    assert session.redo == []


def test_redo_restores_promotions_and_chosen_pieces() -> None:
    session = Session()
    capture_promotions(session)
    before = snapshot(session)
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "undo"})
    assert session.position[0]["a8"] == "bR"
    session.dispatch({"action": "redo"})
    session.dispatch({"action": "redo"})
    assert snapshot(session) == before
    assert session.position[0]["a8"] == "wN" and session.position[0]["h1"] == "bB"
    assert session.notation[-2:] == ["b7xa8=N", "g2xh1=B"]


def test_redo_steps_forward_one_move_at_a_time() -> None:
    session = Session()
    play_capture(session)
    for _ in range(3):
        session.dispatch({"action": "undo"})
    for expected in (["e2-e4"], ["e2-e4", "d7-d5"], ["e2-e4", "d7-d5", "e4xd5"]):
        assert session.dispatch({"action": "redo"})["moves"] == expected


def test_redo_with_nothing_to_redo_does_nothing() -> None:
    session = Session()
    assert session.dispatch({"action": "redo"})["moves"] == []
    play_capture(session)
    before = snapshot(session)
    session.dispatch({"action": "redo"})
    assert snapshot(session) == before


def test_undo_save_load_redo() -> None:
    session = Session()
    capture_promotions(session)
    before = snapshot(session)
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "undo"})
    loaded = save_and_load(session)
    assert loaded.redo == session.redo
    loaded.dispatch({"action": "redo"})
    loaded.dispatch({"action": "redo"})
    assert snapshot(loaded) == before


def test_different_move_after_undo_discards_redo() -> None:
    session = Session()
    play_capture(session)
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "move", "source": "e7", "target": "e5"})
    assert session.redo == []
    before = snapshot(session)
    session.dispatch({"action": "redo"})
    assert snapshot(session) == before


def test_same_move_after_undo_keeps_the_rest_of_redo() -> None:
    session = Session()
    play_capture(session)
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "move", "source": "d7", "target": "d5"})
    assert [record["label"] for record in session.redo] == ["e4xd5"]
    session.dispatch({"action": "redo"})
    assert session.notation == ["e2-e4", "d7-d5", "e4xd5"]


def test_same_squares_with_another_promotion_discard_redo() -> None:
    session = Session()
    capture_promotions(session)
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "move", "source": "g2", "target": "h1", "promotion": "Q"})
    assert session.redo == []


def test_new_game_clears_undo_and_redo() -> None:
    session = Session()
    play_capture(session)
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "new", "opponent": "computer"})
    assert session.history == [] and session.redo == []
    assert session.dispatch({"action": "redo"})["moves"] == []


def test_redo_against_computer_restores_your_move_and_its_reply() -> None:
    session = Session("computer")
    play_computer_game(session)
    before = snapshot(session)
    session.dispatch({"action": "undo"})
    view = session.dispatch({"action": "redo"})
    assert snapshot(session) == before
    assert view["turn"] == "w" and len(view["moves"]) == 4
    assert not session.computer_to_move()


def test_redo_against_computer_after_undo_to_start() -> None:
    session = Session("computer")
    play_computer_game(session)
    before = snapshot(session)
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "undo"})
    assert session.dispatch({"action": "redo"})["moves"] == before[1][:2]
    session.dispatch({"action": "redo"})
    assert snapshot(session) == before


def test_redo_against_computer_survives_save_and_load() -> None:
    session = Session("computer")
    play_computer_game(session)
    before = snapshot(session)
    session.dispatch({"action": "undo"})
    loaded = save_and_load(session)
    loaded.dispatch({"action": "redo"})
    assert loaded.opponent == "computer"
    assert snapshot(loaded) == before


def test_redo_against_computer_without_recorded_reply() -> None:
    # Your move ended up undone before the computer replied: redo restores only it,
    # and the computer then answers.
    session = Session("computer")
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "redo"})
    assert session.notation == ["e2-e4"] and session.computer_to_move()
    session.dispatch({"action": "computer-move"})
    assert len(session.notation) == 2


def test_failed_redo_keeps_the_record() -> None:
    session = Session()
    session.play("e2", "e4")
    session.dispatch({"action": "undo"})
    session.play("d2", "d4")
    # A record that no longer fits the position (e2 is empty).
    session.redo = [
        {"source": "e2", "target": "e5", "promotion": None, "captured": None, "label": "e2-e5"}
    ]
    before = snapshot(session)
    with pytest.raises(ValueError):
        session.dispatch({"action": "redo"})
    assert snapshot(session) == before and len(session.redo) == 1
