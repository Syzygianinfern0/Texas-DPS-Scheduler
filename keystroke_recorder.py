import argparse
import json
import os
import time
from typing import Any, Dict, List, Optional

from pynput import keyboard
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from seleniumwire import webdriver

DEFAULT_URL = "https://public.txdpsscheduler.com"


def build_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    return driver


def key_to_string(k) -> str:
    try:
        if isinstance(k, keyboard.KeyCode) and k.char is not None:
            return k.char
        if isinstance(k, keyboard.Key):
            return f"Key.{k.name}"
        return str(k)
    except Exception:
        return str(k)


def record_keystrokes_until(stop_condition_fn) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    start_time = time.time()
    last_time = start_time

    print("Recording keystrokes. Will stop automatically when login is detected.")

    def on_press(k):
        nonlocal last_time
        now = time.time()
        dt = now - last_time
        last_time = now
        events.append({"k": key_to_string(k), "dt": dt})

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    try:
        stop_condition_fn(listener)
    finally:
        try:
            listener.stop()
        except Exception:
            pass
    return events


def string_to_selenium_keys(s: str):
    special_map = {
        "Key.enter": Keys.ENTER,
        "Key.return": Keys.RETURN,
        "Key.tab": Keys.TAB,
        "Key.backspace": Keys.BACKSPACE,
        "Key.delete": Keys.DELETE,
        "Key.space": Keys.SPACE,
        "Key.left": Keys.ARROW_LEFT,
        "Key.right": Keys.ARROW_RIGHT,
        "Key.up": Keys.ARROW_UP,
        "Key.down": Keys.ARROW_DOWN,
        "Key.home": Keys.HOME,
        "Key.end": Keys.END,
    }
    if s in special_map:
        return special_map[s]
    if s in {"Key.shift", "Key.shift_r", "Key.ctrl", "Key.ctrl_r", "Key.cmd", "Key.cmd_r", "Key.alt", "Key.alt_r"}:
        return None
    return s


def replay_keystrokes(driver, events: List[Dict[str, Any]]):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body.click()
    except Exception:
        pass
    for e in events:
        dt = float(e.get("dt", 0))
        key_str = e.get("k")
        time.sleep(max(dt, 0))
        mapped = string_to_selenium_keys(key_str)
        if mapped is None:
            continue
        try:
            target = driver.switch_to.active_element
            target.send_keys(mapped)
        except Exception:
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(mapped)
            except Exception:
                pass


def wait_for_eligibility_like(driver, manual: bool = True) -> Optional[Any]:
    # Mirror logic from fingerprints.py: poll selenium-wire requests list
    loops = 30 if manual else 5
    for _ in range(loops):
        time.sleep(2 if manual else 5)
        try:
            eligibility_request = [
                req for req in driver.requests if req.url == "https://apptapi.txdpsscheduler.com/api/Eligibility"
            ][0]
            return eligibility_request
        except Exception:
            continue
    return None


def record_cli(file_path: str):
    driver = build_driver()
    try:
        driver.get(DEFAULT_URL)
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.click()  # focus page for typing
        except Exception:
            pass
        print("Recording keystrokes for DPS login in the opened browser window.")
        print("Will stop automatically when the Eligibility API request is detected.")

        def stop_when_login(_listener):
            req = wait_for_eligibility_like(driver, manual=True)
            if req is not None:
                print("Detected Eligibility API request. Stopping recording...")
            else:
                print("Timeout waiting for Eligibility request. Stopping recording anyway...")

        events = record_keystrokes_until(stop_when_login)
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w") as f:
            json.dump({"events": events}, f, indent=2)
        print(f"Saved {len(events)} key events to {file_path}")
        time.sleep(0.5)
    finally:
        driver.quit()


def replay_cli(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Recording file not found: {file_path}")
    with open(file_path, "r") as f:
        data = json.load(f)
    events: List[Dict[str, Any]] = data.get("events", [])
    driver = build_driver()
    try:
        driver.get(DEFAULT_URL)
        replay_keystrokes(driver, events)
        time.sleep(1)
    finally:
        driver.quit()


def main():
    parser = argparse.ArgumentParser(description="Record or replay keystrokes with original timing.")
    parser.add_argument("--mode", choices=["record", "replay"], required=True, help="Operation mode")
    parser.add_argument("--save-file", required=True, help="Path to save to (record) or load from (replay)")
    args = parser.parse_args()

    if args.mode == "record":
        record_cli(args.save_file)
    else:
        replay_cli(args.save_file)


if __name__ == "__main__":
    main()
