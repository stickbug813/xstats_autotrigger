import time, os, threading, logging, xml.etree.ElementTree as ET
from xstats_autotrigger.engine import compose_player_takeid
from xstats_autotrigger.engine import EngineState

class XMLWatcher(threading.Thread):
    def __init__(self, cfg, rt, state: EngineState):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.rt = rt
        self.state = state
        self.aliases = {k.upper(): v.upper() for k, v in cfg.types.aliases.items()}
        self.player_enabled = cfg.types.player_enabled
        self.bursts_enabled = cfg.types.bursts_enabled
        self.last_mtime = 0.0
        self.last_mtime_change = 0.0

    def run(self):
        logging.info("XML Watcher Started: %s", self.cfg.stats_xml)
        while True:
            time.sleep(0.25)
            if not self.state.enabled:
                continue

            try:
                if os.path.getsize(self.cfg.stats_xml) == 0:
                    continue

                # Implement debounce: wait for file to stop changing
                mtime = os.path.getmtime(self.cfg.stats_xml)
                now = time.time()

                if mtime != self.last_mtime:
                    self.last_mtime = mtime
                    self.last_mtime_change = now
                    logging.debug("XML file changed, starting debounce timer")
                    continue

                # Check if debounce period has elapsed
                debounce_sec = self.cfg.debounce_ms / 1000.0
                if now - self.last_mtime_change < debounce_sec:
                    continue

                with open(self.cfg.stats_xml, "rb") as f:
                    root = ET.fromstring(f.read())

                plays = root.findall(".//play")

                if not self.state.first_parse_done:
                    for p in plays:
                        self.state.processed_keys.add(self._key(p))
                    self.state.first_parse_done = True
                    logging.info("Initial parse complete: %d historical plays skipped", len(plays))
                    continue

                for p in plays:
                    self._handle_play(p)

            except Exception as e:
                logging.debug("XML parse skip: %s", e)

    def _key(self, p):
        return (
            p.get("vh"),
            self._canon(p.get("type")),
            p.get("uni"),
            p.get("action"),
            p.get("hscore"),
            p.get("vscore"),
        )

    def _canon(self, raw):
        raw = (raw or "").upper()
        return self.aliases.get(raw, raw)

    def _handle_play(self, p):
        if not self.state.enabled:
            return

        key = self._key(p)
        if key in self.state.processed_keys:
            logging.debug("Duplicate play detected, skipping: %s", key)
            return
        self.state.processed_keys.add(key)
        logging.debug("New play detected: %s", key)

        # Only trigger on made shots
        action = p.get("action")
        if action != "GOOD":
            logging.debug("Skipping non-scoring play: action=%s", action)
            return

        stat = self._canon(p.get("type"))
        vh = p.get("vh")
        uni = p.get("uni")
        side = "home" if vh == "H" else "away"

        now = time.time()

        # Enforce global rate limit
        if self.cfg.min_trigger_interval_ms > 0:
            min_interval_sec = self.cfg.min_trigger_interval_ms / 1000.0
            time_since_last = now - self.state.last_trigger_at
            if time_since_last < min_interval_sec:
                logging.debug("Rate limit: skipping trigger (%.2fs < %.2fs)", time_since_last, min_interval_sec)
                return

        if self.player_enabled.get(stat, True):
            take = compose_player_takeid(vh, stat, uni)
            logging.info("Player trigger: %s #%s %s (take %d)", side, uni, stat, take)

            # Handle focus_mode: before_take | on_take | off
            if self.cfg.player.focus_mode == "before_take":
                logging.debug("Sending FOCUS then SEQI (mode: before_take)")
                self.rt.send(f"FOCUS {take}")
                self.rt.send(f"SEQI {take}")
            elif self.cfg.player.focus_mode == "on_take":
                logging.debug("Sending SEQI then FOCUS (mode: on_take)")
                self.rt.send(f"SEQI {take}")
                self.rt.send(f"FOCUS {take}")
            else:  # "off"
                logging.debug("Sending SEQI only (mode: off)")
                self.rt.send(f"SEQI {take}")

            threading.Timer(
                self.cfg.player.auto_takeoff_seconds,
                lambda: self.rt.send(f"SEQO {take}")
            ).start()
            self.state.last_player_trigger_at = now
            self.state.last_trigger_at = now
        else:
            logging.debug("Player graphic disabled for stat type: %s", stat)

        if self.cfg.team_bursts.enabled and self.bursts_enabled.get(stat, True):

            if stat not in self.cfg.team_bursts.thresholds:
                logging.debug("No burst threshold configured for stat: %s", stat)
                return

            self.state.burst_counts[side][stat] += 1
            count = self.state.burst_counts[side][stat]
            threshold = self.cfg.team_bursts.thresholds[stat]
            logging.debug("Burst count: %s %s = %d/%d", side, stat, count, threshold)

            if count >= threshold:
                self.state.burst_counts[side][stat] = 0
                delay = (
                    self.cfg.player.auto_takeoff_seconds
                    + self.cfg.team_bursts.delay_after_player_seconds
                )
                logging.info("Burst threshold reached! Scheduling %s %s burst in %.1fs", side, stat, delay)
                threading.Timer(delay, lambda: self._fire_burst(side, stat)).start()
        else:
            logging.debug("Team bursts disabled for stat type: %s", stat)

    def _fire_burst(self, side, stat):
        try:
            take = self.cfg.team_bursts.take_ids[side][stat]
        except KeyError:
            logging.warning("Missing take_id for %s/%s burst - check config", side, stat)
            return

        logging.info("Firing team burst: %s %s (take %d)", side, stat, take)
        self.rt.send(f"SEQI {take}")
        threading.Timer(
            self.cfg.team_bursts.auto_takeoff_seconds,
            lambda: self.rt.send(f"SEQO {take}")
        ).start()