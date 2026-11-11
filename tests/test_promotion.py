import json

import pytest

from computer import choose_move
from game import copy_position, legal_moves, move
from session import Session


def test_white_capture_promotion():
    session = Session()
    session.dispatch({"action": "promotion-setup"})
    legal = session.dispatch({"action": "legal", "source": "b7"})
    assert "a8" in legal["promotions"]
    session.play("b7", "a8", "Q")
    assert session.position[0]["a8"] == "wQ"
    assert session.position[1] == "b"
    session.play("g2", "h1", "N")
    assert session.position[0]["h1"] == "bN"
    assert "b7" in legal_moves(session.position, "a8")


@pytest.mark.parametrize("piece", list("QRBN"))
def test_chosen_piece_and_notation(piece):
    board = {"a1": "wK", "h6": "bK", "d7": "wP"}
    label = move([board, "w"], "d7", "d8", piece)
    assert board["d8"] == "w" + piece
    assert label.startswith("d7-d8=" + piece)


@pytest.mark.parametrize("choice", [None, "K", "P", "X"])
def test_promotion_needs_a_valid_choice(choice):
    position = [{"a1": "wK", "h6": "bK", "d7": "wP"}, "w"]
    before = copy_position(position)
    with pytest.raises(ValueError):
        move(position, "d7", "d8", choice)
    assert position == before


def test_computer_promotes():
    position = [{"a8": "wK", "e8": "bK", "h2": "bP"}, "b"]
    assert choose_move(position) == ("h2", "h1", "Q")


def test_choice_only_on_promotion():
    session = Session()
    with pytest.raises(ValueError):
        session.play("e2", "e4", "Q")


# Promotion with undo, captured pieces and save/load.

def capture_promotions(session):
    session.dispatch({"action": "promotion-setup"})
    session.dispatch({"action": "move", "source": "b7", "target": "a8", "promotion": "Q"})
    session.dispatch({"action": "move", "source": "g2", "target": "h1", "promotion": "N"})


def test_history_records_promotion():
    session = Session()
    capture_promotions(session)
    assert session.history[-2] == {"source": "b7", "target": "a8", "promotion": "Q",
                                   "captured": "bR", "label": "b7xa8=Q"}
    assert session.notation[-1] == "g2xh1=N"


def test_undo_promotion_restores_pawn_and_captured_piece():
    session = Session()
    capture_promotions(session)
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "undo"})
    board = session.position[0]
    assert board["b7"] == "wP" and board["a8"] == "bR"
    assert board["g2"] == "bP" and board["h1"] == "wR"
    assert session.captured == ["bP", "wP"]
    assert [r["label"] for r in session.redo] == ["g2xh1=N", "b7xa8=Q"]


def test_captured_shows_capture_not_promotion():
    session = Session()
    capture_promotions(session)
    # The rooks were captured; the promoted pawns are not shown as captured.
    assert session.captured == ["bP", "bR", "wP", "wR"]
    plain = Session()
    plain.position = [{"a1": "wK", "h6": "bK", "d7": "wP"}, "w"]
    plain.play("d7", "d8", "R")
    assert plain.captured == []


def test_save_and_load_keep_promotion():
    session = Session()
    capture_promotions(session)
    session.dispatch({"action": "undo"})
    game = json.loads(json.dumps(session.dispatch({"action": "save"})["game"]))
    loaded = Session()
    loaded.dispatch({"action": "load", "game": game})
    assert loaded.position == session.position and loaded.position[0]["a8"] == "wQ"
    assert loaded.redo == session.redo and loaded.redo[-1]["promotion"] == "N"


def test_load_rejects_missing_or_wrong_promotion():
    session = Session()
    capture_promotions(session)
    game = json.loads(json.dumps(session.dispatch({"action": "save"})["game"]))
    for choice in (None, "K"):
        game["history"][-1]["promotion"] = choice
        with pytest.raises(ValueError, match="not a valid game"):
            Session().dispatch({"action": "load", "game": game})


def test_computer_promotion_is_recorded():
    session = Session("computer")
    session.position = [{"a8": "wK", "e8": "bK", "h2": "bP", "a2": "wP"}, "b"]
    session.dispatch({"action": "computer-move"})
    assert session.history[-1]["promotion"] == "Q"
    assert session.position[0]["h1"] == "bQ"
