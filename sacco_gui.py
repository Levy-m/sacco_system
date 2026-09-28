# sacco_gui.py
# SACCO Financial Management System
# A desktop (GUI) program that manages members, savings, loans,
# repayments, transactions and reports.
#
# Built with Tkinter, which ships with Python, so the windows themselves
# need nothing extra installed. Data is kept in sacco_data.json (see
# storage.py) and face verification is handled by biometric.py.
#
# Run this file to start the system.

import contextlib
import hashlib
import hmac
import io
import os
from datetime import date

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

from storage import load_data, save_data
import biometric


# ==========================================================
# SECTION 1: COLOURS AND STYLES
# ==========================================================

SIDEBAR_BG = "#1f3b4d"
SIDEBAR_ACTIVE = "#2f5a75"
SIDEBAR_HIGHLIGHT = "#4fb3a9"
SIDEBAR_FG = "#ffffff"
PAGE_BG = "#f4f6f8"
CARD_BG = "#ffffff"
STRIPE_BG = "#f3f7fa"
TEXT = "#1f2933"
MUTED = "#5f6b76"

# Accent colours: used sparingly for buttons, cards and status text
GREEN = "#2e7d32"
BLUE = "#1565c0"
AMBER = "#b26a00"
RED = "#c62828"
TEAL = "#00796b"

# Loan statuses that deserve attention get a soft row highlight in tables.
# Everything else stays plain dark text on white/striped rows.
STATUS_TAGS = {
    "Pending": {"background": "#fff4e0"},
    "Repaid": {"background": "#e8f5e9"},
    "Rejected": {"foreground": MUTED},
}

ALL_MEMBERS = "All members"

# Screens with display scaling (for example 4K laptops) draw text larger,
# so sizes given in pixels are multiplied by this. Set in setup_styles().
UI_SCALE = 1.0


def px(size):
    """Scale a pixel size to suit the current display."""
    return int(size * UI_SCALE)


def setup_styles(root):
    """Give every ttk widget a consistent, clean look on Windows, Mac and Linux."""
    global UI_SCALE
    style = ttk.Style(root)
    style.theme_use("clam")

    # A 10pt font is about 18px tall on a normal screen; anything taller
    # means the display is scaled, so grow row heights and widths to match.
    line_height = tkfont.Font(root=root, font=("Segoe UI", 10)).metrics("linespace")
    UI_SCALE = max(1.0, line_height / 18)

    style.configure(".", background=PAGE_BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("TFrame", background=PAGE_BG)
    style.configure("TLabel", background=PAGE_BG, foreground=TEXT)
    style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground=SIDEBAR_BG, background=PAGE_BG)
    style.configure("Sub.TLabel", foreground=MUTED, background=PAGE_BG)
    style.configure("Big.TLabel", font=("Segoe UI", 12, "bold"), foreground=SIDEBAR_BG, background=PAGE_BG)
    style.configure("Money.TLabel", font=("Segoe UI", 12, "bold"), foreground=TEAL, background=PAGE_BG)

    # Buttons: green for "go" actions, blue for biometric/secondary actions, red for destructive ones
    style.configure("TButton", padding=(px(10), px(4)))
    for name, colour, pressed in (("Accent", GREEN, "#256628"),
                                  ("Primary", BLUE, "#0f4f96"),
                                  ("Danger", RED, "#a31f1f")):
        style.configure(name + ".TButton", foreground="white", background=colour, bordercolor=colour)
        style.map(name + ".TButton", background=[("active", pressed), ("pressed", pressed)])

    style.configure("Treeview", rowheight=line_height + px(8), background=CARD_BG, fieldbackground=CARD_BG, foreground=TEXT)
    style.map("Treeview", background=[("selected", "#cfe3f1")], foreground=[("selected", TEXT)])
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                    background=SIDEBAR_BG, foreground="white", relief="flat")
    style.map("Treeview.Heading", background=[("active", SIDEBAR_ACTIVE)])

    style.configure("TNotebook", background=PAGE_BG)
    style.configure("TNotebook.Tab", padding=(px(14), px(4)))
    style.map("TNotebook.Tab", background=[("selected", CARD_BG)],
              foreground=[("selected", SIDEBAR_BG)])
    style.configure("TLabelframe", background=PAGE_BG)
    style.configure("TLabelframe.Label", background=PAGE_BG, foreground=SIDEBAR_BG,
                    font=("Segoe UI", 10, "bold"))


# ==========================================================
# SECTION 2: TABLE AND INPUT HELPERS
# ==========================================================

def make_table(parent, columns):
    """
    Build a scrollable table.
    columns is a list of (heading, width, alignment) where alignment is "w" or "e".
    Returns (frame, tree): place the frame, fill the tree.
    """
    frame = ttk.Frame(parent)
    ids = ["c" + str(i) for i in range(len(columns))]
    tree = ttk.Treeview(frame, columns=ids, show="headings", selectmode="browse")

    for column_id, (heading, width, anchor) in zip(ids, columns):
        tree.heading(column_id, text=heading, anchor=anchor)
        # Only the wide text columns (names, emails) take up spare space;
        # short columns like IDs, dates and amounts keep their size.
        tree.column(column_id, width=px(width), minwidth=px(60), anchor=anchor,
                    stretch=width >= 180)

    # Striped rows, plus a soft highlight for loan statuses that need attention
    tree.tag_configure("stripe", background=STRIPE_BG)
    for word, options in STATUS_TAGS.items():
        tree.tag_configure(word, **options)

    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return frame, tree


def fill_table(tree, rows):
    """Replace everything in a table with the given rows."""
    tree.delete(*tree.get_children())
    for index, row in enumerate(rows):
        tags = []
        if index % 2 == 1:
            tags.append("stripe")
        for value in row:
            if value in STATUS_TAGS:
                tags.append(value)
                break
        tree.insert("", "end", values=row, tags=tags)


def selected_value(tree):
    """Return the first column of the selected row, or None if nothing is selected."""
    selection = tree.selection()
    if not selection:
        return None
    return str(tree.item(selection[0], "values")[0])


def parse_amount(text):
    """Turn typed text into a positive amount of money, or show an error and return None."""
    try:
        amount = float(text.strip().replace(",", ""))
    except ValueError:
        messagebox.showerror("Invalid amount", "Please enter a number, for example 1500")
        return None
    if amount <= 0:
        messagebox.showerror("Invalid amount", "The amount must be greater than zero.")
        return None
    return round(amount, 2)


def valid_phone(phone):
    digits = phone.replace("+", "").replace(" ", "")
    return digits.isdigit() and len(digits) >= 9


def valid_email(email):
    return "@" in email and "." in email


# ==========================================================
# SECTION 3: SACCO CALCULATIONS
# These work on the data dictionary only and never touch the screen.
# ==========================================================

def today():
    """Return today's date as text, for example 2026-09-20."""
    return date.today().strftime("%Y-%m-%d")


def money(amount):
    """Format a number as Kenyan money, for example KES 1,500.00."""
    return "KES {:,.2f}".format(amount)


def next_member_id(data):
    """Work out the next member ID, for example SM001, SM002, SM003."""
    highest = 0
    for member in data["members"]:
        try:
            number = int(member["member_id"][2:])
        except ValueError:
            continue
        if number > highest:
            highest = number
    return "SM" + str(highest + 1).zfill(3)


def find_member(data, member_id):
    """Look for a member using their ID. Return the member, or None."""
    for member in data["members"]:
        if member["member_id"].lower() == member_id.lower():
            return member
    return None


def member_name(data, member_id):
    member = find_member(data, member_id)
    return member["full_name"] if member is not None else "Unknown"


def record_transaction(data, member_id, transaction_type, amount):
    """Save one transaction into the transactions list."""
    data["transactions"].append({
        "member_id": member_id,
        "type": transaction_type,
        "amount": amount,
        "date": today()
    })


def savings_balance(data, member_id):
    """Add up the deposits and subtract the withdrawals for one member."""
    balance = 0
    for transaction in data["transactions"]:
        if transaction["member_id"] == member_id:
            if transaction["type"] == "Deposit":
                balance = balance + transaction["amount"]
            elif transaction["type"] == "Withdrawal":
                balance = balance - transaction["amount"]
    return round(balance, 2)


def next_loan_id(data):
    """Work out the next loan ID, for example LN001, LN002."""
    highest = 0
    for loan in data["loans"]:
        try:
            number = int(loan["loan_id"][2:])
        except ValueError:
            continue
        if number > highest:
            highest = number
    return "LN" + str(highest + 1).zfill(3)


def loan_balance(loan):
    """How much of this loan is still owed."""
    return round(loan["amount"] - loan["amount_repaid"], 2)


def total_member_loan_balance(data, member_id):
    """Add up everything a member still owes on all their approved loans."""
    total = 0
    for loan in data["loans"]:
        if loan["member_id"] == member_id and loan["status"] == "Approved":
            total = total + loan_balance(loan)
    return round(total, 2)


def submit_loan_application(data, member_id, amount):
    """Add a new Pending loan application and return it."""
    loan = {
        "loan_id": next_loan_id(data),
        "member_id": member_id,
        "amount": amount,
        "date_applied": today(),
        "status": "Pending",
        "amount_repaid": 0
    }
    data["loans"].append(loan)
    return loan


def member_loans(data, member_id, status=None):
    """All loans of one member, optionally only those with a given status."""
    loans = []
    for loan in data["loans"]:
        if loan["member_id"] == member_id and (status is None or loan["status"] == status):
            loans.append(loan)
    return loans


