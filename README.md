# CHARMM-GUI Automation Tool

**Author:** Manuel Alejandro Lopez (2025)

A Selenium-based browser automation tool for [CHARMM-GUI](https://www.charmm-gui.org/) that records, replays, and parallelizes multi-step molecular system setup workflows. Useful for batch-submitting many identical or similar simulation jobs without manual repetition.


## Requirements

- Python 3.8+
- Google Chrome + matching [ChromeDriver](https://chromedriver.chromium.org/)
- A CHARMM-GUI account

### Install dependencies

`pip install selenium numpy`

## Usage

Run the script and follow the interactive prompts:

`python charmm_gui_automation.py`

You will be prompted for your CHARMM-GUI **username** and **password**, then asked to choose one of four modes.

## Modes

### 0 — Create Action File

Records a sequence of browser interactions to a JSON file for later replay.

1. The browser opens and you are logged in automatically.
2. At each step, choose the interaction type (see **Interaction Types** below).
3. Perform the action — it is recorded to your named JSON file in real time.
4. Exit when done.

**Use this mode to record a workflow once, then replay it many times.**

### 1 — Replay Action File

Replays a previously recorded action file, distributing the work across multiple parallel browser instances.

- Uses `os.cpu_count() - 1` parallel workers by default.
- Prompts for **Total Iterations** — the total number of complete runs to perform across all workers.
- Displays per-worker progress bars that update every second.

```
Username:
Password 
Action: 1
Action File Name:
Total Iterations: 
```

---

### 2 — Append Action File

Loads an existing action file, replays it to its current end state, then drops into the interactive recorder so you can continue adding steps.

Useful when you need to extend a previously recorded workflow.

---

### 3 — Download TGZ Files

Navigates to your CHARMM-GUI job list and bulk-downloads completed output archives (`.tgz`) for a specified export step number.

- Visits each job in your Job IDs list.
- Finds the "Go" link matching the requested step number.
- Clicks `download.tgz` and waits 2 minutes between downloads.

```
Username: 
Password: 
Action: 
Export Step:
```

---

## Interaction Types (Modes 0 and 2)

When recording, you select the type of browser interaction at each step:

| Input | Type | Description |
|-------|------|-------------|
| `1` | **Click** | Click a button or link by its visible text |
| `2` | **Type** | Enter text into a named input field or textarea |
| `3` | **Dropdown** | Select an option from a `<select>` dropdown |
| `4` | **Bubble** | Toggle a checkbox or radio button |
| `5` | **Next Step** | Click the CHARMM-GUI "Next Step" navigation element and wait for the page to reload |
| `6` | **Extend** | Click an expandable section toggle (lipid type toggles, etc.) |
| `7` | **Exit** | Stop recording and exit |

---

## Action File Format

Action files are plain JSON arrays. Each entry is one recorded interaction. Examplen for a potassium channel system:


## Notes

- **Next Step locking:** In parallel mode, a file lock (`/tmp/charmm_gui_next_step.lock`) prevents multiple workers from clicking "Next Step" simultaneously, which can cause conflicts on the server side. This requires `fcntl` (Linux/macOS only).
- **Headless mode:** The `--headless=new` Chrome option is present in the code but commented out. Uncomment the relevant lines in `parallelsubmission` and the download mode if you want to run without visible browser windows.
- **Timeouts:** Next Step waits up to 10 minutes for the page to reload. Downloads wait 2 minutes per file. Adjust these in the source if your jobs are faster or slower.
- **Platform:** Designed for Linux/macOS due to `fcntl` usage. On Windows, the file-locking context manager would need to be replaced (e.g., with `msvcrt`).

---

## File Structure

```
CHARMM.py   # Main script
Example.json           # Example recorded action file (you create this)
README.md                  # This file
```
