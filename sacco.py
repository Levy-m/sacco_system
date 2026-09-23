# sacco.py
# SACCO Financial Management System
# A simple menu driven program that manages members, savings,
# loans, repayments, transactions and reports.

from datetime import date

# We bring in our own storage module, which handles the JSON file
from storage import load_data, save_data

# Biometric (face) enrollment and verification
import biometric


# ==========================================================
# SECTION 1: SMALL HELPER FUNCTIONS
# These are used all over the program.
# ==========================================================

def today():
    """Return today's date as text, for example 2026-09-20."""
    return date.today().strftime("%Y-%m-%d")


def money(amount):
    """Format a number as Kenyan money, for example KES 1,500.00."""
    return "KES {:,.2f}".format(amount)


def print_header(title):
    """Print a title inside a line of equal signs."""
    print()
    print("=" * 55)
    print(title.center(55))
    print("=" * 55)


def pause():
    """Wait for the user to press Enter before showing the menu again."""
    input("\nPress Enter to continue...")


def ask_text(prompt):
    """Ask the user for text and refuse to accept an empty answer."""
    while True:
        value = input(prompt).strip()
        if value != "":
            return value
        print("This field cannot be left blank. Please try again.")


def ask_amount(prompt):
    """Ask the user for an amount of money and make sure it is a valid number."""
    while True:
        value = input(prompt).strip()
        try:
            amount = float(value)
        except ValueError:
            # The user typed something that is not a number, for example "abc"
            print("Please enter a number, for example 1500")
            continue

        if amount <= 0:
            print("The amount must be greater than zero.")
            continue

        return round(amount, 2)


def ask_phone(prompt):
    """Ask for a phone number and do a simple check on it."""
    while True:
        phone = ask_text(prompt)
        digits = phone.replace("+", "").replace(" ", "")
        if digits.isdigit() and len(digits) >= 9:
            return phone
        print("Please enter a valid phone number, for example 0712345678")


def ask_email(prompt):
    """Ask for an email address and do a simple check on it."""
    while True:
        email = ask_text(prompt)
        if "@" in email and "." in email:
            return email
        print("Please enter a valid email address, for example jane@gmail.com")


def confirm(prompt):
    """Ask a yes or no question and return True only if the answer is yes."""
    answer = input(prompt + " (y/n): ").strip().lower()
    return answer == "y" or answer == "yes"


# ==========================================================
# SECTION 1B: BIOMETRIC HELPERS
# ==========================================================

def enroll_biometric_menu(data):
    """Menu action: enroll (or re-enroll) a member's face for biometric checks."""
    print_header("ENROLL MEMBER BIOMETRIC (FACE)")

    member = choose_member(data)
    if member is None:
        return

    if biometric.is_enrolled(member["member_id"]):
        print(member["full_name"] + " already has a biometric on file.")
        if not confirm("Re-capture and replace it?"):
            print("Enrollment cancelled.")
            return

    print("\nMember: " + member["full_name"])
    success = biometric.enroll_face(member["member_id"])

    if success:
        print("\nBiometric enrollment successful for " + member["full_name"] + ".")
    else:
        print("\nBiometric enrollment failed. Please try again.")


def require_biometric(member, action_description):
    """
    Gate a sensitive action behind face verification.
    Returns True if the member is verified and the action should proceed.
    """
    if not biometric.is_enrolled(member["member_id"]):
        print("\n" + member["full_name"] + " has not enrolled a biometric yet.")
        print("Biometric verification is required to " + action_description + ".")
        if confirm("Enroll their biometric now?"):
            if not biometric.enroll_face(member["member_id"]):
                print("Enrollment failed. Cannot proceed with " + action_description + ".")
                return False
        else:
            print("Cannot proceed without a biometric on file.")
            return False

    print("\nBiometric verification is required to " + action_description + ".")
    if not confirm("Ready to scan your face?"):
        print("Verification cancelled. Action aborted.")
        return False

    verified = biometric.verify_face(member["member_id"])
    if not verified:
        print("\nBiometric verification failed. " + action_description.capitalize() + " has been cancelled for security.")
        return False

    return True


# ==========================================================
# SECTION 2: MEMBER MANAGEMENT
# ==========================================================

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


