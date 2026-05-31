========================================================================
  CRAZIIALI — Laptop Alarm Agent  (Windows 11)
========================================================================

  LIVE FOLDER:  C:\craziiali-alarm
  (This copy on the Desktop is just the backup/source kept in your code
   project. Do everything below in  C:\craziiali-alarm .)

WHAT IT DOES
------------
When you press "Add to Calendar" on a shoot (that has a date AND time),
the website does two things:
  1. Adds the shoot to your Google Calendar, AND
  2. Arms a LOUD WINDOWS ALARM on this laptop.

The alarm rings TWICE per shoot — 1 HOUR BEFORE and AT THE EXACT time —
and LOOPS UNTIL YOU DISMISS IT (fullscreen, with DISMISS + SNOOZE),
even with every browser closed. The only requirement is that the agent
is running; after setup it auto-starts with Windows.


========================================================================
  ALREADY DONE FOR YOU
========================================================================
  [x] Python 3.12 installed
  [x] firebase-admin installed
  [x] Agent copied to  C:\craziiali-alarm


========================================================================
  WHAT'S LEFT  (2 steps — only you can do these, they need your login)
========================================================================

STEP 1 — Get your Firebase key
------------------------------
  - Go to:  https://console.firebase.google.com/
  - Open the project:  my-figma-a7909
  - Gear icon (top-left) -> "Project settings"
  - "Service accounts" tab
  - "Generate new private key" -> "Generate key"  (a .json downloads)
  - RENAME the file to exactly:   serviceAccountKey.json
  - MOVE it into:                 C:\craziiali-alarm
  (Keep it private — it's the key to your database. It lives only on
   this PC, never in the website code.)

STEP 2 — Publish the database rule (so the website can arm alarms)
-----------------------------------------------------------------
  - Firebase Console -> Realtime Database -> Rules
  - Add an "alarms" entry to the rules, then Publish:

        "alarms": { ".read": "auth != null", ".write": "auth != null" }

  (Easiest: paste your current rules to me and I'll merge this in.)


========================================================================
  THEN: TEST IT
========================================================================
  - Open  C:\craziiali-alarm  and double-click  run-alarm.bat
    (a window stays open showing "Connected").
  - In the planner, make a shoot with TODAY's date + a time ~2 minutes
    away, and press its "Add to Calendar" button.
  - Within ~15 seconds of that time the alarm fills the screen and rings.
    Click DISMISS to stop it.

  MAKE IT AUTOMATIC:
  - Close the test window, then double-click  install-autostart.bat
  - It now runs silently in the background every time you log into
    Windows. You never touch it again.


========================================================================
  HANDY CONTROLS
========================================================================
  - Stop the agent now:    Task Manager -> "pythonw.exe" -> End task
  - Turn off auto-start:    run  uninstall-autostart.bat
  - Adjust snooze length / loudness / lead time: edit the settings near
    the top of agent.py  (SNOOZE_MINUTES, GRACE_MINUTES, amp).
  - Use your own sound: drop any  alarm.wav  into the folder and the
    agent loops that instead (it auto-generates one if missing).


========================================================================
  TROUBLESHOOTING
========================================================================
  - "Missing serviceAccountKey.json": redo Step 1; filename must be
    exactly serviceAccountKey.json and sit in C:\craziiali-alarm.
  - No alarm fired: make sure the shoot has BOTH a date and a time,
    run-alarm.bat shows "Connected", and Step 2's rule is published.
    The agent checks every 15 seconds, so allow a few seconds.
  - It only rings if the time is now or up to 5 minutes past, so
    booting up hours later won't ring for shoots already gone.
