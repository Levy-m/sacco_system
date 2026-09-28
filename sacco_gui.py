# sacco_gui.py
# SACCO Financial Management System - Graphical (GUI) version.
#
# Built with Tkinter, which ships with Python, so the windows themselves
# need nothing extra installed. It shares the same data file
# (sacco_data.json), the same calculations (from sacco.py) and the same
# face verification (biometric.py) as the menu version.
#
# Run this file to start the system.

import tkinter as tk
from tkinter import ttk, messagebox

from storage import load_data, save_data
import biometric

# Reuse the calculation helpers from the menu version so both
# versions always agree on balances, IDs and formatting.
from sacco import (today, money, next_member_id, find_member,
                   record_transaction, savings_balance, next_loan_id,
                   loan_balance, total_member_loan_balance)


# ==========================================================
# SECTION 1: COLOURS, STYLES AND SMALL HELPERS
# ==========================================================

SIDEBAR_BG = "#1f3b4d"
SIDEBAR_ACTIVE = "#2f5a75"
SIDEBAR_FG = "#ffffff"
PAGE_BG = "#f4f6f8"
CARD_BG = "#ffffff"
ACCENT = "#2e7d32"
DANGER = "#c62828"
MUTED = "#5f6b76"

ALL_MEMBERS = "All members"