def capture_output(function, *args):
    """
    Run a function and collect anything it prints, so storage and
    biometric messages can be shown in a pop-up instead of a terminal.
    Returns (result, printed_text).
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = function(*args)
    return result, buffer.getvalue().strip()


# ==========================================================
# SECTION 3B: USER ACCOUNTS (LOGIN)
# Staff accounts are kept in the same data file under "users".
# Passwords are never stored: only a salted PBKDF2 hash of them.
# ==========================================================

PASSWORD_ITERATIONS = 200_000
MIN_PASSWORD_LENGTH = 6
MAX_LOGIN_ATTEMPTS = 5


def hash_password(password, salt=None):
    """Return (salt, hash) as hex text. A new random salt is made if none is given."""
    if salt is None:
        salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt), PASSWORD_ITERATIONS)
    return salt, digest.hex()


def next_user_id(data):
    """Work out the next staff ID, for example US001, US002. Used to store a staff face scan."""
    highest = 0
    for user in data.get("users", []):
        try:
            number = int(user.get("user_id", "US0")[2:])
        except ValueError:
            continue
        highest = max(highest, number)
    return "US" + str(highest + 1).zfill(3)


def make_user(data, username, password, role):
    salt, password_hash = hash_password(password)
    return {"user_id": next_user_id(data), "username": username, "salt": salt,
            "password_hash": password_hash, "role": role, "date_created": today()}


def find_user(data, username):
    for user in data.get("users", []):
        if user["username"].lower() == username.lower():
            return user
    return None


def check_login(data, username, password):
    """Return the user if the username and password are correct, otherwise None."""
    user = find_user(data, username)
    if user is None:
        # Still do the slow hash so a wrong username takes as long as a wrong password
        hash_password(password)
        return None
    salt, password_hash = hash_password(password, user["salt"])
    if hmac.compare_digest(password_hash, user["password_hash"]):
        return user
    return None


def password_problem(password, confirm_password):
    """Return a message describing what is wrong with a new password, or None if it is fine."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return "The password must be at least " + str(MIN_PASSWORD_LENGTH) + " characters long."
    if password != confirm_password:
        return "The two passwords do not match."
    return None


def set_member_password(member, password):
    """Store a member's portal password (as a salted hash) on their member record."""
    member["salt"], member["password_hash"] = hash_password(password)


def member_has_password(member):
    return "password_hash" in member


def check_member_login(data, member_id, password):
    """Return the member if the Member ID and password are correct, otherwise None."""
    member = find_member(data, member_id)
    if member is None or not member_has_password(member):
        hash_password(password)
        return None
    salt, password_hash = hash_password(password, member["salt"])
    if hmac.compare_digest(password_hash, member["password_hash"]):
        return member
    return None


# ==========================================================
# SECTION 3C: ROLES AND PERMISSIONS
# Staff accounts have one of the staff roles below. Members sign in to
# their own portal with the "Member" role and only see their own records.
# ==========================================================

ADMIN = "Administrator"
LOAN_OFFICER = "Loan Officer"
TELLER = "Teller"
MEMBER = "Member"
STAFF_ROLES = [TELLER, LOAN_OFFICER, ADMIN]

# What each staff role is allowed to do
PERMISSIONS = {
    ADMIN: {"view_members", "register_member", "edit_member", "delete_member",
            "enroll_biometric", "savings", "apply_loan", "approve_loans", "repay_loan",
            "view_loans", "view_transactions", "view_reports", "manage_users"},
    # Loan officers assess and decide on loans; they do not handle cash
    LOAN_OFFICER: {"view_members", "apply_loan", "approve_loans", "view_loans",
                   "view_transactions", "view_reports"},
    # Tellers serve members at the counter: registration and cash movements
    TELLER: {"view_members", "register_member", "edit_member", "enroll_biometric",
             "savings", "apply_loan", "repay_loan", "view_loans", "view_transactions"},
    MEMBER: set(),
}

ROLE_DESCRIPTIONS = {
    ADMIN: "Full access, including managing staff accounts",
    LOAN_OFFICER: "Approve or reject loans, view members and reports",
    TELLER: "Register members, deposits, withdrawals and loan repayments",
}


# ==========================================================
# SECTION 4: THE MAIN WINDOW
# ==========================================================

