from session import Session


def test_display_after_capture_and_new_game() -> None:
    session = Session()
    assert session.view()["captured"] == []
    session.play("e2", "e4")
    session.play("d7", "d5")
    session.play("e4", "d5")
    assert session.view()["captured"] == ["bP"]
    session.dispatch({"action": "new"})
    assert session.view()["captured"] == []


def test_undo_removes_capture_from_display() -> None:
    session = Session()
    session.play("e2", "e4")
    session.play("d7", "d5")
    session.play("e4", "d5")
    session.dispatch({"action": "undo"})
    assert session.view()["captured"] == []


def test_display_matches_loaded_game() -> None:
    session = Session()
    session.play("e2", "e4")
    session.play("d7", "d5")
    session.play("e4", "d5")
    session.play("d8", "d5")
    saved = session.dispatch({"action": "save"})["game"]
    loaded = Session()
    loaded.dispatch({"action": "load", "game": saved})
    assert loaded.view()["captured"] == ["bP", "wP"]
    # Loading a game with no moves clears a previous game's captures.
    empty = {**saved, "history": [], "redo": []}
    loaded.dispatch({"action": "load", "game": empty})
    assert loaded.view()["captured"] == []


def test_captured_counts_only_history_captures() -> None:
    session = Session()
    session.play("e2", "e4")
    # A piece missing from the board without a recorded capture (as after a
    # promotion) is not shown as captured.
    del session.position[0]["a7"]
    assert session.view()["captured"] == []
