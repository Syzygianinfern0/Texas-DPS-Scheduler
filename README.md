# Texas-DPS-Scheduler
Book Texas DPS Appointments (fixes auth errors) 🚦

## Why?
DPS appointments are pretty much impossible to get and the website is a mess. This script automates the process of booking an appointment. Also, earlier versions of the script were broken due to authentication changes in the DPS website. This version fixes those issues and provides multiple authentication modes to work around the DPS website's security measures.


## Usage

1. Clone the repository
```bash
git clone https://github.com/Syzygianinfern0/Texas-DPS-Scheduler.git
cd Texas-DPS-Scheduler
```
1. Copy `config.example.yaml` to `config.yaml` and fill in the required fields
2. Start with `auth_mode: automated_sendkeys` in your config file (recommended first choice). See [More on Authentication Modes](#more-on-authentication-modes) for more details/if you encounter any issues.
3. _(Optional)_ Setup notifications through [Apprise](https://github.com/caronc/apprise) in the config file (leave as `[]` if you don't want notifications). You will still get official email notifications from the DPS website when the appointment is booked.
4. Run the following commands

```script
pip install requirements.txt
./run.sh
```

Please open an issue if you encounter any problems. 

> [!TIP]
> You need to keep the script running in order to get an appointment. Keep your computer plugged in and prevent it from sleeping to ensure the script runs continuously. 

> [!TIP]
> There also seems to be an IP blocking issue when the script is run for too long. I would recommend starting the script the night before you want to book the appointment.

> [!IMPORTANT]  
> There are occasional errors with authentication and selenium (about once per hour based on my experience), but they're expected. It's difficult to bypass the new authentication system every time, but it works out most times. Since monitor.py triggers the main script each minute, this ends up working to our advantage. Check out [#1](https://github.com/Syzygianinfern0/Texas-DPS-Scheduler/issues/1) for more details.

## Project Structure

- `config.example.yaml`: Example configuration file which needs to be copied to `config.yaml`
- `fingerprints.py`: Generates the auth fingerprint for the DPS website
- `keystroke_recorder.py`: Records and replays keystrokes for automated login
- `main.py`: Main script that checks, holds, and books the appointment
- `monitor.py`: Calls main script periodically and sends notifications
- `run.sh`: Bash script to call the monitor script


## More on Authentication Modes
<details>
<summary><strong>Click to expand</strong></summary>

The script supports three different authentication modes to handle the Texas DPS website's security requirements. Due to the DPS website's anti-automation measures, you should try these modes in the following order until one works for you:

### 1. Automated SendKeys Mode (`auth_mode: automated_sendkeys`) - Try First
- Uses human-like typing patterns with realistic timing delays
- Automatically navigates through the login form using Tab keys
- Types your credentials character by character with natural pauses
- Fully automated - no manual intervention required

**Features:**
- Human-like typing speed variations
- Realistic delays between keystrokes
- Tab-based navigation through form fields
- Automatic form submission

### 2. Recorded Keystrokes Mode (`auth_mode: recorded_keystrokes`) - Try Second
- Records your keystrokes during a successful login session
- Replays the exact same keystrokes with original timing for future logins
- Requires initial setup to record your login process once

**Setup Instructions:**
1. Run the keystroke recorder: `python keystroke_recorder.py --mode record --save-file login_recording.json`
2. Complete your login process in the opened browser window
3. The recorder will automatically stop when login is detected
4. Set `auth_mode: recorded_keystrokes` in your config.yaml
5. The script will now use your recorded keystrokes for automated login

### 3. Manual Mode (`auth_mode: manual`) - Try Last
- The script launches a browser window approximately every 20 minutes
- You manually log in to your DPS account in the browser when prompted
- Once logged in, the bot continues its automated appointment booking process
- Most reliable option but requires your attention

**Recommended Approach:**
Start with `automated_sendkeys` mode. If you encounter authentication failures or blocks, switch to `recorded_keystrokes` mode. If that also fails, use `manual` mode as a fallback. The DPS website's security measures vary, so what works for one user may not work for another.

</details> 
