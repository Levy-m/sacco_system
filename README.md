# SACCO Financial Management System

![Python](https://img.shields.io/badge/Python-3.10%2B-1f3b4d?logo=python&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-Tkinter-2e7d32)
![Biometrics](https://img.shields.io/badge/Biometrics-OpenCV-1565c0?logo=opencv&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-5f6b76)

A desktop application for managing SACCO members, savings, loans,
repayments and transactions. Staff sign in with a username and password,
and sensitive actions (withdrawing savings and applying for a loan) are
protected by face-based biometric verification.

Everything runs in a graphical window: there is no terminal menu to use.

---

## Features

| Area | What you can do |
|---|---|
| **Sign in** | Password-protected staff accounts, with a lockout after repeated failed attempts |
| **Dashboard** | See member count, total savings, loans outstanding, pending applications and recent transactions at a glance |
| **Members** | Register, search, edit and delete members; enroll a member's face; open a full member statement |
| **Savings** | Deposit savings, and withdraw savings after biometric verification |
| **Loans** | Apply for a loan (biometric required), approve or reject applications, record repayments and view loan balances |
| **Transactions** | Browse every transaction, filtered by member and type, with running totals |
| **Reports** | Member list, total savings, loans issued, outstanding loans, repayments, transactions and individual statements |
| **Users** *(administrators only)* | Add staff accounts, reset passwords and remove accounts |

In loan tables, pending applications are highlighted in amber and fully
repaid loans in green, so items needing attention stand out.

---

## Project files

| File | Purpose |
|---|---|
| `sacco_gui.py` | **The application: run this to start the system** |
| `biometric.py` | Face enrollment and verification (OpenCV) |
| `storage.py` | Loads and saves data to `sacco_data.json` |
| `haarcascade_frontalface_default.xml` | Face-detection model used by OpenCV; must stay in the same folder as `biometric.py` |
| `requirements.txt` | Python package dependencies |

Data files are created automatically on first use and are not committed to Git:

- `sacco_data.json` holds members, transactions, loans and staff accounts
  (passwords are stored only as salted hashes, never as plain text)
- `biometric_data/` holds the enrolled face samples and trained model

---

## Requirements

- **Python 3.10 or newer**
- **Tkinter**, the GUI library. It is included with the python.org installers
  for Windows and macOS. On Linux, install it separately
  (see [Tkinter on Linux](#tkinter-on-linux)).
- **A webcam**, for biometric enrollment and verification
- The packages in `requirements.txt` (`opencv-contrib-python`, `numpy`)

---

## Setting up in PyCharm

PyCharm can clone the repository, create the virtual environment and install
the dependencies for you. Git must be installed on your system first;
PyCharm uses it in the background.

### 1. Clone the repository

1. `File → New → Project from Version Control`
2. Paste the repository URL: `https://github.com/Levy-m/sacco_system.git`
3. Choose a location on your machine and click **Clone**

### 2. Create the virtual environment

1. PyCharm usually notices that no interpreter is configured and offers to
   create one: accept it. Otherwise open
   `File → Settings → Project: sacco_system → Python Interpreter`
   (on macOS: `PyCharm → Settings → ...`)
2. Click **Add Interpreter → Add Local Interpreter → Virtualenv Environment**
3. Choose **New**, keep the default `venv` location, pick your Python
   version and click **OK**

### 3. Install the dependencies

- Open `requirements.txt`. PyCharm shows a banner offering to
  **Install requirements**: click it.
- If no banner appears, open the **Terminal** tab at the bottom of PyCharm
  (it runs inside the new virtual environment) and run:
  ```
  pip install -r requirements.txt
  ```

### 4. Run the application

- Right-click `sacco_gui.py` in the project sidebar → **Run 'sacco_gui'**
- Or open `sacco_gui.py` and click the green ▶ button next to
  `if __name__ == "__main__":`

The first time it runs, the application asks you to **create the
administrator account** (username and a password of at least 6 characters).
After that, it opens on the sign-in screen every time.

Once signed in, the application opens on the **Dashboard**. Use the sidebar
on the left to move between pages. From then on, the green ▶ button at the
top right of PyCharm starts the application again.

---

## Signing in and user accounts

- **First run:** the account you create is an **Administrator**.
- **Adding staff:** administrators open the **Users** page and click
  **Add User**. Choose the **Staff** role for day-to-day users. Staff can
  use every page except Users.
- **Forgotten password:** an administrator selects the user on the
  **Users** page and clicks **Reset Password**.
- **Your own password:** click **Change Password** at the bottom of the
  sidebar.
- **Security:** after 5 wrong passwords in a row the sign-in form locks for
  30 seconds. You cannot delete your own account or the last administrator.
- **Log out:** click **Log Out** at the bottom of the sidebar.

---

## Using biometric verification

1. On the **Members** page, select a member and click **Enroll Biometric**.
   A camera window opens and captures 20 face samples. Move your head
   slightly while it captures.
2. When a member withdraws savings or applies for a loan, a camera window
   opens to confirm their identity. The action only goes ahead if the face
   matches.
3. Press `q` in any camera window to cancel.

If a member has not enrolled yet, the application offers to enroll them
before continuing. Camera or OpenCV problems are explained in a pop-up
message.

---

## Troubleshooting

### Tkinter on Linux

If you see `ModuleNotFoundError: No module named 'tkinter'`, install the
system package and then restart PyCharm:

```
sudo apt install python3-tk        # Ubuntu / Debian
sudo dnf install python3-tkinter   # Fedora
```

### Other issues

- **"externally-managed-environment" error on Linux:** always install
  packages inside the project's virtual environment (step 2 above), not
  system-wide.
- **"missing the 'face' module":** uninstall `opencv-python` and install
  `opencv-contrib-python` instead. Only the contrib package includes the
  face recogniser.
- **Verification too strict or too loose:** adjust `CONFIDENCE_THRESHOLD`
  in `biometric.py`. Lower is stricter.
