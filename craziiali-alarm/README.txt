========================================================================
  CRAZIIALI — Laptop Alarm Agent  (Windows 11)
========================================================================

WHAT IT DOES
------------
When you press the "Add to Calendar" button on a shoot in the planner,
the website does two things now:

  1. Adds the shoot to your Google Calendar (as before), AND
  2. Arms a LOUD WINDOWS ALARM on this laptop.

The alarm rings TWICE per shoot:
  - 1 HOUR BEFORE the shoot
  - AT THE EXACT shoot time

It LOOPS UNTIL YOU DISMISS IT (a fullscreen red screen with a DISMISS
and a SNOOZE button) — even if every browser is closed. The only
requirement: this little agent must be running. After the one-time
setup below, it starts itself automatically every time you log in.

It only arms an alarm for shoots that have a TIME set (an all-day shoot
has no exact hour to ring at).


========================================================================
  ONE-TIME SETUP  (about 5 minutes)
========================================================================

STEP 1 — Install Python (if you don't have it)
----------------------------------------------
  - Go to https://www.python.org/downloads/
  - Download Python 3 for Windows and run the installer.
  - IMPORTANT: on the first screen, TICK the box
        "Add python.exe to PATH"
    then click Install.

STEP 2 — Install the agent's dependencies
-----------------------------------------
  - Double-click  install.bat  in this folder.
  - It opens a black window, installs what's needed, then says "Done".

STEP 3 — Get your Firebase key (so the agent can read your alarms)
-----------------------------------------------------------------
  - Go to:  https://console.firebase.google.com/
  - Open the project:  my-figma-a7909
  - Click the gear icon (top-left) -> "Project settings"
  - Go to the "Service accounts" tab
  - Click "Generate new private key" -> "Generate key"
  - A .json file downloads. RENAME it to exactly:
        serviceAccountKey.json
  - MOVE it into THIS folder (next to agent.py).
  (Keep this file private — it's the key to your database.)

STEP 4 — Add the database rule (one line, so the website can arm alarms)
-----------------------------------------------------------------------
  - In the Firebase Console, open: Realtime Database -> Rules
  - Inside the top-level rules, add an "alarms" entry so it looks like:

        {
          "rules": {
            ... your existing rules ...,
            "alarms": { ".read": "auth != null", ".write": "auth != null" }
          }
        }

  - Click "Publish".
  (If you'd like, send me your current rules and I'll merge it for you.)

STEP 5 — Test it
----------------
  - Double-click  run-alarm.bat  (a window stays open showing status).
  - In the planner, make a shoot with TODAY's date and a time about
    2 minutes from now, then press its "Add to Calendar" button.
  - Within ~15 seconds of that time, the alarm should ring loudly and
    fill the screen. Click DISMISS to stop it.

STEP 6 — Make it automatic
--------------------------
  - Close the test window.
  - Double-click  install-autostart.bat
  - From now on the agent runs silently in the background every time
    you log into Windows. You never have to think about it again.


========================================================================
  EVERYDAY USE
========================================================================
  - Just press "Add to Calendar" on any shoot that has a date + time.
  - You'll get the Google Calendar event AND the two laptop alarms.
  - Deleting a shoot cancels its laptop alarm automatically.


========================================================================
  HANDY CONTROLS
========================================================================
  - Stop the agent now:        Task Manager -> "pythonw.exe" -> End task
  - Turn off auto-start:        run  uninstall-autostart.bat
  - Change snooze length / how loud / colors: edit the settings near the
    top of agent.py (SNOOZE_MINUTES, GRACE_MINUTES, the amp value).
  - The siren file (alarm.wav) is generated automatically on first run.
    Delete it and the agent makes a fresh one. You can also drop in your
    OWN alarm.wav (any WAV) and the agent will loop that instead.


========================================================================
  TROUBLESHOOTING
========================================================================
  - "Python is not installed": redo Step 1 and make sure you ticked
    "Add python.exe to PATH".
  - "Missing serviceAccountKey.json": redo Step 3 (the filename must be
    exactly serviceAccountKey.json and it must be in this folder).
  - No alarm fired: make sure the shoot has BOTH a date and a time, that
    run-alarm.bat shows "Connected", and that you published the Step 4
    rule. The agent checks every 15 seconds, so allow a few seconds.
  - It only rings if the trigger time is now or up to 5 minutes past
    (so booting up hours later won't ring for shoots already gone).
