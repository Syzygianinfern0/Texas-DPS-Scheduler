import argparse
import logging
import subprocess
import time

import apprise
import yaml


def load_apprise_config():
    """Load Apprise configuration from config.yaml"""
    try:
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)

        apobj = apprise.Apprise()

        # Load notification URLs from config
        notification_urls = config.get("notifications", {}).get("urls", [])
        for url in notification_urls:
            if url:  # Skip empty/None URLs
                apobj.add(url)

        return apobj
    except FileNotFoundError:
        logging.warning("config.yaml not found. Using default Apprise configuration.")
        return apprise.Apprise()
    except Exception as e:
        logging.error(f"Error loading Apprise configuration: {e}")
        return apprise.Apprise()


# Initialize Apprise with configuration from YAML
apobj = load_apprise_config()


def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr


def monitor_command(command, interval):
    last_output = None
    while True:
        current_output = run_command(command)
        if current_output != last_output:
            logging.info(f"Output changed:\n\n{current_output}")
            apobj_current_output = current_output.replace("\n", "\r\n ")
            apobj_current_output = current_output.replace("<", "")
            apobj.notify(body=f"Output changed:\r\n{apobj_current_output}")
            last_output = current_output
            if last_output.strip() == "Current appointment is within the specified date and time range":
                apobj.notify(body="Stopping the monitor script")
                return
        else:
            logging.info("Output unchanged.")
        time.sleep(interval * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor a command's output for changes.")
    parser.add_argument("command", help="The command to run.")
    parser.add_argument("interval", type=int, help="The interval (in minutes) to run the command.")

    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s [%(levelname)8s]: %(message)s", level=logging.INFO)

    monitor_command(args.command, args.interval)