class SaccoApp(tk.Tk):
    """
    The main window. It first shows the login screen; once a staff member
    signs in it shows a navigation sidebar on the left and pages on the right.
    """

    def __init__(self):
        super().__init__()
        self.title("SACCO Financial Management System")
        self.configure(background=PAGE_BG)
        setup_styles(self)

        # Open at about 70% of the screen, centred, whatever the resolution
        width = min(int(self.winfo_screenwidth() * 0.7), px(1400))
        height = min(int(self.winfo_screenheight() * 0.75), px(860))
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 3
        self.geometry(str(width) + "x" + str(height) + "+" + str(x) + "+" + str(y))
        self.minsize(px(980), px(620))

        self.data, problem = capture_output(load_data)
        if problem:
            messagebox.showwarning("Data file", problem)
        self.data.setdefault("users", [])
        # Accounts created before roles were introduced become Tellers
        for user in self.data["users"]:
            if user["role"] not in STAFF_ROLES:
                user["role"] = TELLER
            # Accounts created before face sign-in need an ID to store their face under
            if "user_id" not in user:
                user["user_id"] = next_user_id(self.data)

        self.user = None      # the signed-in staff account, or a small record for a member
        self.member = None    # the member record when a member is signed in
        self.pages = {}
        self.nav_buttons = {}
        self.show_login()

    # ---------- login and logout ----------

    def clear_window(self):
        for child in self.winfo_children():
            child.destroy()
        self.pages = {}
        self.nav_buttons = {}

    def show_login(self):
        """Show the sign-in screen (or the first-time setup screen if there are no accounts)."""
        self.clear_window()
        self.user = None
        self.member = None
        LoginScreen(self).pack(fill="both", expand=True)

    def login(self, user):
        """Called by the login screen once a staff member's password is correct."""
        self.user = user
        self.member = None
        self.clear_window()
        self.build_main_window()

    def login_member(self, member):
        """Called by the login screen once a member's password or face is verified."""
        self.user = {"username": member["full_name"], "role": MEMBER}
        self.member = member
        self.clear_window()
        self.build_main_window()
        # Members who only have a face scan are asked to create a password,
        # once the portal is on screen (they can choose "Later")
        if not member_has_password(member):
            self.after(200, self.prompt_member_password)

    def prompt_member_password(self):
        """Ask a member without a portal password to create one."""
        if self.member is None or member_has_password(self.member):
            return
        dialog = PasswordDialog(
            self, "Create Your Portal Password",
            note="You signed in with a face scan, but you don't have a portal password yet.\n"
                 "Create one so you can also sign in with your Member ID and password.",
            cancel_text="Later")
        self.wait_window(dialog)
        if dialog.result is None:
            return
        set_member_password(self.member, dialog.result[1])
        self.save()
        messagebox.showinfo("Portal password",
                            "Your portal password has been created. You can now sign in with "
                            "Member ID " + self.member["member_id"] + " and your password, "
                            "or with a face scan.")

    def logout(self):
        if messagebox.askyesno("Log out", "Log out of the SACCO system?"):
            self.show_login()

    def can(self, permission):
        """True if the signed-in user's role allows this action."""
        return self.user is not None and permission in PERMISSIONS[self.user["role"]]

    def require(self, permission):
        """Check a permission before an action; explain and return False if it is not allowed."""
        if self.can(permission):
            return True
        messagebox.showerror("Access denied",
                             "Your role (" + self.user["role"] + ") is not allowed to do this.")
        return False

    # ---------- main window ----------

    def build_main_window(self):
        # --- Sidebar ---
        sidebar = tk.Frame(self, background=SIDEBAR_BG, width=px(210))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="SACCO", background=SIDEBAR_BG, foreground=SIDEBAR_FG,
                 font=("Segoe UI", 18, "bold")).pack(pady=(px(22), 0))
        tk.Label(sidebar, text="Financial Management", background=SIDEBAR_BG,
                 foreground="#b7c7d3", font=("Segoe UI", 9)).pack()
        tk.Frame(sidebar, background=SIDEBAR_HIGHLIGHT, height=2, width=px(48)).pack(pady=(px(10), px(18)))

        # --- Page area ---
        content = ttk.Frame(self, padding=(px(24), px(18)))
        content.pack(side="left", fill="both", expand=True)
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        if self.member is not None:
            navigation = [("My Account", MemberHomePage), ("My Loans", MemberLoansPage)]
        else:
            # Each staff page is listed with the permission needed to see it
            all_pages = [
                ("Dashboard", DashboardPage, None),
                ("Members", MembersPage, "view_members"),
                ("Savings", SavingsPage, "savings"),
                ("Loans", LoansPage, "view_loans"),
                ("Transactions", TransactionsPage, "view_transactions"),
                ("Reports", ReportsPage, "view_reports"),
                ("Users", UsersPage, "manage_users"),
            ]
            navigation = []
            for name, page_class, permission in all_pages:
                if permission is None or self.can(permission):
                    navigation.append((name, page_class))

        for name, page_class in navigation:
            page = page_class(content, self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page

            # Each menu item is a thin colour strip (shown when active) plus a flat button
            row = tk.Frame(sidebar, background=SIDEBAR_BG)
            row.pack(fill="x")
            strip = tk.Frame(row, background=SIDEBAR_BG, width=px(4))
            strip.pack(side="left", fill="y")
            button = tk.Button(row, text=name, anchor="w", relief="flat",
                               background=SIDEBAR_BG, foreground=SIDEBAR_FG,
                               activebackground=SIDEBAR_ACTIVE, activeforeground=SIDEBAR_FG,
                               font=("Segoe UI", 10), borderwidth=0, highlightthickness=0,
                               padx=px(18), pady=px(7), cursor="hand2",
                               command=lambda n=name: self.show_page(n))
            button.pack(side="left", fill="x", expand=True)
            self.nav_buttons[name] = (button, strip)

        # --- Signed-in user and log out, pinned to the bottom ---
        footer = tk.Frame(sidebar, background=SIDEBAR_BG)
        footer.pack(side="bottom", fill="x", pady=(0, px(14)))
        tk.Frame(footer, background=SIDEBAR_ACTIVE, height=1).pack(fill="x", padx=px(18), pady=(0, px(10)))
        tk.Label(footer, text=self.user["username"], background=SIDEBAR_BG, foreground=SIDEBAR_FG,
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", padx=px(22))
        tk.Label(footer, text=self.user["role"], background=SIDEBAR_BG, foreground="#b7c7d3",
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=px(22), pady=(0, px(6)))
        footer_actions = [("Change Password", self.change_password)]
        if self.member is None:
            footer_actions.append(("Set Up Face Sign-In", self.enroll_own_face))
        footer_actions.append(("Log Out", self.logout))
        for text, command in footer_actions:
            tk.Button(footer, text=text, anchor="w", relief="flat",
                      background=SIDEBAR_BG, foreground="#b7c7d3",
                      activebackground=SIDEBAR_ACTIVE, activeforeground=SIDEBAR_FG,
                      font=("Segoe UI", 9), borderwidth=0, highlightthickness=0,
                      padx=px(22), pady=px(3), cursor="hand2", command=command).pack(fill="x")

        self.show_page(navigation[0][0])

    def enroll_own_face(self):
        """Let a signed-in staff member capture their own face for face sign-in."""
        if biometric.is_enrolled(self.user["user_id"]):
            if not messagebox.askyesno("Face sign-in", "You already have a face scan on file.\n"
                                                       "Re-capture and replace it?"):
                return
        self.enroll_face(self.user["user_id"], self.user["username"])

    def change_password(self):
        # A member who signed in by face may not have a password yet, so skip "current password"
        has_password = self.member is None or member_has_password(self.member)
        dialog = PasswordDialog(self, "Change Password", ask_current=has_password)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        current, new_password = dialog.result

        if self.member is not None:
            if has_password and check_member_login(self.data, self.member["member_id"], current) is None:
                messagebox.showerror("Change password", "Your current password is incorrect.")
                return
            set_member_password(self.member, new_password)
        else:
            if check_login(self.data, self.user["username"], current) is None:
                messagebox.showerror("Change password", "Your current password is incorrect.")
                return
            self.user["salt"], self.user["password_hash"] = hash_password(new_password)

        self.save()
        messagebox.showinfo("Change password", "Your password has been changed.")

    def show_page(self, name):
        """Bring a page to the front and refresh it with the latest data."""
        for other, (button, strip) in self.nav_buttons.items():
            active = other == name
            button.configure(background=SIDEBAR_ACTIVE if active else SIDEBAR_BG,
                             font=("Segoe UI", 11, "bold" if active else "normal"))
            strip.configure(background=SIDEBAR_HIGHLIGHT if active else SIDEBAR_BG)
        page = self.pages[name]
        page.refresh()
        page.tkraise()

    def save(self):
        """Save to disk and refresh every page so they all show the new data."""
        result, problem = capture_output(save_data, self.data)
        if problem:
            messagebox.showerror("Save failed", problem)
        for page in self.pages.values():
            page.refresh()

    # ---------- member drop-down helpers used by several pages ----------

    def member_choices(self):
        choices = []
        for member in self.data["members"]:
            choices.append(member["member_id"] + " - " + member["full_name"])
        return choices

    def member_from_choice(self, text):
        member_id = text.split(" - ")[0].strip()
        if member_id == "" or member_id == ALL_MEMBERS:
            return None
        return find_member(self.data, member_id)

    # ---------- biometric helpers ----------

    def run_camera(self, action, member_id):
        """
        Run a webcam step (enroll or verify). The camera opens in its own
        window; the main window waits until it is closed.
        Returns (success, messages printed by the biometric module).
        """
        self.config(cursor="watch")
        self.update()
        try:
            return capture_output(action, member_id)
        finally:
            self.config(cursor="")

    def enroll(self, member):
        """Capture a member's face. Returns True on success."""
        return self.enroll_face(member["member_id"], member["full_name"])

    def enroll_face(self, face_id, name):
        """Capture the face of a member or staff account (stored under face_id). Returns True on success."""
        messagebox.showinfo(
            "Biometric enrollment",
            "A camera window will open for " + name + ".\n\n"
            "Look at the camera and move your head slightly while "
            + str(biometric.SAMPLES_PER_MEMBER) + " samples are captured.\n"
            "Press 'q' in the camera window to cancel.")
        success, details = self.run_camera(biometric.enroll_face, face_id)
        if success:
            messagebox.showinfo("Biometric enrollment",
                                "Biometric enrollment successful for " + name + ".")
        else:
            messagebox.showerror("Biometric enrollment",
                                 "Biometric enrollment failed or was cancelled.\n\n" + details)
        self.save()
        return success

    def require_biometric(self, member, action_description):
        """Gate a sensitive action behind face verification. Returns True if verified."""
        if not biometric.is_enrolled(member["member_id"]):
            enroll_now = messagebox.askyesno(
                "Biometric required",
                member["full_name"] + " has not enrolled a biometric yet.\n"
                "Biometric verification is required to " + action_description + ".\n\n"
                "Enroll their biometric now?")
            if not enroll_now or not self.enroll(member):
                messagebox.showwarning("Action cancelled",
                                       "Cannot " + action_description + " without a biometric on file.")
                return False

        ready = messagebox.askokcancel(
            "Biometric verification",
            "Biometric verification is required to " + action_description + ".\n\n"
            "Click OK, then look at the camera. Press 'q' in the camera window to cancel.")
        if not ready:
            return False

        verified, details = self.run_camera(biometric.verify_face, member["member_id"])
        if not verified:
            messagebox.showerror("Verification failed",
                                 "Biometric verification failed. "
                                 + action_description.capitalize() + " has been cancelled for security.\n\n"
                                 + details)
        return verified


class Page(ttk.Frame):
    """Base class for every page: a title, subtitle and a refresh() method."""

    def __init__(self, parent, app, title, subtitle):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text=title, style="Title.TLabel").pack(anchor="w")
        tk.Frame(self, background=SIDEBAR_HIGHLIGHT, height=3, width=48).pack(anchor="w", pady=(2, 6))
        ttk.Label(self, text=subtitle, style="Sub.TLabel").pack(anchor="w", pady=(0, 14))

    @property
    def data(self):
        return self.app.data

    def refresh(self):
        pass


# ==========================================================
# SECTION 5: DASHBOARD
# ==========================================================

class DashboardPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Dashboard", "An overview of the SACCO today")

        cards = ttk.Frame(self)
        cards.pack(fill="x")
        self.card_values = {}
        card_colours = [("Members", BLUE), ("Total Savings", GREEN),
                        ("Loans Outstanding", AMBER), ("Pending Loans", TEAL)]
        for index, (name, colour) in enumerate(card_colours):
            # A white card with a coloured band across the top
            card = tk.Frame(cards, background=CARD_BG, highlightthickness=1,
                            highlightbackground="#dde3e8")
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 12, 0))
            cards.columnconfigure(index, weight=1)
            tk.Frame(card, background=colour, height=4).pack(fill="x")
            tk.Label(card, text=name, background=CARD_BG, foreground=MUTED,
                     font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(12, 0))
            value = tk.Label(card, text="-", background=CARD_BG, foreground=colour,
                             font=("Segoe UI", 16, "bold"))
            value.pack(anchor="w", padx=16, pady=(4, 14))
            self.card_values[name] = value

        ttk.Label(self, text="Recent transactions", style="Big.TLabel").pack(anchor="w", pady=(24, 6))
        frame, self.table = make_table(self, [
            ("Date", 110, "w"), ("Member", 90, "w"), ("Name", 220, "w"),
            ("Type", 150, "w"), ("Amount", 150, "e")])
        frame.pack(fill="both", expand=True)

    def refresh(self):
        total_savings = 0
        for member in self.data["members"]:
            total_savings = total_savings + savings_balance(self.data, member["member_id"])

        outstanding = 0
        pending = 0
        for loan in self.data["loans"]:
            if loan["status"] == "Approved":
                outstanding = outstanding + loan_balance(loan)
            elif loan["status"] == "Pending":
                pending = pending + 1

        self.card_values["Members"].configure(text=str(len(self.data["members"])))
        self.card_values["Total Savings"].configure(text=money(round(total_savings, 2)))
        self.card_values["Loans Outstanding"].configure(text=money(round(outstanding, 2)))
        self.card_values["Pending Loans"].configure(text=str(pending))

        rows = []
        for transaction in reversed(self.data["transactions"][-15:]):
            rows.append((transaction["date"], transaction["member_id"],
                         member_name(self.data, transaction["member_id"]),
                         transaction["type"], money(transaction["amount"])))
        fill_table(self.table, rows)


# ==========================================================
# SECTION 6: MEMBERS
# ==========================================================

class MemberDialog(tk.Toplevel):
    """Pop-up form used to register a new member or edit an existing one."""

    def __init__(self, app, member=None):
        super().__init__(app)
        self.result = None
        self.title("Edit Member" if member else "Register New Member")
        self.configure(background=PAGE_BG)
        self.resizable(False, False)
        self.transient(app)

        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)

        member_id = member["member_id"] if member else next_member_id(app.data)
        ttk.Label(body, text="Member ID:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Label(body, text=member_id, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w")

        self.entries = {}
        fields = [("full_name", "Full Name:"), ("phone", "Phone Number:"), ("email", "Email Address:")]
        for row, (key, label) in enumerate(fields, start=1):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(body, width=34)
            entry.grid(row=row, column=1, pady=4, padx=(10, 0))
            if member:
                entry.insert(0, member[key])
            self.entries[key] = entry

        # Portal password: required for a new member, optional when editing
        self.is_new = member is None
        ttk.Separator(body).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 6))
        if self.is_new:
            hint = "Password the member will use to sign in to their portal."
        elif member_has_password(member):
            hint = "Leave blank to keep the member's current portal password."
        else:
            hint = "This member has no portal password yet. Set one, or leave blank."
        ttk.Label(body, text=hint, style="Sub.TLabel").grid(row=5, column=0, columnspan=2, sticky="w")
        for row, (key, label) in enumerate([("password", "Portal Password:"),
                                            ("confirm", "Confirm Password:")], start=6):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(body, width=34, show="\u2022")
            entry.grid(row=row, column=1, pady=4, padx=(10, 0))
            self.entries[key] = entry

        buttons = ttk.Frame(body)
        buttons.grid(row=8, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Save", style="Accent.TButton",
                   command=self.on_save).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda event: self.on_save())
        self.bind("<Escape>", lambda event: self.destroy())
        self.entries["full_name"].focus_set()
        # Make the dialog modal (the window must be visible before it can grab input)
        self.wait_visibility()
        self.grab_set()

    def on_save(self):
        full_name = self.entries["full_name"].get().strip()
        phone = self.entries["phone"].get().strip()
        email = self.entries["email"].get().strip()

        if full_name == "":
            messagebox.showerror("Missing name", "Full name cannot be left blank.", parent=self)
            return
        if not valid_phone(phone):
            messagebox.showerror("Invalid phone",
                                 "Please enter a valid phone number, for example 0712345678", parent=self)
            return
        if not valid_email(email):
            messagebox.showerror("Invalid email",
                                 "Please enter a valid email address, for example jane@gmail.com", parent=self)
            return

        password = self.entries["password"].get()
        confirm_password = self.entries["confirm"].get()
        if self.is_new or password or confirm_password:
            problem = password_problem(password, confirm_password)
            if problem:
                messagebox.showerror("Portal password", problem, parent=self)
                return
        else:
            password = None

        self.result = {"full_name": full_name, "phone": phone, "email": email}
        self.password = password
        self.destroy()