def choose_member(data):
    """Ask the user for a member ID and return that member."""
    if len(data["members"]) == 0:
        print("There are no members registered yet. Please register one first.")
        return None

    member_id = ask_text("Enter Member ID (for example SM001): ")
    member = find_member(data, member_id)

    if member is None:
        print("No member was found with the ID '" + member_id + "'.")
        return None

    return member


def register_member(data):
    """Register a new SACCO member."""
    print_header("REGISTER NEW MEMBER")

    member_id = next_member_id(data)
    print("The system has assigned the Member ID: " + member_id)

    full_name = ask_text("Enter Full Name: ")
    phone = ask_phone("Enter Phone Number: ")
    email = ask_email("Enter Email Address: ")

    # A member is stored as a dictionary inside the members list
    member = {
        "member_id": member_id,
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "date_registered": today()
    }

    data["members"].append(member)
    save_data(data)

    print("\nMember registered successfully!")
    print("Member ID   : " + member["member_id"])
    print("Full Name   : " + member["full_name"])
    print("Registered  : " + member["date_registered"])

    if confirm("\nEnroll their biometric (face) now?"):
        biometric.enroll_face(member["member_id"])


def view_members(data):
    """Display all registered members in a table."""
    print_header("REGISTERED SACCO MEMBERS")

    if len(data["members"]) == 0:
        print("There are no members registered yet.")
        return

    print("{:<8} {:<22} {:<14} {:<12} {:<10}".format(
        "ID", "FULL NAME", "PHONE", "JOINED", "BIOMETRIC"))
    print("-" * 68)

    for member in data["members"]:
        bio_status = "Enrolled" if biometric.is_enrolled(member["member_id"]) else "Not set"
        print("{:<8} {:<22} {:<14} {:<12} {:<10}".format(
            member["member_id"],
            member["full_name"],
            member["phone"],
            member["date_registered"],
            bio_status
        ))

    print("-" * 68)
    print("Total members: " + str(len(data["members"])))


def search_member(data):
    """Search for a member by ID or by part of their name."""
    print_header("SEARCH FOR A MEMBER")

    if len(data["members"]) == 0:
        print("There are no members registered yet.")
        return

    term = ask_text("Enter a Member ID or part of a name: ").lower()
    matches = []

    for member in data["members"]:
        if term in member["member_id"].lower() or term in member["full_name"].lower():
            matches.append(member)

    if len(matches) == 0:
        print("\nNo member matched your search.")
        return

    print("\nFound " + str(len(matches)) + " matching member(s):\n")
    for member in matches:
        print("Member ID : " + member["member_id"])
        print("Full Name : " + member["full_name"])
        print("Phone     : " + member["phone"])
        print("Email     : " + member["email"])
        print("Savings   : " + money(savings_balance(data, member["member_id"])))
        print("-" * 40)


def update_member(data):
    """Update the details of an existing member."""
    print_header("UPDATE MEMBER INFORMATION")

    member = choose_member(data)
    if member is None:
        return

    print("\nPress Enter to keep the value shown in brackets.\n")

    new_name = input("Full Name [" + member["full_name"] + "]: ").strip()
    if new_name != "":
        member["full_name"] = new_name

    new_phone = input("Phone Number [" + member["phone"] + "]: ").strip()
    if new_phone != "":
        member["phone"] = new_phone

    new_email = input("Email Address [" + member["email"] + "]: ").strip()
    if new_email != "":
        member["email"] = new_email

    save_data(data)
    print("\nMember details updated successfully!")


def delete_member(data):
    """Remove a member and their records from the system."""
    print_header("DELETE A MEMBER")

    member = choose_member(data)
    if member is None:
        return

    # A member who still owes the SACCO money may not be deleted
    owed = total_member_loan_balance(data, member["member_id"])
    if owed > 0:
        print("\nThis member cannot be deleted.")
        print("They still have an outstanding loan of " + money(owed) + ".")
        return

    print("\nYou are about to delete " + member["full_name"] + " (" + member["member_id"] + ").")
    if not confirm("Are you sure?"):
        print("Deletion cancelled. No changes were made.")
        return

    data["members"].remove(member)

    # Remove the transactions that belong to this member
    remaining_transactions = []
    for transaction in data["transactions"]:
        if transaction["member_id"] != member["member_id"]:
            remaining_transactions.append(transaction)
    data["transactions"] = remaining_transactions

    # Remove the loans that belong to this member
    remaining_loans = []
    for loan in data["loans"]:
        if loan["member_id"] != member["member_id"]:
            remaining_loans.append(loan)
    data["loans"] = remaining_loans

    save_data(data)
    print("\nMember deleted successfully.")


