from session import Session


def play_capture(session):
    session.play("e2", "e4")
    session.play("d7", "d5")
    session.play("e4", "d5")


def test_history_records_moves():
    session = Session()
    play_capture(session)
    assert session.history[-1] == {"source": "e4", "target": "d5",
                                   "promotion": None, "captured": "bP",
                                   "label": "e4xd5"}
    assert session.history[0]["captured"] is None
    assert session.view()["moves"] == ["e2-e4", "d7-d5", "e4xd5"]


def test_replay_rebuilds_same_game():
    original = Session()
    play_capture(original)
    rebuilt = Session()
    rebuilt.replay(original.history)
    assert rebuilt.position == original.position
    assert rebuilt.history == original.history
    assert rebuilt.notation == original.notation


def test_replay_prefix_restores_capture_and_turn():
    session = Session()
    play_capture(session)
    session.replay(session.history[:2])
    assert session.position[0]["d5"] == "bP"
    assert session.position[0]["e4"] == "wP"
    assert session.position[1] == "w"


def test_new_move_clears_redo_and_new_game_clears_all():
    session = Session()
    play_capture(session)
    session.redo = [{"source": "x"}]
    session.play("d8", "d5")
    assert session.redo == []
    session.dispatch({"action": "new"})
    assert session.history == [] and session.redo == []


def test_undo_restores_capture_turn_and_notation():
    session = Session()
    play_capture(session)
    view = session.dispatch({"action": "undo"})
    assert view["board"]["d5"] == "bP" and view["board"]["e4"] == "wP"
    assert view["turn"] == "w"
    assert view["moves"] == ["e2-e4", "d7-d5"]
    assert session.redo[-1]["label"] == "e4xd5"


def test_repeated_undo_reaches_start_then_does_nothing():
    session = Session()
    play_capture(session)
    for _ in range(3):
        session.dispatch({"action": "undo"})
    start = Session()
    assert session.position == start.position and session.history == []
    session.dispatch({"action": "undo"})
    assert session.position == start.position
    assert [r["label"] for r in session.redo] == ["e4xd5", "d7-d5", "e2-e4"]


def test_undo_against_computer_takes_back_reply_and_your_move():
    session = Session("computer")
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    session.dispatch({"action": "computer-move"})
    session.dispatch({"action": "move", "source": "d2", "target": "d4"})
    session.dispatch({"action": "computer-move"})
    view = session.dispatch({"action": "undo"})
    assert view["turn"] == "w" and len(view["moves"]) == 2
    # Redo order: your move is restored before the computer's reply.
    assert len(session.redo) == 2 and session.redo[-1]["label"] == "d2-d4"
    session.dispatch({"action": "undo"})
    assert session.history == [] and session.position == Session().position


def test_undo_against_computer_before_its_reply_takes_back_one():
    session = Session("computer")
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    view = session.dispatch({"action": "undo"})
    assert view["turn"] == "w" and view["moves"] == []