class StatementWindow(tk.Toplevel):
    """A full financial statement for one member."""

    def __init__(self, app, member):
        super().__init__(app)
        data = app.data
        member_id = member["member_id"]
        self.title("Statement - " + member["full_name"])
        self.geometry("820x640")
        self.configure(background=PAGE_BG)

        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text=member["full_name"], style="Title.TLabel").pack(anchor="w")
        details = (member_id + "   |   " + member["phone"] + "   |   " + member["email"]
                   + "   |   Registered " + member["date_registered"])
        ttk.Label(body, text=details, style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

        summary = ttk.Frame(body)
        summary.pack(fill="x", pady=(0, 12))
        ttk.Label(summary, text="Savings balance: " + money(savings_balance(data, member_id)),
                  style="Money.TLabel").pack(side="left")
        ttk.Label(summary, text="Total loans owed: " + money(total_member_loan_balance(data, member_id)),
                  style="Big.TLabel").pack(side="right")

        ttk.Label(body, text="Transactions", style="Big.TLabel").pack(anchor="w")
        frame, table = make_table(body, [("Date", 120, "w"), ("Type", 200, "w"), ("Amount", 160, "e")])
        frame.pack(fill="both", expand=True, pady=(4, 12))
        rows = []
        for transaction in data["transactions"]:
            if transaction["member_id"] == member_id:
                rows.append((transaction["date"], transaction["type"], money(transaction["amount"])))
        fill_table(table, rows)

        ttk.Label(body, text="Loans", style="Big.TLabel").pack(anchor="w")
        frame, table = make_table(body, [
            ("Loan ID", 90, "w"), ("Amount", 140, "e"), ("Repaid", 140, "e"),
            ("Balance", 140, "e"), ("Status", 100, "w"), ("Applied", 110, "w")])
        frame.pack(fill="both", expand=True, pady=(4, 12))
        rows = []
        for loan in member_loans(data, member_id):
            rows.append((loan["loan_id"], money(loan["amount"]), money(loan["amount_repaid"]),
                         money(loan_balance(loan)), loan["status"], loan["date_applied"]))
        fill_table(table, rows)

        ttk.Button(body, text="Close", command=self.destroy).pack(anchor="e")


class MembersPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Members", "Register, search, update and remove SACCO members")

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Label(toolbar, text="Search:").pack(side="left")
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *args: self.refresh())
        ttk.Entry(toolbar, textvariable=self.search, width=28).pack(side="left", padx=(6, 16))

        # Only show the buttons the signed-in role is allowed to use
        if app.can("register_member"):
            ttk.Button(toolbar, text="Register Member", style="Accent.TButton",
                       command=self.register).pack(side="left", padx=(0, 8))
        if app.can("edit_member"):
            ttk.Button(toolbar, text="Edit", command=self.edit).pack(side="left", padx=(0, 8))
        if app.can("enroll_biometric"):
            ttk.Button(toolbar, text="Enroll Biometric", style="Primary.TButton",
                       command=self.enroll).pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Statement", command=self.statement).pack(side="left")
        if app.can("delete_member"):
            ttk.Button(toolbar, text="Delete", style="Danger.TButton",
                       command=self.delete).pack(side="right")

        frame, self.table = make_table(self, [
            ("ID", 80, "w"), ("Full Name", 200, "w"), ("Phone", 130, "w"),
            ("Email", 200, "w"), ("Joined", 100, "w"), ("Savings", 140, "e"),
            ("Biometric", 100, "w"), ("Portal", 90, "w")])
        frame.pack(fill="both", expand=True)
        self.table.bind("<Double-1>", lambda event: self.statement())

        self.count_label = ttk.Label(self, style="Sub.TLabel")
        self.count_label.pack(anchor="w", pady=(8, 0))

    def refresh(self):
        term = self.search.get().strip().lower()
        rows = []
        for member in self.data["members"]:
            if term and term not in member["member_id"].lower() and term not in member["full_name"].lower():
                continue
            bio_status = "Enrolled" if biometric.is_enrolled(member["member_id"]) else "Not set"
            portal_status = "Password" if member_has_password(member) else "Not set"
            rows.append((member["member_id"], member["full_name"], member["phone"], member["email"],
                         member["date_registered"], money(savings_balance(self.data, member["member_id"])),
                         bio_status, portal_status))
        fill_table(self.table, rows)
        self.count_label.configure(text="Showing " + str(len(rows)) + " of "
                                   + str(len(self.data["members"])) + " members")

    def selected_member(self):
        member_id = selected_value(self.table)
        if member_id is None:
            messagebox.showinfo("No member selected", "Please select a member in the table first.")
            return None
        return find_member(self.data, member_id)

    def register(self):
        if not self.app.require("register_member"):
            return
        dialog = MemberDialog(self.app)
        self.app.wait_window(dialog)
        if dialog.result is None:
            return

        member = {"member_id": next_member_id(self.data)}
        member.update(dialog.result)
        member["date_registered"] = today()
        set_member_password(member, dialog.password)
        self.data["members"].append(member)
        self.app.save()

        if messagebox.askyesno("Member registered",
                               member["full_name"] + " registered as " + member["member_id"] + ".\n\n"
                               "Enroll their biometric (face) now?"):
            self.app.enroll(member)

    def edit(self):
        if not self.app.require("edit_member"):
            return
        member = self.selected_member()
        if member is None:
            return
        dialog = MemberDialog(self.app, member)
        self.app.wait_window(dialog)
        if dialog.result is not None:
            member.update(dialog.result)
            if dialog.password is not None:
                set_member_password(member, dialog.password)
            self.app.save()
            messagebox.showinfo("Member updated", "Member details updated successfully!")

    def enroll(self):
        if not self.app.require("enroll_biometric"):
            return
        member = self.selected_member()
        if member is None:
            return
        if biometric.is_enrolled(member["member_id"]):
            if not messagebox.askyesno("Already enrolled",
                                       member["full_name"] + " already has a biometric on file.\n"
                                       "Re-capture and replace it?"):
                return
        self.app.enroll(member)

    def statement(self):
        member = self.selected_member()
        if member is not None:
            StatementWindow(self.app, member)

    def delete(self):
        if not self.app.require("delete_member"):
            return
        member = self.selected_member()
        if member is None:
            return

        # A member who still owes the SACCO money may not be deleted
        owed = total_member_loan_balance(self.data, member["member_id"])
        if owed > 0:
            messagebox.showerror("Cannot delete",
                                 member["full_name"] + " still has an outstanding loan of " + money(owed) + ".")
            return

        if not messagebox.askyesno("Delete member",
                                   "Delete " + member["full_name"] + " (" + member["member_id"] + ")?\n\n"
                                   "Their transactions and loan records will also be removed.",
                                   icon="warning"):
            return

        member_id = member["member_id"]
        self.data["members"].remove(member)
        self.data["transactions"] = [t for t in self.data["transactions"] if t["member_id"] != member_id]
        self.data["loans"] = [loan for loan in self.data["loans"] if loan["member_id"] != member_id]
        self.app.save()
        messagebox.showinfo("Member deleted", "Member deleted successfully.")


# ==========================================================
# SECTION 7: SAVINGS
# ==========================================================

class SavingsPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Savings", "Deposit and withdraw member savings")

        form = ttk.LabelFrame(self, text="Member savings", padding=16)
        form.pack(fill="x")

        ttk.Label(form, text="Member:").grid(row=0, column=0, sticky="w")
        self.member_box = ttk.Combobox(form, state="readonly", width=40)
        self.member_box.grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.member_box.bind("<<ComboboxSelected>>", lambda event: self.show_member())

        self.balance_label = ttk.Label(form, text="Select a member to see their balance", style="Money.TLabel")
        self.balance_label.grid(row=0, column=2, sticky="w", padx=(30, 0))

        ttk.Label(form, text="Amount (KES):").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.amount = ttk.Entry(form, width=20)
        self.amount.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(12, 0))

        buttons = ttk.Frame(form)
        buttons.grid(row=1, column=2, sticky="w", padx=(30, 0), pady=(12, 0))
        ttk.Button(buttons, text="Deposit", style="Accent.TButton", command=self.deposit).pack(side="left")
        ttk.Button(buttons, text="Withdraw (Biometric)", style="Primary.TButton", command=self.withdraw).pack(side="left", padx=(8, 0))

        ttk.Label(self, text="Savings transaction history", style="Big.TLabel").pack(anchor="w", pady=(20, 6))
        frame, self.table = make_table(self, [("Date", 120, "w"), ("Type", 200, "w"), ("Amount", 160, "e")])
        frame.pack(fill="both", expand=True)

    def refresh(self):
        self.member_box.configure(values=self.app.member_choices())
        member = self.app.member_from_choice(self.member_box.get())
        if member is None:
            self.member_box.set("")
        self.show_member()

    def show_member(self):
        member = self.app.member_from_choice(self.member_box.get())
        if member is None:
            self.balance_label.configure(text="Select a member to see their balance")
            fill_table(self.table, [])
            return

        self.balance_label.configure(text="Savings: " + money(savings_balance(self.data, member["member_id"])))
        rows = []
        for transaction in self.data["transactions"]:
            if transaction["member_id"] == member["member_id"]:
                rows.append((transaction["date"], transaction["type"], money(transaction["amount"])))
        fill_table(self.table, rows)

    def chosen_member(self):
        member = self.app.member_from_choice(self.member_box.get())
        if member is None:
            messagebox.showinfo("No member selected", "Please choose a member first.")
        return member

    def deposit(self):
        if not self.app.require("savings"):
            return
        member = self.chosen_member()
        if member is None:
            return
        amount = parse_amount(self.amount.get())
        if amount is None:
            return

        record_transaction(self.data, member["member_id"], "Deposit", amount)
        self.app.save()
        self.amount.delete(0, "end")
        messagebox.showinfo("Deposit recorded",
                            "Deposit of " + money(amount) + " recorded successfully!\n"
                            "New savings balance: " + money(savings_balance(self.data, member["member_id"])))

    def withdraw(self):
        if not self.app.require("savings"):
            return
        member = self.chosen_member()
        if member is None:
            return

        balance = savings_balance(self.data, member["member_id"])
        if balance <= 0:
            messagebox.showerror("No savings", "This member has no savings to withdraw.")
            return

        amount = parse_amount(self.amount.get())
        if amount is None:
            return
        if amount > balance:
            messagebox.showerror("Withdrawal failed",
                                 "The amount is more than the available savings of " + money(balance) + ".")
            return

        # --- Biometric gate ---
        if not self.app.require_biometric(member, "withdraw savings"):
            return

        record_transaction(self.data, member["member_id"], "Withdrawal", amount)
        self.app.save()
        self.amount.delete(0, "end")
        messagebox.showinfo("Withdrawal recorded",
                            "Withdrawal of " + money(amount) + " recorded successfully!\n"
                            "New savings balance: " + money(savings_balance(self.data, member["member_id"])))


