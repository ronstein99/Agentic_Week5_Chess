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
