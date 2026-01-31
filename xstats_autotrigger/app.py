import argparse, logging, sys, os
from xstats_autotrigger.config_loader import load_config
from xstats_autotrigger.engine import EngineState
from xstats_autotrigger.rosstalk import RossTalkClient
from xstats_autotrigger.watcher import XMLWatcher
from xstats_autotrigger.server import build_app

def main():
    parser = argparse.ArgumentParser(description="XSAT Auto Trigger v1.0.1-alpha1")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    args = parser.parse_args()

    # Load and validate configuration
    try:
        cfg = load_config(args.config)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, KeyError) as e:
        print(f"ERROR: Invalid configuration - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load config - {e}", file=sys.stderr)
        sys.exit(1)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, cfg.logging_level),
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info("XSAT Auto Trigger v1.0.1-alpha1 starting")
    logging.info("Config: %s", args.config)
    logging.info("Logging level: %s", cfg.logging_level)

    # Validate stats XML file exists
    if not os.path.exists(cfg.stats_xml):
        logging.warning("Stats XML file does not exist yet: %s", cfg.stats_xml)
        logging.warning("Watcher will wait for file to be created...")

    # Initialize components
    rt = RossTalkClient(cfg.xpression.host, cfg.xpression.port)
    logging.info("RossTalk target: %s:%d", cfg.xpression.host, cfg.xpression.port)

    # Check XPression connectivity
    if rt.healthy():
        logging.info("XPression connection: OK")
    else:
        logging.warning("XPression connection: FAILED - check host/port and ensure XPression is running")

    state = EngineState()
    watcher = XMLWatcher(cfg, rt, state)
    watcher.start()
    logging.info("XML Watcher started")

    # Start HTTP server
    app = build_app(cfg, rt, state, watcher)
    logging.info("HTTP API starting on port 5005")
    app.run(host='127.0.0.1', port=5005, debug=False)

if __name__ == "__main__":
    main()