# ==========================================================
# SECTION 8: LOANS
# ==========================================================

class LoansPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Loans", "Apply for, approve and repay loans")

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True)

        # Only build the tabs the signed-in role is allowed to use
        self.has_apply = app.can("apply_loan")
        self.has_approve = app.can("approve_loans")
        self.has_repay = app.can("repay_loan")
        if self.has_apply:
            self.build_apply_tab(tabs)
        if self.has_approve:
            self.build_approve_tab(tabs)
        if self.has_repay:
            self.build_repay_tab(tabs)
        self.build_all_loans_tab(tabs)

    # ---------- Tab 1: apply ----------

    def build_apply_tab(self, tabs):
        tab = ttk.Frame(tabs, padding=20)
        tabs.add(tab, text="Apply for Loan")

        ttk.Label(tab, text="Member:").grid(row=0, column=0, sticky="w", pady=6)
        self.apply_member = ttk.Combobox(tab, state="readonly", width=40)
        self.apply_member.grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.apply_member.bind("<<ComboboxSelected>>", lambda event: self.show_apply_member())

        self.apply_info = ttk.Label(tab, text="", style="Sub.TLabel")
        self.apply_info.grid(row=1, column=1, sticky="w", padx=(10, 0))

        ttk.Label(tab, text="Loan amount (KES):").grid(row=2, column=0, sticky="w", pady=6)
        self.apply_amount = ttk.Entry(tab, width=20)
        self.apply_amount.grid(row=2, column=1, sticky="w", padx=(10, 0))

        ttk.Button(tab, text="Submit Application (Biometric)", style="Primary.TButton",
                   command=self.apply).grid(row=3, column=1, sticky="w", padx=(10, 0), pady=(14, 0))

    def show_apply_member(self):
        member = self.app.member_from_choice(self.apply_member.get())
        if member is None:
            self.apply_info.configure(text="")
            return
        self.apply_info.configure(
            text="Savings: " + money(savings_balance(self.data, member["member_id"]))
                 + "     Currently owes: " + money(total_member_loan_balance(self.data, member["member_id"])))

    def apply(self):
        if not self.app.require("apply_loan"):
            return
        member = self.app.member_from_choice(self.apply_member.get())
        if member is None:
            messagebox.showinfo("No member selected", "Please choose a member first.")
            return
        amount = parse_amount(self.apply_amount.get())
        if amount is None:
            return

        # --- Biometric gate ---
        if not self.app.require_biometric(member, "apply for a loan"):
            return

        loan = submit_loan_application(self.data, member["member_id"], amount)
        self.app.save()
        self.apply_amount.delete(0, "end")
        messagebox.showinfo("Application submitted",
                            "Loan application submitted successfully!\n\n"
                            "Loan ID : " + loan["loan_id"] + "\n"
                            "Amount  : " + money(amount) + "\n"
                            "Status  : Pending")

    # ---------- Tab 2: approve / reject ----------

    def build_approve_tab(self, tabs):
        tab = ttk.Frame(tabs, padding=20)
        tabs.add(tab, text="Approve / Reject")

        frame, self.pending_table = make_table(tab, [
            ("Loan ID", 90, "w"), ("Member", 90, "w"), ("Name", 220, "w"),
            ("Amount", 150, "e"), ("Savings", 150, "e"), ("Applied", 110, "w")])
        frame.pack(fill="both", expand=True)

        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Approve", style="Accent.TButton",
                   command=lambda: self.decide("Approved")).pack(side="left")
        ttk.Button(buttons, text="Reject", style="Danger.TButton",
                   command=lambda: self.decide("Rejected")).pack(side="left", padx=(8, 0))

    def decide(self, status):
        if not self.app.require("approve_loans"):
            return
        loan_id = selected_value(self.pending_table)
        if loan_id is None:
            messagebox.showinfo("No loan selected", "Please select a pending loan first.")
            return

        loan = None
        for candidate in self.data["loans"]:
            if candidate["loan_id"] == loan_id and candidate["status"] == "Pending":
                loan = candidate
        if loan is None:
            return

        verb = "approve" if status == "Approved" else "reject"
        if not messagebox.askyesno("Confirm", "Do you want to " + verb + " loan " + loan_id + " of "
                                   + money(loan["amount"]) + " for "
                                   + member_name(self.data, loan["member_id"]) + "?"):
            return

        loan["status"] = status
        loan["date_decided"] = today()
        self.app.save()
        messagebox.showinfo("Decision recorded", "Loan " + loan_id + " has been " + status.upper() + ".")

    # ---------- Tab 3: repayment ----------

    def build_repay_tab(self, tabs):
        tab = ttk.Frame(tabs, padding=20)
        tabs.add(tab, text="Make Repayment")

        top = ttk.Frame(tab)
        top.pack(fill="x")
        ttk.Label(top, text="Member:").pack(side="left")
        self.repay_member = ttk.Combobox(top, state="readonly", width=40)
        self.repay_member.pack(side="left", padx=(10, 0))
        self.repay_member.bind("<<ComboboxSelected>>", lambda event: self.show_active_loans())

        ttk.Label(tab, text="Active loans (select one):", style="Sub.TLabel").pack(anchor="w", pady=(14, 4))
        frame, self.active_table = make_table(tab, [
            ("Loan ID", 90, "w"), ("Amount", 150, "e"), ("Repaid", 150, "e"), ("Balance", 150, "e")])
        frame.pack(fill="both", expand=True)

        bottom = ttk.Frame(tab)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Label(bottom, text="Repayment amount (KES):").pack(side="left")
        self.repay_amount = ttk.Entry(bottom, width=20)
        self.repay_amount.pack(side="left", padx=(10, 10))
        ttk.Button(bottom, text="Record Repayment", style="Accent.TButton",
                   command=self.repay).pack(side="left")

    def show_active_loans(self):
        member = self.app.member_from_choice(self.repay_member.get())
        rows = []
        if member is not None:
            for loan in member_loans(self.data, member["member_id"], "Approved"):
                rows.append((loan["loan_id"], money(loan["amount"]),
                             money(loan["amount_repaid"]), money(loan_balance(loan))))
        fill_table(self.active_table, rows)

    def repay(self):
        if not self.app.require("repay_loan"):
            return
        member = self.app.member_from_choice(self.repay_member.get())
        if member is None:
            messagebox.showinfo("No member selected", "Please choose a member first.")
            return

        loan_id = selected_value(self.active_table)
        if loan_id is None:
            messagebox.showinfo("No loan selected", "Please select the loan being repaid.")
            return

        chosen = None
        for loan in member_loans(self.data, member["member_id"], "Approved"):
            if loan["loan_id"] == loan_id:
                chosen = loan
        if chosen is None:
            return

        amount = parse_amount(self.repay_amount.get())
        if amount is None:
            return
        if amount > loan_balance(chosen):
            messagebox.showerror("Repayment failed",
                                 "That is more than the outstanding balance of "
                                 + money(loan_balance(chosen)) + ".")
            return

        chosen["amount_repaid"] = round(chosen["amount_repaid"] + amount, 2)
        record_transaction(self.data, member["member_id"], "Loan Repayment", amount)

        # If the loan is now fully paid we mark it as cleared
        if loan_balance(chosen) == 0:
            chosen["status"] = "Repaid"
            chosen["date_cleared"] = today()

        self.app.save()
        self.repay_amount.delete(0, "end")

        message = ("Repayment of " + money(amount) + " recorded successfully!\n"
                   "Remaining balance on " + chosen["loan_id"] + ": " + money(loan_balance(chosen)))
        if chosen["status"] == "Repaid":
            message = message + "\n\nThis loan has been fully repaid. Thank you!"
        messagebox.showinfo("Repayment recorded", message)

    # ---------- Tab 4: all loans ----------

    def build_all_loans_tab(self, tabs):
        tab = ttk.Frame(tabs, padding=20)
        tabs.add(tab, text="Loan Balances")

        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Show loans for:").pack(side="left")
        self.balance_member = ttk.Combobox(top, state="readonly", width=40)
        self.balance_member.pack(side="left", padx=(10, 0))
        self.balance_member.bind("<<ComboboxSelected>>", lambda event: self.show_all_loans())

        frame, self.all_table = make_table(tab, [
            ("Loan ID", 80, "w"), ("Member", 80, "w"), ("Name", 180, "w"), ("Amount", 130, "e"),
            ("Repaid", 130, "e"), ("Balance", 130, "e"), ("Status", 90, "w"), ("Applied", 100, "w")])
        frame.pack(fill="both", expand=True)

        self.all_total = ttk.Label(tab, style="Big.TLabel")
        self.all_total.pack(anchor="e", pady=(8, 0))

    def show_all_loans(self):
        member = self.app.member_from_choice(self.balance_member.get())
        rows = []
        outstanding = 0
        for loan in self.data["loans"]:
            if member is not None and loan["member_id"] != member["member_id"]:
                continue
            if loan["status"] == "Approved":
                outstanding = outstanding + loan_balance(loan)
            rows.append((loan["loan_id"], loan["member_id"], member_name(self.data, loan["member_id"]),
                         money(loan["amount"]), money(loan["amount_repaid"]), money(loan_balance(loan)),
                         loan["status"], loan["date_applied"]))
        fill_table(self.all_table, rows)
        self.all_total.configure(text="Total still outstanding: " + money(round(outstanding, 2)))

    # ---------- refresh every tab ----------

    def refresh(self):
        choices = self.app.member_choices()
        boxes = []
        if self.has_apply:
            boxes.append(self.apply_member)
        if self.has_repay:
            boxes.append(self.repay_member)
        for box in boxes:
            box.configure(values=choices)
            if self.app.member_from_choice(box.get()) is None:
                box.set("")

        self.balance_member.configure(values=[ALL_MEMBERS] + choices)
        if self.app.member_from_choice(self.balance_member.get()) is None:
            self.balance_member.set(ALL_MEMBERS)

        if self.has_approve:
            rows = []
            for loan in self.data["loans"]:
                if loan["status"] == "Pending":
                    rows.append((loan["loan_id"], loan["member_id"], member_name(self.data, loan["member_id"]),
                                 money(loan["amount"]), money(savings_balance(self.data, loan["member_id"])),
                                 loan["date_applied"]))
            fill_table(self.pending_table, rows)

        if self.has_apply:
            self.show_apply_member()
        if self.has_repay:
            self.show_active_loans()
        self.show_all_loans()


