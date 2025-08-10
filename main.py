from datetime import datetime

import requests
import urllib3
import yaml

from fingerprints import Authenticate

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main():
    yaml_data = yaml.safe_load(open("config.yaml"))

    # Extract date and time
    date_str = yaml_data["date"]
    start_time_str = yaml_data["time"]["start"]
    end_time_str = yaml_data["time"]["end"]
    needed_start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%m/%d/%Y %H:%M")
    needed_end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%m/%d/%Y %H:%M")

    json_data = {
        "TypeId": yaml_data["type_id"],
        "ZipCode": yaml_data["zip_code"],
        "CityName": "",
        "PreferredDay": 0,
    }

    auth = Authenticate(
        first_name=yaml_data["first_name"],
        last_name=yaml_data["last_name"],
        dob=yaml_data["dob"],
        last_4_ssn=yaml_data["last_4_ssn"],
        auth_mode=yaml_data.get("auth_mode", "manual"),
        keystroke_file=yaml_data.get("keystroke_file", "login_recording.json"),
    )

    # Get current appointment info
    payload = {
        "FirstName": yaml_data["first_name"],
        "LastName": yaml_data["last_name"],
        "DateOfBirth": yaml_data["dob"],
        "LastFourDigitsSsn": yaml_data["last_4_ssn"],
    }
    current_booking = requests.post(
        "https://apptapi.txdpsscheduler.com/api/Booking",
        headers=auth.get_headers(),
        json=payload,
        verify=False,
    )
    # Re-authenticate if the token is invalid
    if current_booking.status_code != 200:
        current_booking = requests.post(
            "https://apptapi.txdpsscheduler.com/api/Booking",
            headers=auth.get_headers(reauth=True),
            json=payload,
            verify=False,
        )
    assert current_booking.status_code == 200, "Authentication failure"
    current_booking = current_booking.json()
    if len(current_booking) > 0:  # There is a current appointment
        current_booking = current_booking[0]["BookingDateTime"]  # 2024-10-21T15:20:00
        current_booking = datetime.strptime(current_booking, "%Y-%m-%dT%H:%M:%S")  # 2024-10-21 15:20:00
        # Check if the current appointment already satisfies the required dt
        if needed_start_dt <= current_booking <= needed_end_dt:
            print("Current appointment is within the specified date and time range")
            return

    # Get list of available locations
    response = requests.post(
        "https://apptapi.txdpsscheduler.com/api/AvailableLocation",
        headers=auth.get_headers(),
        json=json_data,
        verify=False,
    )
    if response.status_code != 200:  # TODO: Move checking into class itself!
        response = requests.post(
            "https://apptapi.txdpsscheduler.com/api/AvailableLocation",
            headers=auth.get_headers(reauth=True),
            json=json_data,
            verify=False,
        )

    assert response.status_code == 200, "Authentication failure"
    response = response.json()

    # Check all locations for available timeslots within the needed date and time range
    slot = None
    slot_id = None
    for location in response:
        if location["Distance"] > yaml_data["miles_within"]:
            continue

        # Get timeslots for each location
        payload = {
            "LocationId": location["Id"],
            "TypeId": yaml_data["type_id"],
            "SameDay": False,
            "StartDate": None,
            "PreferredDay": 0,
        }
        timeslots = requests.post(
            "https://apptapi.txdpsscheduler.com/api/AvailableLocationDates",
            headers=auth.get_headers(),
            json=payload,
            verify=False,
        ).json()

        for date_info in timeslots["LocationAvailabilityDates"]:
            for available_slot in date_info["AvailableTimeSlots"]:
                slot_start_dt = datetime.strptime(available_slot["StartDateTime"], "%Y-%m-%dT%H:%M:%S")
                if needed_start_dt <= slot_start_dt <= needed_end_dt:
                    slot = available_slot
                    slot_id = slot["SlotId"]
                    print(f"Found a slot: {slot['StartDateTime']} at {location['Name']}")
                    break
            if slot:
                break
        if slot:
            break

    if not slot:
        print("No available slots within the specified date and time range")
        return

    # Hold the timeslot
    payload = {
        "SlotId": slot_id,
        "FirstName": yaml_data["first_name"],
        "LastName": yaml_data["last_name"],
        "DateOfBirth": yaml_data["dob"],
        "Last4Ssn": yaml_data["last_4_ssn"],
    }
    slot_held = requests.post(
        "https://apptapi.txdpsscheduler.com/api/HoldSlot",
        headers=auth.get_headers(),
        json=payload,
        verify=False,
    ).json()
    assert slot_held["SlotHeldSuccessfully"], "Failed to hold slot"

    # Get Response ID
    payload = {
        "FirstName": yaml_data["first_name"],
        "LastName": yaml_data["last_name"],
        "DateOfBirth": yaml_data["dob"],
        "LastFourDigitsSsn": yaml_data["last_4_ssn"],
        "CardNumber": "",
    }
    eligibility = requests.post(
        "https://apptapi.txdpsscheduler.com/api/Eligibility",
        headers=auth.get_headers(),
        json=payload,
        verify=False,
    ).json()
    response_id = eligibility[0]["ResponseId"]

    # Book the slot
    payload = {
        "CardNumber": "",
        "FirstName": yaml_data["first_name"],
        "LastName": yaml_data["last_name"],
        "DateOfBirth": yaml_data["dob"],
        "Last4Ssn": yaml_data["last_4_ssn"],
        "Email": yaml_data["email"],
        "CellPhone": "",
        "HomePhone": "",
        "ServiceTypeId": yaml_data["type_id"],
        "BookingDateTime": slot["StartDateTime"],
        "BookingDuration": 20,
        "SlotId": slot_id,
        "SpanishLanguage": "N",
        "SiteId": location["Id"],
        "SendSms": False,
        "AdaRequired": False,
        "ResponseId": response_id,
    }
    booking = requests.post(
        "https://apptapi.txdpsscheduler.com/api/NewBooking",
        headers=auth.get_headers(),
        json=payload,
        verify=False,
    ).json()
    print("Booking successful!")


if __name__ == "__main__":
    main()
