import json

import pytest

from session import Session


def play_capture(session):
    session.play("e2", "e4")
    session.play("d7", "d5")
    session.play("e4", "d5")


def test_history_records_moves():
    session = Session()
    play_capture(session)
    assert session.history[-1] == {
        "source": "e4",
        "target": "d5",
        "promotion": None,
        "captured": "bP",
        "label": "e4xd5",
    }
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


# Undo.


def play_computer_game(session):
    """Two moves for each side against the computer, so White is to move."""
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    session.dispatch({"action": "computer-move"})
    session.dispatch({"action": "move", "source": "d2", "target": "d4"})
    session.dispatch({"action": "computer-move"})


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
    assert session.position == Session().position and session.history == []
    session.dispatch({"action": "undo"})
    assert session.position == Session().position
    assert [r["label"] for r in session.redo] == ["e4xd5", "d7-d5", "e2-e4"]


def test_undo_against_computer_takes_back_reply_and_your_move():
    session = Session("computer")
    play_computer_game(session)
    view = session.dispatch({"action": "undo"})
    assert view["turn"] == "w" and len(view["moves"]) == 2
    # Your move is redone before the computer's reply, so it goes on top.
    assert len(session.redo) == 2 and session.redo[-1]["label"] == "d2-d4"
    session.dispatch({"action": "undo"})
    assert session.history == [] and session.position == Session().position


def test_undo_against_computer_before_its_reply_takes_back_one():
    session = Session("computer")
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    view = session.dispatch({"action": "undo"})
    assert view["turn"] == "w" and view["moves"] == []


# Undo with save/load.


def save_and_load(session):
    """Save through JSON, as the browser does, and load into a fresh session."""
    game = json.loads(json.dumps(session.dispatch({"action": "save"})["game"]))
    loaded = Session()
    loaded.dispatch({"action": "load", "game": game})
    return loaded


def test_load_after_undo_keeps_game_and_redo():
    session = Session("computer")
    play_computer_game(session)
    session.dispatch({"action": "undo"})
    loaded = save_and_load(session)
    assert loaded.opponent == "computer"
    assert loaded.position == session.position
    assert loaded.history == session.history
    assert loaded.redo == session.redo


def test_undo_after_load_matches_undo_before_save():
    session = Session()
    play_capture(session)
    loaded = save_and_load(session)
    loaded.dispatch({"action": "undo"})
    session.dispatch({"action": "undo"})
    assert loaded.position == session.position
    assert loaded.notation == session.notation
    assert loaded.redo == session.redo
    assert loaded.position[0]["d5"] == "bP"


def test_undo_after_load_against_computer_takes_back_two():
    session = Session("computer")
    play_computer_game(session)
    loaded = save_and_load(session)
    view = loaded.dispatch({"action": "undo"})
    assert view["turn"] == "w" and len(view["moves"]) == 2
    assert loaded.redo[-1]["label"] == "d2-d4"


def test_undo_to_start_then_save_and_load():
    session = Session()
    play_capture(session)
    for _ in range(3):
        session.dispatch({"action": "undo"})
    loaded = save_and_load(session)
    assert loaded.history == [] and loaded.position == Session().position
    assert loaded.redo == session.redo
    loaded.dispatch({"action": "undo"})
    assert loaded.position == Session().position and loaded.redo == session.redo


# Rejected save files leave the current game unchanged.


def valid_save():
    session = Session()
    play_capture(session)
    session.dispatch({"action": "undo"})
    return session.dispatch({"action": "save"})["game"]


def corrupt(change):
    game = json.loads(json.dumps(valid_save()))
    change(game)
    return game


@pytest.mark.parametrize(
    "game",
    [
        None,
        [],
        corrupt(lambda g: g.update(version=2)),
        corrupt(lambda g: g.update(opponent="robot")),
        corrupt(lambda g: g.update(history="e2-e4")),
        corrupt(lambda g: g.update(redo=None)),
        corrupt(lambda g: g["history"].append("e2-e4")),
        corrupt(lambda g: g["history"][0].update(target="e5")),  # Illegal move.
        corrupt(lambda g: g["redo"][0].update(source="a1")),  # Illegal redo move.
        corrupt(lambda g: g["history"][0].pop("promotion")),  # Missing field.
    ],
)
def test_invalid_save_is_rejected_and_game_kept(game):
    session = Session("computer")
    session.play("e2", "e4")
    before = (session.opponent, session.position, list(session.history), list(session.redo))
    with pytest.raises(ValueError, match="not a valid game"):
        session.dispatch({"action": "load", "game": game})
    assert (session.opponent, session.position, session.history, session.redo) == before


# Other actions.


def test_legal_action_lists_targets():
    assert set(Session().dispatch({"action": "legal", "source": "g1"})["targets"]) == {"f3", "h3"}


def test_unknown_action_is_rejected():
    with pytest.raises(ValueError, match="Unknown action"):
        Session().dispatch({"action": "fly"})


def test_computer_turn_is_enforced():
    session = Session("computer")
    with pytest.raises(ValueError, match="not the computer's turn"):
        session.dispatch({"action": "computer-move"})
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    with pytest.raises(ValueError, match="Wait for the computer"):
        session.dispatch({"action": "move", "source": "d2", "target": "d4"})


def test_unknown_opponent_is_rejected():
    with pytest.raises(ValueError, match="Unknown opponent"):
        Session("robot")