# ==========================================================
# SECTION 9: TRANSACTIONS
# ==========================================================

class TransactionsPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Transactions", "Every deposit, withdrawal and loan repayment")

        filters = ttk.Frame(self)
        filters.pack(fill="x", pady=(0, 10))
        ttk.Label(filters, text="Member:").pack(side="left")
        self.member_box = ttk.Combobox(filters, state="readonly", width=36)
        self.member_box.pack(side="left", padx=(6, 16))
        ttk.Label(filters, text="Type:").pack(side="left")
        self.type_box = ttk.Combobox(filters, state="readonly", width=18,
                                     values=["All types", "Deposit", "Withdrawal", "Loan Repayment"])
        self.type_box.set("All types")
        self.type_box.pack(side="left", padx=(6, 0))
        for box in (self.member_box, self.type_box):
            box.bind("<<ComboboxSelected>>", lambda event: self.refresh())

        frame, self.table = make_table(self, [
            ("Date", 110, "w"), ("Member", 90, "w"), ("Name", 220, "w"),
            ("Type", 150, "w"), ("Amount", 150, "e")])
        frame.pack(fill="both", expand=True)

        self.total_label = ttk.Label(self, style="Big.TLabel")
        self.total_label.pack(anchor="e", pady=(8, 0))

    def refresh(self):
        self.member_box.configure(values=[ALL_MEMBERS] + self.app.member_choices())
        member = self.app.member_from_choice(self.member_box.get())
        if member is None:
            self.member_box.set(ALL_MEMBERS)
        chosen_type = self.type_box.get()

        rows = []
        total = 0
        for transaction in self.data["transactions"]:
            if member is not None and transaction["member_id"] != member["member_id"]:
                continue
            if chosen_type != "All types" and transaction["type"] != chosen_type:
                continue
            total = total + transaction["amount"]
            rows.append((transaction["date"], transaction["member_id"],
                         member_name(self.data, transaction["member_id"]),
                         transaction["type"], money(transaction["amount"])))
        fill_table(self.table, rows)
        self.total_label.configure(text=str(len(rows)) + " transactions   |   Total: " + money(round(total, 2)))


# ==========================================================
# SECTION 10: REPORTS
# ==========================================================

class ReportsPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Reports", "Financial reports for the whole SACCO")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        menu = ttk.Frame(body)
        menu.pack(side="left", fill="y", padx=(0, 20))

        self.reports = [
            ("List of SACCO Members", self.report_members),
            ("Total SACCO Savings", self.report_total_savings),
            ("Total Loans Issued", self.report_loans_issued),
            ("Outstanding Loans", self.report_outstanding_loans),
            ("Loan Repayment Report", self.report_repayments),
            ("Transaction Report", self.report_transactions),
        ]
        for name, function in self.reports:
            ttk.Button(menu, text=name, width=26,
                       command=lambda n=name, f=function: self.show_report(n, f)).pack(fill="x", pady=3)

        ttk.Separator(menu).pack(fill="x", pady=12)
        ttk.Label(menu, text="Member statement:").pack(anchor="w")
        self.statement_member = ttk.Combobox(menu, state="readonly", width=26)
        self.statement_member.pack(fill="x", pady=(4, 6))
        ttk.Button(menu, text="Open Statement", style="Primary.TButton", command=self.open_statement).pack(fill="x")

        self.report_area = ttk.Frame(body)
        self.report_area.pack(side="left", fill="both", expand=True)
        self.current = self.reports[0]

    def refresh(self):
        self.statement_member.configure(values=self.app.member_choices())
        self.show_report(*self.current)

    def show_report(self, name, function):
        """Clear the report area and draw the chosen report."""
        self.current = (name, function)
        for child in self.report_area.winfo_children():
            child.destroy()

        columns, rows, summary = function()
        ttk.Label(self.report_area, text=name, style="Big.TLabel").pack(anchor="w", pady=(0, 6))
        frame, table = make_table(self.report_area, columns)
        frame.pack(fill="both", expand=True)
        fill_table(table, rows)
        ttk.Label(self.report_area, text=summary, style="Big.TLabel").pack(anchor="e", pady=(8, 0))

    def open_statement(self):
        member = self.app.member_from_choice(self.statement_member.get())
        if member is None:
            messagebox.showinfo("No member selected", "Please choose a member first.")
            return
        StatementWindow(self.app, member)

    # Each report returns (columns, rows, summary text)

    def report_members(self):
        rows = []
        for member in self.data["members"]:
            rows.append((member["member_id"], member["full_name"], member["phone"],
                         member["email"], member["date_registered"]))
        columns = [("ID", 80, "w"), ("Full Name", 200, "w"), ("Phone", 130, "w"),
                   ("Email", 200, "w"), ("Joined", 100, "w")]
        return columns, rows, "Total members: " + str(len(rows))

    def report_total_savings(self):
        rows = []
        total = 0
        for member in self.data["members"]:
            balance = savings_balance(self.data, member["member_id"])
            total = total + balance
            rows.append((member["member_id"], member["full_name"], money(balance)))
        columns = [("ID", 80, "w"), ("Member", 240, "w"), ("Savings", 160, "e")]
        return columns, rows, "TOTAL SACCO SAVINGS: " + money(round(total, 2))

    def report_loans_issued(self):
        rows = []
        total = 0
        for loan in self.data["loans"]:
            if loan["status"] == "Approved" or loan["status"] == "Repaid":
                total = total + loan["amount"]
                rows.append((loan["loan_id"], loan["member_id"], member_name(self.data, loan["member_id"]),
                             money(loan["amount"]), loan["status"]))
        columns = [("Loan ID", 80, "w"), ("Member", 80, "w"), ("Name", 200, "w"),
                   ("Amount", 150, "e"), ("Status", 100, "w")]
        return columns, rows, "Loans issued: " + str(len(rows)) + "   |   Total value: " + money(round(total, 2))

    def report_outstanding_loans(self):
        rows = []
        total = 0
        for loan in self.data["loans"]:
            if loan["status"] == "Approved" and loan_balance(loan) > 0:
                total = total + loan_balance(loan)
                rows.append((loan["loan_id"], member_name(self.data, loan["member_id"]),
                             money(loan["amount"]), money(loan["amount_repaid"]), money(loan_balance(loan))))
        columns = [("Loan ID", 80, "w"), ("Name", 200, "w"), ("Amount", 140, "e"),
                   ("Repaid", 140, "e"), ("Balance", 140, "e")]
        return columns, rows, "Total outstanding: " + money(round(total, 2))

    def report_repayments(self):
        rows = []
        total = 0
        for transaction in self.data["transactions"]:
            if transaction["type"] == "Loan Repayment":
                total = total + transaction["amount"]
                rows.append((transaction["date"], transaction["member_id"],
                             member_name(self.data, transaction["member_id"]), money(transaction["amount"])))
        columns = [("Date", 110, "w"), ("Member", 80, "w"), ("Name", 220, "w"), ("Amount", 150, "e")]
        return columns, rows, "Total repaid: " + money(round(total, 2))

    def report_transactions(self):
        rows = []
        for transaction in self.data["transactions"]:
            rows.append((transaction["date"], transaction["member_id"],
                         member_name(self.data, transaction["member_id"]),
                         transaction["type"], money(transaction["amount"])))
        columns = [("Date", 110, "w"), ("Member", 80, "w"), ("Name", 200, "w"),
                   ("Type", 150, "w"), ("Amount", 140, "e")]
        return columns, rows, "Total transactions: " + str(len(rows))


# ==========================================================
# SECTION 10B: MEMBER PORTAL
# What a member sees after signing in. Every page only reads the
# signed-in member's own records (self.app.member).
# ==========================================================