# ==========================================================
# SECTION 3: SAVINGS AND TRANSACTIONS
# ==========================================================

def record_transaction(data, member_id, transaction_type, amount):
    """Save one transaction into the transactions list."""
    transaction = {
        "member_id": member_id,
        "type": transaction_type,
        "amount": amount,
        "date": today()
    }
    data["transactions"].append(transaction)


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


def deposit_savings(data):
    """Record money paid in by a member."""
    print_header("DEPOSIT SAVINGS")

    member = choose_member(data)
    if member is None:
        return

    print("Member: " + member["full_name"])
    print("Current savings: " + money(savings_balance(data, member["member_id"])))

    amount = ask_amount("Enter amount to deposit: ")
    record_transaction(data, member["member_id"], "Deposit", amount)
    save_data(data)

    print("\nDeposit of " + money(amount) + " recorded successfully!")
    print("New savings balance: " + money(savings_balance(data, member["member_id"])))


def withdraw_savings(data):
    """Record money taken out by a member. Requires biometric verification."""
    print_header("WITHDRAW SAVINGS")

    member = choose_member(data)
    if member is None:
        return

    balance = savings_balance(data, member["member_id"])
    print("Member: " + member["full_name"])
    print("Available savings: " + money(balance))

    if balance <= 0:
        print("\nThis member has no savings to withdraw.")
        return

    # --- Biometric gate ---
    if not require_biometric(member, "withdraw savings"):
        return

    amount = ask_amount("Enter amount to withdraw: ")

    if amount > balance:
        print("\nWithdrawal failed. The amount is more than the available savings.")
        return

    record_transaction(data, member["member_id"], "Withdrawal", amount)
    save_data(data)

    print("\nWithdrawal of " + money(amount) + " recorded successfully!")
    print("New savings balance: " + money(savings_balance(data, member["member_id"])))


def check_savings_balance(data):
    """Show one member's savings balance and their transaction history."""
    print_header("SAVINGS BALANCE")

    member = choose_member(data)
    if member is None:
        return

    print("\nMember ID : " + member["member_id"])
    print("Full Name : " + member["full_name"])
    print("Savings   : " + money(savings_balance(data, member["member_id"])))

    print("\nSavings transaction history:")
    show_transactions(data, member["member_id"])


def show_transactions(data, member_id=None):
    """Print transactions. If a member ID is given, only show that member's own."""
    rows = []
    for transaction in data["transactions"]:
        if member_id is None or transaction["member_id"] == member_id:
            rows.append(transaction)

    if len(rows) == 0:
        print("No transactions have been recorded.")
        return

    print("{:<12} {:<8} {:<16} {:>14}".format("DATE", "MEMBER", "TYPE", "AMOUNT"))
    print("-" * 52)

    for transaction in rows:
        print("{:<12} {:<8} {:<16} {:>14}".format(
            transaction["date"],
            transaction["member_id"],
            transaction["type"],
            money(transaction["amount"])
        ))

    print("-" * 52)
    print("Total transactions: " + str(len(rows)))


def view_transactions(data):
    """Menu option that shows all transactions in the SACCO."""
    print_header("ALL TRANSACTIONS")
    show_transactions(data)


# ==========================================================
# SECTION 4: LOAN MANAGEMENT
# ==========================================================

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


def apply_for_loan(data):
    """Record a new loan application. Requires biometric verification."""
    print_header("APPLY FOR A LOAN")

    member = choose_member(data)
    if member is None:
        return

    print("Member: " + member["full_name"])
    print("Savings: " + money(savings_balance(data, member["member_id"])))

    # --- Biometric gate ---
    if not require_biometric(member, "apply for a loan"):
        return

    amount = ask_amount("Enter loan amount applied for: ")

    loan = {
        "loan_id": next_loan_id(data),
        "member_id": member["member_id"],
        "amount": amount,
        "date_applied": today(),
        "status": "Pending",
        "amount_repaid": 0
    }

    data["loans"].append(loan)
    save_data(data)

    print("\nLoan application submitted successfully!")
    print("Loan ID : " + loan["loan_id"])
    print("Amount  : " + money(loan["amount"]))
    print("Status  : " + loan["status"])


