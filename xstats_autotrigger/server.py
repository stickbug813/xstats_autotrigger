import logging
from flask import Flask, jsonify, request
from xstats_autotrigger.engine import compose_player_takeid


def build_app(cfg, rt, state, watcher):
    app = Flask(__name__)

    @app.route("/enable", methods=["PUT"])
    def enable():
        logging.info("HTTP API: Enable triggered - resetting runtime state")
        state.reset_runtime_state()
        state.enabled = True
        return jsonify(ok=True)

    @app.route("/disable", methods=["PUT"])
    def disable():
        logging.info("HTTP API: Disable triggered")
        state.enabled = False
        return jsonify(ok=True)

    @app.route("/force_on", methods=["POST"])
    def force_on():
        data = request.get_json(force=True)

        # Validate required fields
        required = ["vh", "type", "uni"]
        missing = [k for k in required if k not in data]
        if missing:
            return jsonify(error=f"Missing required fields: {', '.join(missing)}"), 400

        # Validate vh field
        if data["vh"] not in ["H", "V"]:
            return jsonify(error="vh must be 'H' or 'V'"), 400

        try:
            take_id = compose_player_takeid(
                data["vh"],
                data["type"],
                data["uni"]
            )
            logging.info("HTTP API: Force trigger - %s #%s %s (take %d)",
                        data["vh"], data["uni"], data["type"], take_id)
            rt.send(f"SEQI {take_id}")
            return jsonify(ok=True, take_id=take_id)
        except Exception as e:
            logging.error("HTTP API: Force trigger failed - %s", e)
            return jsonify(error=str(e)), 500

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify(
            enabled=state.enabled,
            xpression_ok=rt.healthy(),
            burst_counts=state.burst_counts,
            last_player_trigger_at=state.last_player_trigger_at
        )

    return app
