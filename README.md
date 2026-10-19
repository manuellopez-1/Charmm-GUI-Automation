# CHARMM-GUI Automation Tool

**Author:** Manuel Alejandro Lopez (2025–2026)

A Selenium-based browser automation tool for [CHARMM-GUI](https://www.charmm-gui.org/) that records, replays, and parallelizes multi-step molecular system setup workflows. Useful for batch-submitting many identical or similar simulation jobs without having to manually repeat the same steps.

The tool also includes a job monitoring system that tracks CHARMM-GUI calculations and automatically continues once each step has finished processing.

## Requirements

- Python 3.8+
- Google Chrome + compatible ChromeDriver
- A CHARMM-GUI account
- Linux/macOS (for file locking)

### Install dependencies

```bash
pip install selenium numpy
```

## Usage

Run the script and follow the interactive prompts:

```bash
python CHARMM.py
```

You will be prompted for your CHARMM-GUI **username** and **password**, then asked to choose one of four modes.

## Modes

### 0 — Create Action File

Records a sequence of browser interactions to a JSON file for later replay.

1. The browser opens and you are logged in automatically.
2. At each step, choose the interaction type (see **Interaction Types** below).
3. Perform the action — it is recorded to your named JSON file in real time.
4. For calculations requiring processing, the program monitors CHARMM-GUI and continues once the next step is ready.
5. Exit when done.

**Use this mode to record a workflow once, then replay it many times.**

### 1 — Replay Action File

Replays a previously recorded action file, distributing the work across multiple parallel browser instances.

- Uses 2 parallel workers by default (change `numcores` in the source to adjust).
- Prompts for **Total Iterations** — the total number of complete runs to perform across all workers.
- Divides the iterations between workers as evenly as possible.
- Displays per-worker progress percentages that update every second.
- Uses a separate browser for each worker, along with an additional monitoring browser when needed.
- Automatically waits for CHARMM-GUI calculations to finish before advancing to the next action.

```text
Username:
Password:
Action: 1
Action File Name:
Total Iterations:
```

### 2 — Append Action File

Loads an existing action file, replays it to its current end state, then drops into the interactive recorder so you can continue adding steps.

Useful when you need to extend a previously recorded workflow without starting from scratch.

- Replays all existing actions.
- Waits for any intermediate calculations to finish.
- Continues recording from the final page.
- Saves new actions to the same JSON file.

### 3 — Download TGZ Files

Navigates to your CHARMM-GUI job list and bulk-downloads completed output archives (`.tgz`) for a specified export step number.

- Opens the CHARMM-GUI Job IDs manager.
- Finds jobs whose listed step matches the requested export step.
- Visits each matching job.
- Finds the "Go" link associated with that step.
- Clicks `download.tgz` and waits 2 minutes before continuing to the next job.

```text
Username:
Password:
Action: 3
Export Step:
```

---

## Interaction Types (Modes 0 and 2)

When recording, you select the type of browser interaction at each step:

| Input | Type | Description |
|---|---|---|
| `1` | **Click** | Click a button or link by its visible text or attributes |
| `2` | **Type** | Enter text into an input field or textarea |
| `3` | **Dropdown** | Select an option from a `<select>` dropdown |
| `4` | **Bubble** | Toggle a checkbox or radio button |
| `5` | **Next Step** | Submit the current CHARMM-GUI step, monitor the calculation, and continue once finished |
| `6` | **Extend** | Click an expandable section toggle (lipid type toggles, etc.) |
| `7` | **Exit** | Stop recording and exit |

### Handling Identical Input Fields

Some CHARMM-GUI pages contain multiple input fields with the same name or placeholder.

When this happens, the recorder displays all matching fields and asks you to select the correct index.

The selected index is saved in the action file so the same input field can be used during replay.

You can also choose whether pressing Enter should be part of the recorded action.

---

## Automatic Job Monitoring

The updated version includes a system for handling the long processing times between CHARMM-GUI steps.

Previously, advancing to the next step depended on waiting for the page to reload. This becomes unreliable when CHARMM-GUI takes a long time to finish a calculation.

The new system uses a second browser to independently monitor the job.

### How It Works

1. The program identifies the current job ID and step from the CHARMM-GUI URL or page.
2. When a **Next Step** action is reached, the main browser submits the calculation.
3. A separate monitoring browser opens the CHARMM-GUI Job IDs manager.
4. The monitor refreshes every 10 seconds and checks the job's current step and running status.
5. Once the job has advanced to a different step and is marked as finished, the monitoring browser navigates to the new step.
6. The old main browser closes, and the monitoring browser becomes the new main browser.
7. A new monitoring browser is initialized for the next calculation.

This allows workflows with long CHARMM-GUI processing steps to run without manually refreshing the webpage or guessing how long each calculation will take.

### Job Identification

The program uses the job ID to locate the correct calculation in the CHARMM-GUI Job IDs manager.

Job information is extracted from URL parameters including:

- `doc`
- `step`
- `project`
- `jobid`

If the job ID is not available in the URL, the program also attempts to extract it directly from the webpage.

### Parallel Submission Locking

When several workers submit jobs simultaneously, the program uses a shared file lock:

```text
/tmp/charmm_gui_next_step.lock
```

This prevents multiple workers from clicking **Next Step** at exactly the same time.

The lock only applies to submission. Workers can continue interacting with CHARMM-GUI and monitoring their calculations independently.

---

## Action File Format

Action files are plain JSON arrays. Each entry represents one recorded browser interaction.

Example:

```json
[
    {
        "action": "click",
        "text": "Button Name",
        "tag": "a",
        "attrs": {
            "class": "button"
        }
    },
    {
        "action": "type",
        "field": "input_name",
        "text": "example.pdb",
        "hit_enter": false,
        "match_index": 0
    },
    {
        "action": "dropdown",
        "dropdown_name": "selection_name",
        "dropdown_id": "selection_id",
        "option": "Option Name"
    },
    {
        "action": "next_step"
    }
]
```

Additional action types include:

- `check` — records the checkbox or radio button identification and checked state.
- `records` — records an expandable section using its target identifier.

The action files can be reused to reproduce the same CHARMM-GUI setup with different jobs.

---

## Notes

- **Next Step locking:** Uses `fcntl` and a file lock to prevent concurrent submissions from interfering with one another. This requires Linux/macOS.

- **Job monitoring:** The monitor checks the CHARMM-GUI Job IDs manager every 10 seconds. It continues polling until the job has advanced and is no longer marked as running. There is currently no maximum monitoring timeout.

- **Browser switching:** After a completed calculation, the monitoring browser becomes the main browser. This avoids relying on the original submission page to reload correctly.

- **Parallel workers:** The default is currently 2 workers. Change `numcores` in `main()` to increase or decrease the number of simultaneous workflows.

- **Progress tracking:** Displays the percentage of recorded actions completed by each worker. This measures automation progress rather than the internal progress of CHARMM-GUI calculations.

- **Element selection:** The program searches for buttons using visible text and HTML attributes. If a click fails because an element has changed or become stale, it attempts to find an equivalent element and click again.

- **Duplicate fields:** If several textboxes have identical names, the recorder allows you to specify which one to use. This index is preserved during replay.

- **Headless mode:** A `--headless=new` Chrome option is included but commented out in the download section. Browser creation in the other modes can also be modified to run headlessly.

- **Timeouts:** Login operations use a 15-second Selenium wait. The job monitor checks every 10 seconds without a fixed overall timeout. Downloads wait 2 minutes between files. These values can be adjusted in the source.

- **Platform:** Designed for Linux/macOS due to `fcntl` usage. On Windows, the file-locking mechanism would need to be replaced.

- **CHARMM-GUI compatibility:** The automation depends on CHARMM-GUI's webpage layout and HTML elements. Significant changes to the website may require adjustments to the element-selection functions or recorded action files.

---

## File Structure

```text
CHARMM.py       # Main automation script
Example.json    # Example recorded action file
README.md       # Documentation
```

## Typical Workflow

1. Run `CHARMM.py` in **Create Action File** mode.
2. Record the steps required to set up a molecular system in CHARMM-GUI.
3. Save the recorded workflow to a JSON file.
4. Run **Replay Action File** mode and specify the number of systems to create.
5. The program distributes the jobs across workers and monitors the calculations until each recorded workflow is completed.
6. Use **Download TGZ Files** mode to retrieve the generated simulation files.

This is particularly useful for preparing large numbers of molecular systems that require the same CHARMM-GUI setup procedure.