class MemberHomePage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "My Account",
                         "Welcome, " + app.member["full_name"] + " (" + app.member["member_id"] + ")")

        cards = ttk.Frame(self)
        cards.pack(fill="x")
        self.card_values = {}
        for index, (name, colour) in enumerate([("Savings Balance", GREEN), ("Loans Owed", AMBER),
                                                ("Pending Applications", TEAL)]):
            card = tk.Frame(cards, background=CARD_BG, highlightthickness=1,
                            highlightbackground="#dde3e8")
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 12, 0))
            cards.columnconfigure(index, weight=1)
            tk.Frame(card, background=colour, height=4).pack(fill="x")
            tk.Label(card, text=name, background=CARD_BG, foreground=MUTED,
                     font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(12, 0))
            value = tk.Label(card, text="-", background=CARD_BG, foreground=colour,
                             font=("Segoe UI", 16, "bold"))
            value.pack(anchor="w", padx=16, pady=(4, 14))
            self.card_values[name] = value

        heading = ttk.Frame(self)
        heading.pack(fill="x", pady=(24, 6))
        ttk.Label(heading, text="My transactions", style="Big.TLabel").pack(side="left")
        ttk.Button(heading, text="View Full Statement", style="Primary.TButton",
                   command=lambda: StatementWindow(self.app, self.app.member)).pack(side="right")

        frame, self.table = make_table(self, [("Date", 120, "w"), ("Type", 200, "w"), ("Amount", 160, "e")])
        frame.pack(fill="both", expand=True)

    def refresh(self):
        member_id = self.app.member["member_id"]
        pending = len(member_loans(self.data, member_id, "Pending"))
        self.card_values["Savings Balance"].configure(text=money(savings_balance(self.data, member_id)))
        self.card_values["Loans Owed"].configure(text=money(total_member_loan_balance(self.data, member_id)))
        self.card_values["Pending Applications"].configure(text=str(pending))

        rows = []
        for transaction in reversed(self.data["transactions"]):
            if transaction["member_id"] == member_id:
                rows.append((transaction["date"], transaction["type"], money(transaction["amount"])))
        fill_table(self.table, rows)


class MemberLoansPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "My Loans", "Your loans, and applying for a new one")

        form = ttk.LabelFrame(self, text="Apply for a loan", padding=16)
        form.pack(fill="x")
        ttk.Label(form, text="Loan amount (KES):").pack(side="left")
        self.amount = ttk.Entry(form, width=20)
        self.amount.pack(side="left", padx=(10, 10))
        ttk.Button(form, text="Submit Application (Face Scan)", style="Primary.TButton",
                   command=self.apply).pack(side="left")
        ttk.Label(form, text="Applications are reviewed by a loan officer.",
                  style="Sub.TLabel").pack(side="left", padx=(16, 0))

        ttk.Label(self, text="My loans", style="Big.TLabel").pack(anchor="w", pady=(20, 6))
        frame, self.table = make_table(self, [
            ("Loan ID", 90, "w"), ("Amount", 140, "e"), ("Repaid", 140, "e"),
            ("Balance", 140, "e"), ("Status", 100, "w"), ("Applied", 110, "w")])
        frame.pack(fill="both", expand=True)

    def refresh(self):
        rows = []
        for loan in member_loans(self.data, self.app.member["member_id"]):
            rows.append((loan["loan_id"], money(loan["amount"]), money(loan["amount_repaid"]),
                         money(loan_balance(loan)), loan["status"], loan["date_applied"]))
        fill_table(self.table, rows)

    def apply(self):
        member = self.app.member
        amount = parse_amount(self.amount.get())
        if amount is None:
            return
        if not biometric.is_enrolled(member["member_id"]):
            messagebox.showerror("Face scan required",
                                 "Applying for a loan requires a face scan, but none is on file for you.\n"
                                 "Please ask a teller to enroll your face.")
            return
        # Confirm it is really the member at the screen before submitting
        if not self.app.require_biometric(member, "apply for a loan"):
            return

        loan = submit_loan_application(self.data, member["member_id"], amount)
        self.app.save()
        self.amount.delete(0, "end")
        messagebox.showinfo("Application submitted",
                            "Your loan application " + loan["loan_id"] + " for " + money(amount)
                            + " has been submitted and is waiting for approval.")


# ==========================================================
# SECTION 11: LOGIN SCREEN AND USER ACCOUNTS
# ==========================================================

