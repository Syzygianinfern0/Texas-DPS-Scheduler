import json
import os
import random
import time
from typing import Any, Dict, List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from seleniumwire import webdriver  # Import from seleniumwire

from keystroke_recorder import replay_keystrokes


def random_sleep():
    time.sleep(random.randint(1, 3))


class Authenticate:
    def __init__(
        self, first_name, last_name, dob, last_4_ssn, auth_mode="manual", keystroke_file="login_recording.json"
    ):
        self.auth_token = None
        self.token_file = "auth_token.json"
        self.first_name = first_name
        self.last_name = last_name
        self.dob = dob
        self.last_4_ssn = last_4_ssn
        self.auth_mode = auth_mode  # "manual", "recorded_keystrokes", "automated_sendkeys"
        self.keystroke_file = keystroke_file
        self._load_token()

    def _load_token(self):
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as file:
                data = json.load(file)
                self.auth_token = data.get("auth_token")
        if not self.auth_token:
            self._authenticate()

    def _save_token(self):
        with open(self.token_file, "w") as file:
            json.dump({"auth_token": self.auth_token}, file)

    def _authenticate(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--headless")  # Optional: Run in headless mode
        driver = webdriver.Chrome(options=options)

        # Open the website
        driver.get("https://public.txdpsscheduler.com")

        if self.auth_mode == "manual":
            print("Please complete the login process manually in the opened browser window.")
            print("After you have logged in, the script will continue automatically.")
        elif self.auth_mode == "recorded_keystrokes":
            if os.path.exists(self.keystroke_file):
                print(f"Replaying recorded keystrokes from {self.keystroke_file}")
                with open(self.keystroke_file, "r") as f:
                    data = json.load(f)
                events = data.get("events", [])
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                    body.click()  # focus page for typing
                except Exception:
                    pass
                replay_keystrokes(driver, events)
            else:
                raise FileNotFoundError(
                    f"Keystroke file {self.keystroke_file} not found. Please record keystrokes first using keystroke_recorder.py"
                )
        elif self.auth_mode == "automated_sendkeys":
            # Click the language button
            driver.find_element(By.TAG_NAME, "button").click()  # English button

            # Fill details
            inputs = driver.find_elements(By.TAG_NAME, "input")
            inputs[1].send_keys(self.first_name)  # First Name
            random_sleep()
            inputs[2].send_keys(self.last_name)  # Last Name
            random_sleep()
            inputs[3].send_keys(self.dob)  # DOB
            random_sleep()
            inputs[4].send_keys(self.last_4_ssn)  # Last 4 SSN
            random_sleep()
            driver.find_elements(By.TAG_NAME, "button")[-1].click()  # Log on button

        auth_token = None
        # Extract the auth token from the request
        is_manual = self.auth_mode in ["manual", "recorded_keystrokes"]
        for _ in range(30 if is_manual else 5):
            time.sleep(2 if is_manual else 5)
            try:  # Check if the eligibility request is present
                eligibility_request = [
                    request
                    for request in driver.requests
                    if request.url == "https://apptapi.txdpsscheduler.com/api/Eligibility"
                ][0]
            except:  # If not, recaptcha3 minscore was too low, retry clicking the log on button (only in automated mode)
                if not is_manual:
                    random_sleep()
                    driver.find_elements(By.TAG_NAME, "button")[0].click()  # Ok button
                    random_sleep()
                    driver.find_elements(By.TAG_NAME, "button")[-1].click()  # Log on button
                    continue
                else:
                    continue

            auth_token = eligibility_request.headers["Authorization"]
            break

        # Close the driver
        driver.quit()

        if auth_token is None:
            raise Exception("Failed to authenticate")

        self.auth_token = auth_token
        self._save_token()

    def get_headers(self, reauth=False):
        if reauth:
            self._authenticate()

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": self.auth_token,
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "DNT": "1",
            "Origin": "https://public.txdpsscheduler.com",
            "Referer": "https://public.txdpsscheduler.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
        }

        return headers