def approve_loan(data):
    """Approve or reject a loan that is still pending."""
    print_header("APPROVE OR REJECT A LOAN")

    pending = []
    for loan in data["loans"]:
        if loan["status"] == "Pending":
            pending.append(loan)

    if len(pending) == 0:
        print("There are no loan applications waiting for a decision.")
        return

    print("{:<8} {:<8} {:<20} {:>14} {:<12}".format(
        "LOAN ID", "MEMBER", "NAME", "AMOUNT", "APPLIED"))
    print("-" * 66)

    for loan in pending:
        member = find_member(data, loan["member_id"])
        name = member["full_name"] if member is not None else "Unknown"
        print("{:<8} {:<8} {:<20} {:>14} {:<12}".format(
            loan["loan_id"], loan["member_id"], name,
            money(loan["amount"]), loan["date_applied"]))

    print("-" * 66)

    loan_id = ask_text("\nEnter the Loan ID to process: ")
    chosen = None
    for loan in pending:
        if loan["loan_id"].lower() == loan_id.lower():
            chosen = loan

    if chosen is None:
        print("No pending loan was found with that ID.")
        return

    print("\n1. Approve this loan")
    print("2. Reject this loan")
    decision = input("Enter your choice: ").strip()

    if decision == "1":
        chosen["status"] = "Approved"
        chosen["date_decided"] = today()
        save_data(data)
        print("\nLoan " + chosen["loan_id"] + " has been APPROVED.")
        print("Amount issued: " + money(chosen["amount"]))
    elif decision == "2":
        chosen["status"] = "Rejected"
        chosen["date_decided"] = today()
        save_data(data)
        print("\nLoan " + chosen["loan_id"] + " has been REJECTED.")
    else:
        print("\nInvalid choice. No decision was recorded.")


def repay_loan(data):
    """Record a repayment against an approved loan."""
    print_header("MAKE A LOAN REPAYMENT")

    member = choose_member(data)
    if member is None:
        return

    # Find the loans that this member is still paying
    active = []
    for loan in data["loans"]:
        if loan["member_id"] == member["member_id"] and loan["status"] == "Approved":
            active.append(loan)

    if len(active) == 0:
        print("\n" + member["full_name"] + " has no approved loan to repay.")
        return

    print("\nActive loans for " + member["full_name"] + ":")
    print("{:<8} {:>14} {:>14} {:>14}".format("LOAN ID", "AMOUNT", "REPAID", "BALANCE"))
    print("-" * 54)
    for loan in active:
        print("{:<8} {:>14} {:>14} {:>14}".format(
            loan["loan_id"], money(loan["amount"]),
            money(loan["amount_repaid"]), money(loan_balance(loan))))
    print("-" * 54)

    loan_id = ask_text("\nEnter the Loan ID being repaid: ")
    chosen = None
    for loan in active:
        if loan["loan_id"].lower() == loan_id.lower():
            chosen = loan

    if chosen is None:
        print("No active loan was found with that ID.")
        return

    amount = ask_amount("Enter repayment amount: ")

    if amount > loan_balance(chosen):
        print("\nRepayment failed. That is more than the outstanding balance of "
              + money(loan_balance(chosen)) + ".")
        return

    chosen["amount_repaid"] = round(chosen["amount_repaid"] + amount, 2)
    record_transaction(data, member["member_id"], "Loan Repayment", amount)

    # If the loan is now fully paid we mark it as cleared
    if loan_balance(chosen) == 0:
        chosen["status"] = "Repaid"
        chosen["date_cleared"] = today()

    save_data(data)

    print("\nRepayment of " + money(amount) + " recorded successfully!")
    print("Remaining balance on " + chosen["loan_id"] + ": " + money(loan_balance(chosen)))
    if chosen["status"] == "Repaid":
        print("This loan has been fully repaid. Thank you!")


def view_loan_balance(data):
    """Show all the loans belonging to one member."""
    print_header("LOAN BALANCE")

    member = choose_member(data)
    if member is None:
        return

    loans = []
    for loan in data["loans"]:
        if loan["member_id"] == member["member_id"]:
            loans.append(loan)

    if len(loans) == 0:
        print("\n" + member["full_name"] + " has never applied for a loan.")
        return

    print("\nLoans for " + member["full_name"] + " (" + member["member_id"] + "):\n")
    print("{:<8} {:>14} {:>14} {:>14} {:<10}".format(
        "LOAN ID", "AMOUNT", "REPAID", "BALANCE", "STATUS"))
    print("-" * 64)

    for loan in loans:
        print("{:<8} {:>14} {:>14} {:>14} {:<10}".format(
            loan["loan_id"], money(loan["amount"]),
            money(loan["amount_repaid"]), money(loan_balance(loan)), loan["status"]))

    print("-" * 64)
    print("Total still outstanding: "
          + money(total_member_loan_balance(data, member["member_id"])))


