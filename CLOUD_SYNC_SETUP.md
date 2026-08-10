# Cloud Learning-File Sync

The application uploads only these runtime learning snapshots:

- `data/knowledge_base.jsonl`
- `data/training/active_prompt_profile.json`

Both files exist immediately after installation. `knowledge_base.jsonl`
accumulates generation and training records; `active_prompt_profile.json` is the
complete current profile and is replaced after a successful learning update.
Cloud snapshots remain timestamped and do not overwrite previous uploads.

API keys are never included. Generated MIDI/MP3 files are not uploaded. Be
aware that the learning files may contain user requirements, lyrics, comments,
prompts and generated composition data.

## Google Drive without end-user login

Google Apps Script can run as the deploying owner while allowing anonymous
callers. This means product users do not need Google accounts.

1. The included receiver already defaults to the supplied Drive folder ID
   `1L3gS4Q5YbHDNbnmKyj7Rt9Qu3DN17xjL`. To use another folder, set its ID in
   the `FOLDER_ID` Script Property.
2. Open <https://script.google.com>, create a project, and paste the contents of
   `GOOGLE_DRIVE_UPLOAD_WEB_APP.gs`.
3. `FOLDER_ID` is optional for the supplied folder and required only to override it.
4. For completely anonymous upload, leave `UPLOAD_SECRET` absent. For safer
   upload, add a long random `UPLOAD_SECRET` and put the same value in the local
   `.env` as `GOOGLE_DRIVE_UPLOAD_SECRET=...`.
5. Choose **Deploy → New deployment → Web app**. Execute as **Me** and allow
   **Anyone** (including anonymous users). Authorise Drive access and copy the
   deployed `/exec` URL.
   If the script was deployed before `doGet` was added, choose **Deploy → Manage
   deployments → Edit → New version → Deploy**. Merely saving the source
   does not update the deployed version.
6. Configure the application:

```bash
music-cloud-sync --configure \
  --drive-url 'https://script.google.com/macros/s/DEPLOYMENT_ID/exec' \
  --anonymous-upload \
  --installation-id 'MY_PRODUCT_001' \
  --interval-days 3
```

For protected upload instead:

```bash
music-cloud-sync --configure \
  --drive-url 'https://script.google.com/macros/s/DEPLOYMENT_ID/exec' \
  --protected-upload \
  --installation-id 'MY_PRODUCT_001' \
  --interval-days 3
```

A fully anonymous endpoint can be discovered and abused. Protected upload is
recommended even though end users still do not sign in.

## Test and schedule

```bash
music-cloud-sync --test-connection
music-cloud-sync --run-now
music-cloud-sync --status
music-cloud-sync --install-schedule
launchctl bootstrap gui/$(id -u) \
  "$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist"
```

Change the interval from Bash and reload the LaunchAgent:

```bash
music-cloud-sync --configure --interval-days 1
music-cloud-sync --install-schedule --interval-days 1
launchctl bootout gui/$(id -u) \
  "$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) \
  "$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist"
```

The default interval is three days (259,200 seconds). Configuration is stored at
`~/.config/deterministic-midi/cloud_sync_config.json`, so it is not lost when the
terminal starts in another directory. The command automatically finds the installed
project and creates its `data` log directory before installing the schedule.

For a three-second installation test, configure and reload the native LaunchAgent:

```bash
music-cloud-sync --configure \
  --drive-url 'https://script.google.com/macros/s/DEPLOYMENT_ID/exec' \
  --anonymous-upload \
  --installation-id 'TEST001' \
  --interval-seconds 3
music-cloud-sync --test-connection
music-cloud-sync --install-schedule --interval-seconds 3
launchctl bootout gui/$(id -u) \
  "$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) \
  "$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist"
```

This replaces the old `while true` test loop and therefore does not depend on a
relative `data/cloud_sync_test.log` path. Restore the production interval with:

```bash
music-cloud-sync --configure --interval-days 3
music-cloud-sync --install-schedule --interval-days 3
launchctl bootout gui/$(id -u) \
  "$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) \
  "$HOME/Library/LaunchAgents/com.deterministic-midi.cloud-sync.plist"
```

`--installation-id` can be chosen during
installation and changed later with another `--configure` command. If omitted,
the first configuration creates a stable random ID.

Each upload uses this UTC hierarchy and naming scheme:

```text
year_month_date/
├── KB/
│   └── KB_year_month_date_hour_min_sec_installationID.jsonl
└── prompting/
    └── Pro_year_month_date_hour_min_sec_installationID.json
```

The Apps Script first checks for the date folder and category subfolder and
creates either when missing. It then checks the filename; collisions become
`_2`, `_3`, and so forth instead of overwriting an existing snapshot.
