"""Application actions and information shown beside the board."""

from computer import choose_move
from game import (
    legal_moves,
    move,
    new_position,
    status,
    winner,
)

# Legal from the standard starting position under this game's rules.
# Next move: b7-a8, capturing a rook and reaching the last rank.
PROMOTION_SETUP = [
    ("a2", "a4"), ("h7", "h5"),
    ("a4", "a5"), ("h5", "h4"),
    ("a5", "a6"), ("h4", "h3"),
    ("a6", "b7"), ("h3", "g2"),
]


SAVE_VERSION = 1


class Session:
    def __init__(self, opponent="human"):
        if opponent not in ("human", "computer"):
            raise ValueError("Unknown opponent")
        self.position = new_position()
        self.opponent = opponent
        # Shared move history (see README "Agreed shared design").
        # Each record: {"source", "target", "promotion", "captured", "label"}.
        self.history = []
        # Undone move records, most recently undone last.
        self.redo = []

    def reset(self, opponent="human"):
        """Start a new game: clears history and redo."""
        Session.__init__(self, opponent)

    @property
    def captured(self):
        """Pieces actually captured in the played continuation, as they were when taken.

        Derived from history, so undo, redo and load always match the board, and a
        promoted pawn is not counted as captured.
        """
        return sorted(record["captured"] for record in self.history if record["captured"])

    @property
    def notation(self):
        """Move labels of the currently played continuation."""
        return [record["label"] for record in self.history]

    def play(self, source, target):
        """Play a new move. A new move discards anything that could be redone."""
        self.apply(source, target)
        self.redo = []

    def apply(self, source, target, promotion=None):
        """Apply one move and append its record to history."""
        captured = self.position[0].get(target)
        # promotion is recorded but not used until feature/promotion is merged.
        label = move(self.position, source, target)
        self.history.append({"source": source, "target": target,
                             "promotion": promotion, "captured": captured,
                             "label": label})
        self.after_move()

    def replay(self, records):
        """Rebuild the position from the start by replaying move records.

        Keeps self.redo unchanged; callers (undo, redo, load) manage it.
        """
        self.position = new_position()
        self.history = []
        for record in records:
            self.apply(record["source"], record["target"], record["promotion"])

    def undo(self):
        """Take back the last move; against the computer, take back to White's turn.

        Against a person this undoes one move. Against the computer it undoes the
        computer's reply and your move (two records), so White is to move again; if the
        computer has not replied (e.g. your move ended the game), it undoes just yours.
        At the start of the game it does nothing. Undone records go onto self.redo.
        """
        if not self.history:
            return
        records = self.history[:]
        undone = [records.pop()]
        if self.opponent == "computer":
            while records and len(records) % 2:
                undone.append(records.pop())
        self.replay(records)
        # Most recently undone last: the earlier move goes on top.
        self.redo.extend(undone)

    def saved(self):
        """The game as saved to file: enough to rebuild it, undo and redo."""
        return {"version": SAVE_VERSION, "opponent": self.opponent,
                "history": self.history, "redo": self.redo}

    def restore(self, data):
        """Replace this game with saved data. On invalid data, nothing changes."""
        invalid = ValueError("The save file is not a valid game")
        if (not isinstance(data, dict) or data.get("version") != SAVE_VERSION
                or data.get("opponent") not in ("human", "computer")
                or not isinstance(data.get("history"), list)
                or not isinstance(data.get("redo"), list)
                or not all(isinstance(record, dict)
                           for record in data["history"] + data["redo"])):
            raise invalid
        opponent, history, redo = data["opponent"], data["history"], data["redo"]
        # Check every recorded move is legal, including the moves that could be
        # redone (most recently undone last, so they replay in reverse).
        scratch = Session(opponent)
        try:
            scratch.replay(history)
            for record in reversed(redo):
                scratch.apply(record["source"], record["target"], record["promotion"])
        except (KeyError, TypeError, ValueError) as error:
            raise invalid from error
        self.opponent = opponent
        self.replay(history)
        self.redo = list(redo)

    def after_move(self):
        pass

    def view(self):
        return {
            "board": self.position[0],
            "turn": self.position[1],
            "moves": self.notation,
            "opponent": self.opponent,
            "status": status(self.position),
            "winner": winner(self.position),
            **self.sidebar(),
        }

    def computer_to_move(self):
        return (self.opponent == "computer" and self.position[1] == "b"
                and status(self.position) not in ("checkmate", "stalemate"))

    def sidebar(self):
        return {"captured": self.captured}

    def dispatch(self, action):
        command = action.get("action")
        if command == "move":
            if self.computer_to_move():
                raise ValueError("Wait for the computer's move")
            self.play(action.get("source"), action.get("target"))
        elif command == "computer-move":
            if not self.computer_to_move():
                raise ValueError("It is not the computer's turn")
            self.play(*choose_move(self.position))
        elif command == "undo":
            self.undo()
        elif command == "legal":
            return {"targets": legal_moves(self.position, action.get("source"))}
        elif command == "new":
            self.reset(action.get("opponent", "human"))
        elif command == "save":
            # The browser writes this to a file the player chooses.
            return {"game": self.saved()}
        elif command == "load":
            # The browser sends the contents of a file the player chose.
            self.restore(action.get("game"))
        elif command == "promotion-setup":
            self.reset()
            for source, target in PROMOTION_SETUP:
                self.play(source, target)
        else:
            raise ValueError("Unknown action")
        return self.view()
