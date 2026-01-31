from dataclasses import dataclass, field
from typing import Dict, Set, Tuple
import logging

SCORING_TYPES = {"3PTR", "2PTR", "FT"}
TYPE_TO_DIGIT = {"3PTR": 3, "2PTR": 2, "FT": 1}

def compose_player_takeid(vh: str, stat_type: str, uni: str) -> int:
    team_digit = 1 if vh == "H" else 2
    stat_digit = TYPE_TO_DIGIT[stat_type]
    jersey = int(uni) if uni.isdigit() else 0
    return int(f"{team_digit}{stat_digit}{jersey:02d}")

@dataclass
class EngineState:
    enabled: bool = True
    processed_keys: Set[Tuple] = field(default_factory=set)
    burst_counts: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        "home": {"3PTR": 0, "2PTR": 0, "FT": 0},
        "away": {"3PTR": 0, "2PTR": 0, "FT": 0},
    })
    last_player_trigger_at: float = 0.0
    last_trigger_at: float = 0.0
    first_parse_done: bool = False
    startup_history_skipped: int = 0

    def reset_runtime_state(self):
        logging.info("Resetting runtime state - clearing %d processed plays", len(self.processed_keys))
        self.processed_keys.clear()
        self.burst_counts = {
            "home": {"3PTR": 0, "2PTR": 0, "FT": 0},
            "away": {"3PTR": 0, "2PTR": 0, "FT": 0},
        }
        self.last_player_trigger_at = 0.0
        self.last_trigger_at = 0.0
        self.first_parse_done = False
