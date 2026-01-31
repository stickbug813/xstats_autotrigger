from dataclasses import dataclass, field
from typing import Dict
import yaml
import logging
import os

@dataclass
class XPressionCfg:
    host: str
    port: int = 7788

@dataclass
class PlayerCfg:
    auto_takeoff_seconds: int = 6
    focus_mode: str = "on_take"  # on_take | before_take | off

@dataclass
class TeamBurstCfg:
    enabled: bool = True
    delay_after_player_seconds: float = 1.5
    auto_takeoff_seconds: int = 6
    thresholds: Dict[str, int] = field(default_factory=lambda: {
        "3PTR": 3, "2PTR": 3, "FT": 3
    })
    take_ids: Dict[str, Dict[str, int]] = field(default_factory=dict)

@dataclass
class TypesCfg:
    aliases: Dict[str, str] = field(default_factory=dict)
    player_enabled: Dict[str, bool] = field(default_factory=dict)
    bursts_enabled: Dict[str, bool] = field(default_factory=dict)

@dataclass
class AppCfg:
    stats_xml: str
    xpression: XPressionCfg
    logging_level: str = "INFO"
    debounce_ms: int = 400
    min_trigger_interval_ms: int = 0
    dry_run: bool = False
    player: PlayerCfg = field(default_factory=PlayerCfg)
    team_bursts: TeamBurstCfg = field(default_factory=TeamBurstCfg)
    types: TypesCfg = field(default_factory=TypesCfg)

def load_config(path: str) -> AppCfg:
    # Check if config file exists
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Validate required fields
    if not raw:
        raise ValueError("Config file is empty or invalid YAML")

    if "stats_xml" not in raw:
        raise ValueError("Missing required field: stats_xml")

    if "xpression" not in raw:
        raise ValueError("Missing required field: xpression")

    stats_xml = raw["stats_xml"]
    if not stats_xml:
        raise ValueError("stats_xml cannot be empty - specify the path to your XML stats file")

    # Validate logging level
    logging_level = raw.get("logging_level", "INFO").upper()
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if logging_level not in valid_levels:
        raise ValueError(f"Invalid logging_level: {logging_level}. Must be one of {valid_levels}")

    # Validate focus_mode if present
    player_cfg = raw.get("player", {})
    focus_mode = player_cfg.get("focus_mode", "on_take")
    valid_focus_modes = ["on_take", "before_take", "off"]
    if focus_mode not in valid_focus_modes:
        raise ValueError(f"Invalid focus_mode: {focus_mode}. Must be one of {valid_focus_modes}")

    # Validate team_bursts configuration
    team_bursts = raw.get("team_bursts", {})
    if team_bursts.get("enabled", True):
        if "take_ids" not in team_bursts:
            logging.warning("team_bursts enabled but no take_ids configured")
        else:
            take_ids = team_bursts["take_ids"]
            if "home" not in take_ids or "away" not in take_ids:
                logging.warning("team_bursts take_ids missing 'home' or 'away' configuration")

    return AppCfg(
        stats_xml=stats_xml,
        xpression=XPressionCfg(**raw["xpression"]),
        logging_level=logging_level,
        debounce_ms=raw.get("debounce_ms", 400),
        min_trigger_interval_ms=raw.get("min_trigger_interval_ms", 0),
        dry_run=raw.get("dry_run", False),
        player=PlayerCfg(**player_cfg),
        team_bursts=TeamBurstCfg(**team_bursts),
        types=TypesCfg(**raw.get("types", {})),
    )