# ==========================================================
# SECTION 5: REPORTS
# ==========================================================

def report_total_savings(data):
    """Report on the total savings held by the whole SACCO."""
    print_header("TOTAL SACCO SAVINGS")

    if len(data["members"]) == 0:
        print("There are no members registered yet.")
        return

    total = 0
    print("{:<8} {:<24} {:>16}".format("ID", "MEMBER", "SAVINGS"))
    print("-" * 50)

    for member in data["members"]:
        balance = savings_balance(data, member["member_id"])
        total = total + balance
        print("{:<8} {:<24} {:>16}".format(
            member["member_id"], member["full_name"], money(balance)))

    print("-" * 50)
    print("{:<33} {:>16}".format("TOTAL SACCO SAVINGS", money(round(total, 2))))


def report_loans_issued(data):
    """Report on every loan the SACCO has actually issued."""
    print_header("TOTAL LOANS ISSUED")

    issued = []
    for loan in data["loans"]:
        if loan["status"] == "Approved" or loan["status"] == "Repaid":
            issued.append(loan)

    if len(issued) == 0:
        print("The SACCO has not issued any loans yet.")
        return

    total = 0
    print("{:<8} {:<8} {:<20} {:>14} {:<10}".format(
        "LOAN ID", "MEMBER", "NAME", "AMOUNT", "STATUS"))
    print("-" * 64)

    for loan in issued:
        member = find_member(data, loan["member_id"])
        name = member["full_name"] if member is not None else "Unknown"
        total = total + loan["amount"]
        print("{:<8} {:<8} {:<20} {:>14} {:<10}".format(
            loan["loan_id"], loan["member_id"], name,
            money(loan["amount"]), loan["status"]))

    print("-" * 64)
    print("Loans issued: " + str(len(issued)))
    print("Total value : " + money(round(total, 2)))


def report_outstanding_loans(data):
    """Report on the money members still owe the SACCO."""
    print_header("OUTSTANDING LOANS")

    outstanding = []
    for loan in data["loans"]:
        if loan["status"] == "Approved" and loan_balance(loan) > 0:
            outstanding.append(loan)

    if len(outstanding) == 0:
        print("There are no outstanding loans. All issued loans are fully repaid.")
        return

    total = 0
    print("{:<8} {:<20} {:>14} {:>14} {:>14}".format(
        "LOAN ID", "NAME", "AMOUNT", "REPAID", "BALANCE"))
    print("-" * 74)

    for loan in outstanding:
        member = find_member(data, loan["member_id"])
        name = member["full_name"] if member is not None else "Unknown"
        total = total + loan_balance(loan)
        print("{:<8} {:<20} {:>14} {:>14} {:>14}".format(
            loan["loan_id"], name, money(loan["amount"]),
            money(loan["amount_repaid"]), money(loan_balance(loan))))

    print("-" * 74)
    print("Total outstanding: " + money(round(total, 2)))


def report_repayments(data):
    """Report on every loan repayment that has been received."""
    print_header("LOAN REPAYMENT REPORT")

    repayments = []
    for transaction in data["transactions"]:
        if transaction["type"] == "Loan Repayment":
            repayments.append(transaction)

    if len(repayments) == 0:
        print("No loan repayments have been received yet.")
        return

    total = 0
    print("{:<12} {:<8} {:<20} {:>14}".format("DATE", "MEMBER", "NAME", "AMOUNT"))
    print("-" * 58)

    for transaction in repayments:
        member = find_member(data, transaction["member_id"])
        name = member["full_name"] if member is not None else "Unknown"
        total = total + transaction["amount"]
        print("{:<12} {:<8} {:<20} {:>14}".format(
            transaction["date"], transaction["member_id"],
            name, money(transaction["amount"])))

    print("-" * 58)
    print("Total repaid: " + money(round(total, 2)))