def setup_styles(root):
    """Give every ttk widget a consistent, clean look on Windows, Mac and Linux."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=PAGE_BG, font=("Segoe UI", 10))
    style.configure("TFrame", background=PAGE_BG)
    style.configure("Card.TFrame", background=CARD_BG, relief="solid", borderwidth=1)
    style.configure("TLabel", background=PAGE_BG)
    style.configure("Card.TLabel", background=CARD_BG)
    style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), background=PAGE_BG)
    style.configure("Sub.TLabel", foreground=MUTED, background=PAGE_BG)
    style.configure("CardTitle.TLabel", foreground=MUTED, background=CARD_BG)
    style.configure("CardValue.TLabel", font=("Segoe UI", 16, "bold"), background=CARD_BG)
    style.configure("Big.TLabel", font=("Segoe UI", 12, "bold"), background=PAGE_BG)

    style.configure("TButton", padding=(10, 5))
    style.configure("Accent.TButton", foreground="white", background=ACCENT)
    style.map("Accent.TButton", background=[("active", "#256628")])
    style.configure("Danger.TButton", foreground="white", background=DANGER)
    style.map("Danger.TButton", background=[("active", "#a31f1f")])

    style.configure("Treeview", rowheight=26, background=CARD_BG, fieldbackground=CARD_BG)
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
    style.configure("TNotebook", background=PAGE_BG)
    style.configure("TNotebook.Tab", padding=(14, 6))
    style.configure("TLabelframe", background=PAGE_BG)
    style.configure("TLabelframe.Label", background=PAGE_BG, font=("Segoe UI", 10, "bold"))


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
        tree.column(column_id, width=width, anchor=anchor, stretch=True)

    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return frame, tree


def fill_table(tree, rows):
    """Replace everything in a table with the given rows."""
    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert("", "end", values=row)


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


def member_name(data, member_id):
    member = find_member(data, member_id)
    return member["full_name"] if member is not None else "Unknown"


def member_loans(data, member_id, status=None):
    """All loans of one member, optionally only those with a given status."""
    loans = []
    for loan in data["loans"]:
        if loan["member_id"] == member_id and (status is None or loan["status"] == status):
            loans.append(loan)
    return loans


# ==========================================================
# SECTION 2: THE MAIN WINDOW
# ==========================================================

class SaccoApp(tk.Tk):
    """The main window: a navigation sidebar on the left, pages on the right."""

    def __init__(self):
        super().__init__()
        self.title("SACCO Financial Management System")
        self.geometry("1180x720")
        self.minsize(980, 620)
        self.configure(background=PAGE_BG)
        setup_styles(self)

        self.data = load_data()

        # --- Sidebar ---
        sidebar = tk.Frame(self, background=SIDEBAR_BG, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="SACCO", background=SIDEBAR_BG, foreground=SIDEBAR_FG,
                 font=("Segoe UI", 20, "bold")).pack(pady=(24, 0))
        tk.Label(sidebar, text="Financial Management", background=SIDEBAR_BG,
                 foreground="#b7c7d3", font=("Segoe UI", 10)).pack(pady=(0, 24))

        # --- Page area ---
        content = ttk.Frame(self, padding=20)
        content.pack(side="left", fill="both", expand=True)
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        self.pages = {}
        self.nav_buttons = {}
        navigation = [
            ("Dashboard", DashboardPage),
            ("Members", MembersPage),
            ("Savings", SavingsPage),
            ("Loans", LoansPage),
            ("Transactions", TransactionsPage),
            ("Reports", ReportsPage),
        ]

        for name, page_class in navigation:
            page = page_class(content, self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page

            button = tk.Button(sidebar, text="   " + name, anchor="w", relief="flat",
                               background=SIDEBAR_BG, foreground=SIDEBAR_FG,
                               activebackground=SIDEBAR_ACTIVE, activeforeground=SIDEBAR_FG,
                               font=("Segoe UI", 11), borderwidth=0, padx=16, pady=10,
                               cursor="hand2", command=lambda n=name: self.show_page(n))
            button.pack(fill="x")
            self.nav_buttons[name] = button

        tk.Button(sidebar, text="   Exit", anchor="w", relief="flat",
                  background=SIDEBAR_BG, foreground="#ffb4b4",
                  activebackground=SIDEBAR_ACTIVE, activeforeground="#ffb4b4",
                  font=("Segoe UI", 11), borderwidth=0, padx=16, pady=10,
                  cursor="hand2", command=self.destroy).pack(side="bottom", fill="x", pady=16)

        self.show_page("Dashboard")

    def show_page(self, name):
        """Bring a page to the front and refresh it with the latest data."""
        for other, button in self.nav_buttons.items():
            button.configure(background=SIDEBAR_ACTIVE if other == name else SIDEBAR_BG)
        page = self.pages[name]
        page.refresh()
        page.tkraise()

    def save(self):
        """Save to disk and refresh every page so they all show the new data."""
        save_data(self.data)
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
        """
        self.config(cursor="watch")
        self.update()
        try:
            return action(member_id)
        finally:
            self.config(cursor="")

    def enroll(self, member):
        """Capture a member's face. Returns True on success."""
        messagebox.showinfo(
            "Biometric enrollment",
            "A camera window will open for " + member["full_name"] + ".\n\n"
            "Look at the camera and move your head slightly while "
            + str(biometric.SAMPLES_PER_MEMBER) + " samples are captured.\n"
            "Press 'q' in the camera window to cancel.")
        success = self.run_camera(biometric.enroll_face, member["member_id"])
        if success:
            messagebox.showinfo("Biometric enrollment",
                                "Biometric enrollment successful for " + member["full_name"] + ".")
        else:
            messagebox.showerror("Biometric enrollment",
                                 "Biometric enrollment failed or was cancelled.\n\n"
                                 "Check that a webcam is connected and that "
                                 "opencv-contrib-python is installed.")
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

        verified = self.run_camera(biometric.verify_face, member["member_id"])
        if not verified:
            messagebox.showerror("Verification failed",
                                 "Biometric verification failed. "
                                 + action_description.capitalize() + " has been cancelled for security.")
        return verified


class Page(ttk.Frame):
    """Base class for every page: a title, subtitle and a refresh() method."""

    def __init__(self, parent, app, title, subtitle):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(self, text=subtitle, style="Sub.TLabel").pack(anchor="w", pady=(0, 14))

    @property
    def data(self):
        return self.app.data

    def refresh(self):
        pass


# ==========================================================
# SECTION 3: DASHBOARD
# ==========================================================

class DashboardPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Dashboard", "An overview of the SACCO today")

        cards = ttk.Frame(self)
        cards.pack(fill="x")
        self.card_values = {}
        for index, name in enumerate(["Members", "Total Savings", "Loans Outstanding", "Pending Loans"]):
            card = ttk.Frame(cards, style="Card.TFrame", padding=16)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 12, 0))
            cards.columnconfigure(index, weight=1)
            ttk.Label(card, text=name, style="CardTitle.TLabel").pack(anchor="w")
            value = ttk.Label(card, text="-", style="CardValue.TLabel")
            value.pack(anchor="w", pady=(6, 0))
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
# SECTION 4: MEMBERS
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

        buttons = ttk.Frame(body)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(14, 0))
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

        self.result = {"full_name": full_name, "phone": phone, "email": email}
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
                  style="Big.TLabel").pack(side="left")
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

        ttk.Button(toolbar, text="Register Member", style="Accent.TButton",
                   command=self.register).pack(side="left")
        ttk.Button(toolbar, text="Edit", command=self.edit).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Enroll Biometric", command=self.enroll).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Statement", command=self.statement).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Delete", style="Danger.TButton",
                   command=self.delete).pack(side="right")

        frame, self.table = make_table(self, [
            ("ID", 80, "w"), ("Full Name", 200, "w"), ("Phone", 130, "w"),
            ("Email", 210, "w"), ("Joined", 100, "w"), ("Savings", 140, "e"),
            ("Biometric", 100, "w")])
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
            rows.append((member["member_id"], member["full_name"], member["phone"], member["email"],
                         member["date_registered"], money(savings_balance(self.data, member["member_id"])),
                         bio_status))
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
        dialog = MemberDialog(self.app)
        self.app.wait_window(dialog)
        if dialog.result is None:
            return

        member = {"member_id": next_member_id(self.data)}
        member.update(dialog.result)
        member["date_registered"] = today()
        self.data["members"].append(member)
        self.app.save()

        if messagebox.askyesno("Member registered",
                               member["full_name"] + " registered as " + member["member_id"] + ".\n\n"
                               "Enroll their biometric (face) now?"):
            self.app.enroll(member)

    def edit(self):
        member = self.selected_member()
        if member is None:
            return
        dialog = MemberDialog(self.app, member)
        self.app.wait_window(dialog)
        if dialog.result is not None:
            member.update(dialog.result)
            self.app.save()
            messagebox.showinfo("Member updated", "Member details updated successfully!")

    def enroll(self):
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
# SECTION 5: SAVINGS
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

        self.balance_label = ttk.Label(form, text="Select a member to see their balance", style="Big.TLabel")
        self.balance_label.grid(row=0, column=2, sticky="w", padx=(30, 0))

        ttk.Label(form, text="Amount (KES):").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.amount = ttk.Entry(form, width=20)
        self.amount.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(12, 0))

        buttons = ttk.Frame(form)
        buttons.grid(row=1, column=2, sticky="w", padx=(30, 0), pady=(12, 0))
        ttk.Button(buttons, text="Deposit", style="Accent.TButton", command=self.deposit).pack(side="left")
        ttk.Button(buttons, text="Withdraw (Biometric)", command=self.withdraw).pack(side="left", padx=(8, 0))

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
# SECTION 6: LOANS
# ==========================================================

class LoansPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Loans", "Apply for, approve and repay loans")

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True)

        self.build_apply_tab(tabs)
        self.build_approve_tab(tabs)
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

        ttk.Button(tab, text="Submit Application (Biometric)", style="Accent.TButton",
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

        loan = {
            "loan_id": next_loan_id(self.data),
            "member_id": member["member_id"],
            "amount": amount,
            "date_applied": today(),
            "status": "Pending",
            "amount_repaid": 0
        }
        self.data["loans"].append(loan)
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
        for box in (self.apply_member, self.repay_member):
            box.configure(values=choices)
            if self.app.member_from_choice(box.get()) is None:
                box.set("")

        self.balance_member.configure(values=[ALL_MEMBERS] + choices)
        if self.app.member_from_choice(self.balance_member.get()) is None:
            self.balance_member.set(ALL_MEMBERS)

        rows = []
        for loan in self.data["loans"]:
            if loan["status"] == "Pending":
                rows.append((loan["loan_id"], loan["member_id"], member_name(self.data, loan["member_id"]),
                             money(loan["amount"]), money(savings_balance(self.data, loan["member_id"])),
                             loan["date_applied"]))
        fill_table(self.pending_table, rows)

        self.show_apply_member()
        self.show_active_loans()
        self.show_all_loans()


# ==========================================================
# SECTION 7: TRANSACTIONS
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
# SECTION 8: REPORTS
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
        ttk.Button(menu, text="Open Statement", command=self.open_statement).pack(fill="x")

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
# SECTION 9: PROGRAM START
# ==========================================================

def main():
    app = SaccoApp()
    app.mainloop()


# This line makes the program start when the file is run
if __name__ == "__main__":
    main()
