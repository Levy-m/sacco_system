# SACCO Financial Management System

A desktop (GUI) Python application for managing SACCO members, savings,
loans, repayments, and transactions — with face-based biometric verification
required before a member can withdraw savings or apply for a loan.

The GUI is built with Tkinter, which ships with Python. The original
menu-driven console version (`sacco.py`) still works and shares the same
data file.

## Features

- Register, search, update, and delete members
- Deposit and withdraw savings (withdrawals require biometric verification)
- Apply for, approve/reject, and repay loans (applications require biometric verification)
- Transaction history and financial reports
- Face enrollment and verification using OpenCV (webcam required for biometric features)

## Project files

| File | Purpose |
|---|---|
| `sacco_gui.py` | **GUI application — run this to start the system** |
| `sacco.py` | Console (menu) version, and the shared calculation helpers the GUI uses |
| `biometric.py` | Face enrollment and verification (OpenCV) |
| `storage.py` | Loads/saves data to `sacco_data.json` |
| `haarcascade_frontalface_default.xml` | Face-detection model used by OpenCV — must stay in the same folder as `biometric.py` |
| `requirements.txt` | Python package dependencies |

---

# Getting started from a brand-new machine

- **Path Pycharm** — Either OS, using PyCharm

The path ends the same way: a project folder containing `sacco_gui.py`, with a
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

- Right-click `sacco_gui.py` in the project sidebar → **Run 'sacco_gui'**
- Or open `sacco_gui.py` and click the green ▶ button next to the
  `if __name__ == "__main__":` line

The SACCO window opens with a sidebar: **Dashboard, Members, Savings,
Loans, Transactions, Reports**. Withdrawals and loan applications open a
webcam window for face verification (press `q` in that window to cancel).

To run the old console version instead, run `sacco.py` the same way.

### Tkinter on Linux

Windows and Mac Python installers from python.org include Tkinter. On
Linux it is a separate system package — if you see
`ModuleNotFoundError: No module named 'tkinter'`, install it and then
restart PyCharm:

```
sudo apt install python3-tk      # Ubuntu / Debian
sudo dnf install python3-tkinter # Fedora
```

---


## Notes

- On some Linux distributions, `pip install` outside a virtual environment
  will fail with an "externally-managed-environment" error — this is why
  the venv step matters everywhere above; always install inside it.
- The biometric match sensitivity can be tuned in `biometric.py` via the
  `CONFIDENCE_THRESHOLD` constant if verification feels too strict or too loose.