def report_member_statement(data):
    """Print a full financial statement for one member."""
    print_header("MEMBER FINANCIAL STATEMENT")

    member = choose_member(data)
    if member is None:
        return

    print("\nMember ID    : " + member["member_id"])
    print("Full Name    : " + member["full_name"])
    print("Phone Number : " + member["phone"])
    print("Email        : " + member["email"])
    print("Registered   : " + member["date_registered"])

    print("\n--- SAVINGS ---")
    print("Savings balance: " + money(savings_balance(data, member["member_id"])))

    print("\n--- TRANSACTIONS ---")
    show_transactions(data, member["member_id"])

    print("\n--- LOANS ---")
    loans = []
    for loan in data["loans"]:
        if loan["member_id"] == member["member_id"]:
            loans.append(loan)

    if len(loans) == 0:
        print("This member has never applied for a loan.")
    else:
        print("{:<8} {:>14} {:>14} {:>14} {:<10}".format(
            "LOAN ID", "AMOUNT", "REPAID", "BALANCE", "STATUS"))
        print("-" * 64)
        for loan in loans:
            print("{:<8} {:>14} {:>14} {:>14} {:<10}".format(
                loan["loan_id"], money(loan["amount"]),
                money(loan["amount_repaid"]), money(loan_balance(loan)), loan["status"]))
        print("-" * 64)

    print("\n--- SUMMARY ---")
    print("Total savings      : " + money(savings_balance(data, member["member_id"])))
    print("Total loans owed   : " + money(total_member_loan_balance(data, member["member_id"])))


def reports_menu(data):
    """A smaller menu holding all the reports."""
    while True:
        print_header("REPORTS MENU")
        print("1. List of SACCO Members")
        print("2. Individual Member Financial Statement")
        print("3. Total SACCO Savings")
        print("4. Total Loans Issued")
        print("5. Outstanding Loans")
        print("6. Loan Repayment Report")
        print("7. Transaction Report")
        print("8. Back to Main Menu")
        print("=" * 55)

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            view_members(data)
        elif choice == "2":
            report_member_statement(data)
        elif choice == "3":
            report_total_savings(data)
        elif choice == "4":
            report_loans_issued(data)
        elif choice == "5":
            report_outstanding_loans(data)
        elif choice == "6":
            report_repayments(data)
        elif choice == "7":
            view_transactions(data)
        elif choice == "8":
            return
        else:
            print("\nInvalid choice. Please enter a number between 1 and 8.")

        pause()


# ==========================================================
# SECTION 6: MAIN MENU AND PROGRAM START
# ==========================================================

def show_main_menu():
    """Display the main menu of the system."""
    print()
    print("=" * 55)
    print("        SACCO FINANCIAL MANAGEMENT SYSTEM")
    print("=" * 55)
    print(" 1. Register Member")
    print(" 2. View Members")
    print(" 3. Search Member")
    print(" 4. Deposit Savings")
    print(" 5. Withdraw Savings (Biometric Required)")
    print(" 6. Check Savings Balance")
    print(" 7. Apply for Loan (Biometric Required)")
    print(" 8. Approve Loan")
    print(" 9. Make Loan Repayment")
    print("10. View Loan Balance")
    print("11. View Transactions")
    print("12. Generate Reports")
    print("13. Enroll Member Biometric (Face)")
    print("14. Exit")
    print("=" * 55)


def main():
    """The main program. It keeps showing the menu until the user exits."""

    # Load whatever was saved the last time the program was used
    data = load_data()

    print("\nWelcome to the SACCO Financial Management System")
    print("Members loaded: " + str(len(data["members"])))

    while True:
        show_main_menu()
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            register_member(data)
        elif choice == "2":
            view_members(data)
        elif choice == "3":
            search_member(data)
        elif choice == "4":
            deposit_savings(data)
        elif choice == "5":
            withdraw_savings(data)
        elif choice == "6":
            check_savings_balance(data)
        elif choice == "7":
            apply_for_loan(data)
        elif choice == "8":
            approve_loan(data)
        elif choice == "9":
            repay_loan(data)
        elif choice == "10":
            view_loan_balance(data)
        elif choice == "11":
            view_transactions(data)
        elif choice == "12":
            reports_menu(data)
            continue
        elif choice == "13":
            enroll_biometric_menu(data)
        elif choice == "14":
            print("\nThank you for using the SACCO Financial System. Goodbye!")
            break
        else:
            print("\nInvalid choice. Please enter a number between 1 and 14.")

        pause()


# This line makes the program start when the file is run
if __name__ == "__main__":
    main()