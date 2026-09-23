# SACCO Financial Management System

A menu-driven Python program for managing SACCO members, savings, loans,
repayments, and transactions — with face-based biometric verification
required before a member can withdraw savings or apply for a loan.

## Features

- Register, search, update, and delete members
- Deposit and withdraw savings (withdrawals require biometric verification)
- Apply for, approve/reject, and repay loans (applications require biometric verification)
- Transaction history and financial reports
- Face enrollment and verification using OpenCV (webcam required for biometric features)

## Project files

| File | Purpose |
|---|---|
| `sacco.py` | Main program — run this to start the system |
| `biometric.py` | Face enrollment and verification (OpenCV) |
| `storage.py` | Loads/saves data to `sacco_data.json` |
| `haarcascade_frontalface_default.xml` | Face-detection model used by OpenCV — must stay in the same folder as `biometric.py` |
| `requirements.txt` | Python package dependencies |

---

# Getting started from a brand-new machine

- **Path Pycharm** — Either OS, using PyCharm

The path ends the same way: a project folder containing `sacco.py`, with a
Python virtual environment and dependencies installed, ready to run.

---

## PyCharm (Windows or Mac)

PyCharm can handle Git, the virtual environment, and dependency install for
you through its interface — you still need Git installed on your system
first, PyCharm just calls it from the background.

### 1. Clone the repo

- `File → New → Project from Version Control`
- Paste the repo URL: `https://github.com/Levy-m/sacco_system.git`
- Choose a location on your machine and click **Clone**

### 2. Set up the virtual environment

- PyCharm usually detects there's no interpreter configured and offers to
  create one — accept it, or go to
  `File → Settings → Project: sacco_system → Python Interpreter` (on Mac:
  `PyCharm → Settings → ...`)
- Click **Add Interpreter → Add Local Interpreter → Virtualenv Environment**
- Choose **New**, leave the location as the project's default `venv`
  folder, pick your Python version, click **OK**

### 3. Install dependencies

- Open `requirements.txt` in PyCharm — it usually shows a yellow banner
  offering to **"Install requirements"**; click it
- If it doesn't prompt automatically, open the **Terminal** tab at the
  bottom of PyCharm (this runs inside the venv PyCharm just created) and run:
  ```
  pip install -r requirements.txt
  ```

### 4. Run the program

- Right-click `sacco.py` in the project sidebar → **Run 'sacco'**
- Or open `sacco.py` and click the green ▶ button next to the
  `if __name__ == "__main__":` line

**Important:** this is a terminal (console) program, so PyCharm needs to run
it with an interactive terminal attached so you can type responses to the
menu prompts. This works by default — if typing doesn't register, check
`Run → Edit Configurations` and make sure **"Run with Python Console"**
isn't overriding normal terminal input.

---


## Notes

- On some Linux distributions, `pip install` outside a virtual environment
  will fail with an "externally-managed-environment" error — this is why
  the venv step matters everywhere above; always install inside it.
- The biometric match sensitivity can be tuned in `biometric.py` via the
  `CONFIDENCE_THRESHOLD` constant if verification feels too strict or too loose.