class LoginScreen(tk.Frame):
    """
    The first thing shown when the program starts.
    - First run (no staff accounts yet): create the administrator account.
    - Staff: sign in with username and password.
    - Member: sign in with Member ID and either their portal password or a face scan.
    """

    def __init__(self, app):
        super().__init__(app, background=SIDEBAR_BG)
        self.app = app
        self.failed_attempts = 0
        self.first_run = len(app.data["users"]) == 0
        self.mode = "Staff"

        # A white card in the middle of a navy background
        card = tk.Frame(self, background=CARD_BG, padx=px(36), pady=px(30))
        card.place(relx=0.5, rely=0.45, anchor="center")
        tk.Frame(card, background=SIDEBAR_HIGHLIGHT, height=px(4)).pack(fill="x", pady=(0, px(18)))

        tk.Label(card, text="SACCO Financial Management", background=CARD_BG, foreground=SIDEBAR_BG,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        if self.first_run:
            subtitle = "First-time setup: create the administrator account"
        else:
            subtitle = "Sign in to continue"
        tk.Label(card, text=subtitle, background=CARD_BG, foreground=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(px(2), px(14)))

        # Staff / Member switch (not needed during first-time setup)
        self.mode_buttons = {}
        if not self.first_run:
            switch = tk.Frame(card, background=CARD_BG, highlightthickness=1,
                              highlightbackground="#c9d3db")
            switch.pack(fill="x", pady=(0, px(16)))
            for mode in ("Staff", "Member"):
                button = tk.Button(switch, text=mode, relief="flat", borderwidth=0,
                                   highlightthickness=0, font=("Segoe UI", 10),
                                   pady=px(5), cursor="hand2",
                                   command=lambda m=mode: self.set_mode(m))
                button.pack(side="left", fill="x", expand=True)
                self.mode_buttons[mode] = button

        self.id_label, self.username = self.add_field(card, "Username")
        self.password_label, self.password = self.add_field(card, "Password", secret=True)
        self.confirm = None
        if self.first_run:
            self.confirm = self.add_field(card, "Confirm password", secret=True)[1]

        self.message = tk.Label(card, text="", background=CARD_BG, foreground=RED,
                                font=("Segoe UI", 9), anchor="w", justify="left",
                                wraplength=px(300))
        self.message.pack(fill="x", pady=(px(4), px(8)))

        self.button = ttk.Button(card, text="Create Account" if self.first_run else "Sign In",
                                 style="Accent.TButton", command=self.submit)
        self.button.pack(fill="x")

        # Face sign-in, available to staff and members (not during first-time setup)
        self.face_area = tk.Frame(card, background=CARD_BG)
        tk.Label(self.face_area, text="or", background=CARD_BG, foreground=MUTED,
                 font=("Segoe UI", 9)).pack(pady=px(6))
        self.face_button = ttk.Button(self.face_area, text="Sign In with Face Scan",
                                      style="Primary.TButton", command=self.face_login)
        self.face_button.pack(fill="x")

        app.bind("<Return>", lambda event: self.submit())
        if not self.first_run:
            self.set_mode("Staff")
        self.username.focus_set()

    def add_field(self, parent, label, secret=False):
        label_widget = tk.Label(parent, text=label, background=CARD_BG, foreground=TEXT,
                                font=("Segoe UI", 10))
        label_widget.pack(anchor="w")
        entry = ttk.Entry(parent, width=34, show="\u2022" if secret else "")
        entry.pack(fill="x", pady=(px(2), px(10)), ipady=px(3))
        return label_widget, entry

    def set_mode(self, mode):
        """Switch the form between staff sign-in and member sign-in."""
        self.mode = mode
        for name, button in self.mode_buttons.items():
            if name == mode:
                button.configure(background=SIDEBAR_BG, foreground="white",
                                 activebackground=SIDEBAR_BG, activeforeground="white")
            else:
                button.configure(background=CARD_BG, foreground=MUTED,
                                 activebackground=STRIPE_BG, activeforeground=TEXT)
        self.id_label.configure(text="Member ID (for example SM001)" if mode == "Member" else "Username")
        self.password_label.configure(text="Portal password" if mode == "Member" else "Password")
        self.username.delete(0, "end")
        self.password.delete(0, "end")
        self.message.configure(text="")
        self.face_area.pack(fill="x")
        self.username.focus_set()

    def locked(self):
        return self.button.instate(["disabled"])

    def submit(self):
        if self.locked():
            return
        username = self.username.get().strip()
        password = self.password.get()

        if username == "":
            self.message.configure(text="Please enter your Member ID." if self.mode == "Member"
                                   else "Please enter a username.")
            return

        if self.first_run:
            problem = password_problem(password, self.confirm.get())
            if problem:
                self.message.configure(text=problem)
                return
            user = make_user(self.app.data, username, password, ADMIN)
            self.app.data["users"].append(user)
            capture_output(save_data, self.app.data)
            self.finish(user)
            return

        if self.mode == "Member":
            member = check_member_login(self.app.data, username, password)
            if member is not None:
                self.finish_member(member)
            else:
                self.failed("Incorrect Member ID or password.")
            return

        user = check_login(self.app.data, username, password)
        if user is not None:
            self.finish(user)
        else:
            self.failed("Incorrect username or password.")

    def face_login(self):
        """
        Sign in by face. The username (staff) or Member ID (member) says
        whose stored face scan to compare against.
        """
        if self.locked():
            return
        identifier = self.username.get().strip()
        if self.mode == "Member":
            if identifier == "":
                self.message.configure(text="Enter your Member ID, then choose Sign In with Face Scan.")
                return
            member = find_member(self.app.data, identifier)
            account, face_id = member, member["member_id"] if member else None
            no_face = ("No face scan is on file for that Member ID. "
                       "Sign in with your password, or ask a teller to enroll your face.")
        else:
            if identifier == "":
                self.message.configure(text="Enter your username, then choose Sign In with Face Scan.")
                return
            user = find_user(self.app.data, identifier)
            account, face_id = user, user["user_id"] if user else None
            no_face = ("No face scan is on file for that username. Sign in with your password, "
                       "then use Set Up Face Sign-In in the sidebar.")

        if account is None or not biometric.is_enrolled(face_id):
            self.failed(no_face)
            return

        self.message.configure(text="")
        messagebox.showinfo("Face sign-in", "A camera window will open. Look at the camera.\n"
                                            "Press 'q' in the camera window to cancel.")
        verified, details = self.app.run_camera(biometric.verify_face, face_id)
        if verified:
            if self.mode == "Member":
                self.finish_member(account)
            else:
                self.finish(account)
        elif details and "FAILED" not in details:
            # A camera or OpenCV problem rather than a face mismatch
            self.message.configure(text=details)
        else:
            self.failed("Face not recognised. Try again, or sign in with your password.")

    def failed(self, text):
        """Count a failed attempt and lock the form after too many in a row."""
        self.failed_attempts += 1
        self.password.delete(0, "end")
        if self.failed_attempts >= MAX_LOGIN_ATTEMPTS:
            # Slow down password guessing: lock the form for 30 seconds
            self.failed_attempts = 0
            self.button.state(["disabled"])
            self.face_button.state(["disabled"])
            self.message.configure(text="Too many failed attempts. Please wait 30 seconds.")
            self.after(30000, self.unlock)
        else:
            self.message.configure(text=text)

    def unlock(self):
        if self.winfo_exists():
            self.button.state(["!disabled"])
            self.face_button.state(["!disabled"])
            self.message.configure(text="")

    def finish(self, user):
        self.app.unbind("<Return>")
        self.app.login(user)

    def finish_member(self, member):
        self.app.unbind("<Return>")
        self.app.login_member(member)


class PasswordDialog(tk.Toplevel):
    """
    Pop-up for passwords. It can also ask for a username and role
    (when adding a user) or the current password (when changing your own).
    result is (first value, new password) or None if cancelled.
    """

    def __init__(self, app, title, ask_current=False, ask_user=False, note=None, cancel_text="Cancel"):
        super().__init__(app)
        self.result = None
        self.ask_current = ask_current
        self.ask_user = ask_user
        self.title(title)
        self.configure(background=PAGE_BG)
        self.resizable(False, False)
        self.transient(app)

        body = ttk.Frame(self, padding=px(20))
        body.pack(fill="both", expand=True)

        first_row = 0
        if note:
            ttk.Label(body, text=note, style="Sub.TLabel", justify="left").grid(
                row=0, column=0, columnspan=2, sticky="w", pady=(0, px(10)))
            first_row = 1

        self.fields = {}
        rows = []
        if ask_user:
            rows.append(("username", "Username:"))
        if ask_current:
            rows.append(("current", "Current password:"))
        rows.extend([("new", "New password:" if not ask_user else "Password:"),
                     ("confirm", "Confirm password:")])

        for row, (key, label) in enumerate(rows, start=first_row):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="w", pady=px(4))
            entry = ttk.Entry(body, width=30, show="" if key == "username" else "•")
            entry.grid(row=row, column=1, pady=px(4), padx=(px(10), 0))
            self.fields[key] = entry

        if ask_user:
            ttk.Label(body, text="Role:").grid(row=first_row + len(rows), column=0, sticky="w", pady=px(4))
            self.role = ttk.Combobox(body, state="readonly", width=28,
                                     values=STAFF_ROLES)
            self.role.set(TELLER)
            self.role.grid(row=first_row + len(rows), column=1, pady=px(4), padx=(px(10), 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=first_row + len(rows) + 1, column=0, columnspan=2, sticky="e", pady=(px(14), 0))
        ttk.Button(buttons, text=cancel_text, command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Save", style="Accent.TButton",
                   command=self.on_save).pack(side="right", padx=(0, px(8)))

        self.bind("<Return>", lambda event: self.on_save())
        self.bind("<Escape>", lambda event: self.destroy())
        list(self.fields.values())[0].focus_set()
        self.wait_visibility()
        self.grab_set()

    def on_save(self):
        if self.ask_user and self.fields["username"].get().strip() == "":
            messagebox.showerror("Missing username", "Please enter a username.", parent=self)
            return
        problem = password_problem(self.fields["new"].get(), self.fields["confirm"].get())
        if problem:
            messagebox.showerror("Password", problem, parent=self)
            return

        if self.ask_user:
            first = (self.fields["username"].get().strip(), self.role.get())
        elif self.ask_current:
            first = self.fields["current"].get()
        else:
            first = None
        self.result = (first, self.fields["new"].get())
        self.destroy()


class RoleDialog(tk.Toplevel):
    """Pop-up to pick a new role for a staff account. result is the role, or None."""

    def __init__(self, app, user):
        super().__init__(app)
        self.result = None
        self.title("Change Role - " + user["username"])
        self.configure(background=PAGE_BG)
        self.resizable(False, False)
        self.transient(app)

        body = ttk.Frame(self, padding=px(20))
        body.pack(fill="both", expand=True)
        self.choice = tk.StringVar(value=user["role"])
        for role in STAFF_ROLES:
            ttk.Radiobutton(body, text=role, value=role, variable=self.choice).pack(anchor="w")
            ttk.Label(body, text=ROLE_DESCRIPTIONS[role], style="Sub.TLabel").pack(
                anchor="w", padx=(px(24), 0), pady=(0, px(8)))

        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(px(8), 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Save", style="Accent.TButton",
                   command=self.on_save).pack(side="right", padx=(0, px(8)))
        self.wait_visibility()
        self.grab_set()

    def on_save(self):
        self.result = self.choice.get()
        self.destroy()


class UsersPage(Page):
    """Administrators only: manage the staff accounts that can sign in."""

    def __init__(self, parent, app):
        super().__init__(parent, app, "Users", "Staff accounts that can sign in to the system")

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, px(10)))
        ttk.Button(toolbar, text="Add User", style="Accent.TButton", command=self.add).pack(side="left")
        ttk.Button(toolbar, text="Change Role", command=self.change_role).pack(side="left", padx=(px(8), 0))
        ttk.Button(toolbar, text="Reset Password", command=self.reset).pack(side="left", padx=(px(8), 0))
        ttk.Button(toolbar, text="Enroll Face", style="Primary.TButton",
                   command=self.enroll).pack(side="left", padx=(px(8), 0))
        ttk.Button(toolbar, text="Delete", style="Danger.TButton", command=self.delete).pack(side="right")

        frame, self.table = make_table(self, [
            ("Username", 160, "w"), ("Role", 130, "w"), ("Access", 360, "w"),
            ("Face Sign-In", 110, "w"), ("Created", 110, "w")])
        frame.pack(fill="both", expand=True)

        ttk.Label(self, text="Staff sign in with their password or a face scan (enroll it here, or "
                             "via Set Up Face Sign-In in the sidebar). Members do not need an account "
                             "here: they use their Member ID with their portal password or face scan.",
                  style="Sub.TLabel", wraplength=px(700), justify="left").pack(anchor="w", pady=(px(8), 0))

    def refresh(self):
        rows = []
        for user in self.data["users"]:
            face = "Enrolled" if biometric.is_enrolled(user["user_id"]) else "Not set"
            rows.append((user["username"], user["role"], ROLE_DESCRIPTIONS.get(user["role"], ""),
                         face, user.get("date_created", "")))
        fill_table(self.table, rows)

    def is_last_admin(self, user):
        admins = [u for u in self.data["users"] if u["role"] == ADMIN]
        return user["role"] == ADMIN and len(admins) <= 1

    def enroll(self):
        """Capture a staff member's face so they can sign in with a face scan."""
        if not self.app.require("manage_users"):
            return
        user = self.selected_user()
        if user is None:
            return
        if biometric.is_enrolled(user["user_id"]):
            if not messagebox.askyesno("Enroll face", user["username"] + " already has a face scan on file.\n"
                                                      "Re-capture and replace it?"):
                return
        self.app.enroll_face(user["user_id"], user["username"])

    def change_role(self):
        if not self.app.require("manage_users"):
            return
        user = self.selected_user()
        if user is None:
            return
        if user is self.app.user:
            messagebox.showerror("Change role", "You cannot change the role of the account you are signed in with.")
            return

        dialog = RoleDialog(self.app, user)
        self.app.wait_window(dialog)
        if dialog.result is None or dialog.result == user["role"]:
            return
        if self.is_last_admin(user):
            messagebox.showerror("Change role", "The last administrator account must stay an administrator.")
            return
        user["role"] = dialog.result
        self.app.save()
        messagebox.showinfo("Change role", "'" + user["username"] + "' is now a " + dialog.result + ".")

    def selected_user(self):
        username = selected_value(self.table)
        if username is None:
            messagebox.showinfo("No user selected", "Please select a user in the table first.")
            return None
        return find_user(self.data, username)

    def add(self):
        if not self.app.require("manage_users"):
            return
        dialog = PasswordDialog(self.app, "Add User", ask_user=True)
        self.app.wait_window(dialog)
        if dialog.result is None:
            return
        (username, role), password = dialog.result
        if find_user(self.data, username) is not None:
            messagebox.showerror("Add user", "A user called '" + username + "' already exists.")
            return
        self.data["users"].append(make_user(self.data, username, password, role))
        self.app.save()
        messagebox.showinfo("Add user", "User '" + username + "' created as " + role + ".")

    def reset(self):
        if not self.app.require("manage_users"):
            return
        user = self.selected_user()
        if user is None:
            return
        dialog = PasswordDialog(self.app, "Reset Password - " + user["username"])
        self.app.wait_window(dialog)
        if dialog.result is None:
            return
        user["salt"], user["password_hash"] = hash_password(dialog.result[1])
        self.app.save()
        messagebox.showinfo("Reset password", "Password for '" + user["username"] + "' has been reset.")

    def delete(self):
        if not self.app.require("manage_users"):
            return
        user = self.selected_user()
        if user is None:
            return
        if user is self.app.user:
            messagebox.showerror("Delete user", "You cannot delete the account you are signed in with.")
            return
        if self.is_last_admin(user):
            messagebox.showerror("Delete user", "The last administrator account cannot be deleted.")
            return
        if messagebox.askyesno("Delete user", "Delete the account '" + user["username"] + "'?", icon="warning"):
            self.data["users"].remove(user)
            self.app.save()


# ==========================================================
# SECTION 12: PROGRAM START
# ==========================================================

def main():
    app = SaccoApp()
    app.mainloop()


# This line makes the program start when the file is run
if __name__ == "__main__":
    main()
