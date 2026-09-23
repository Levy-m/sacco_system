# SACCO FINANCIAL MANAGEMENT SYSTEM

**Name:** _______________________________
**Registration Number:** _______________________________
**Course / Unit:** Python Programming
**Date:** 21 September 2026

---

## 1. Project Title

**Development of a SACCO Financial Management System Using Python**

A menu driven desktop application that manages SACCO members, their savings,
their loans, their repayments and the reports the SACCO needs in order to know
its financial position at any time.

---

## 2. Introduction

A SACCO (Savings and Credit Cooperative Organisation) is a member owned
financial cooperative. Members pool their money together through regular
savings, and the pooled fund is then lent back to members as affordable loans.
Unlike a commercial bank, a SACCO is owned and controlled by the very people who
save in it, and any surplus it makes is returned to those members. SACCOs are a
very important part of financial life in Kenya, especially for employees,
farmers, traders and small business owners who may not easily access bank
credit.

A SACCO financial management system is software that records and tracks these
activities. Its purpose is to keep an accurate record of who the members are,
how much each member has saved, which members have borrowed, how much they still
owe, and what money has moved in and out of the organisation.

Computerising this work is useful for several reasons:

- **Accuracy.** Balances are calculated by the program rather than by hand, so
  arithmetic mistakes are removed.
- **Speed.** A member's balance or statement can be produced in seconds instead
  of searching through files.
- **Safety of records.** Data is stored in a file that stays on disk, so records
  are not lost when a book is misplaced or damaged.
- **Accountability.** Every deposit, withdrawal and repayment is recorded with a
  date, which makes it much harder for money to go missing unnoticed.
- **Better decisions.** Management can see total savings, total loans issued and
  outstanding loans immediately, and can therefore decide how much the SACCO can
  safely lend.

---

## 3. Problem Statement

Many small SACCOs still keep their financial records manually, in exercise books,
ledgers and loose receipts. This creates a number of serious problems.

Manual records are slow to search. To answer a simple question such as "how much
has this member saved?", a clerk must page through a ledger and add up entries by
hand, which takes time and may produce a different answer each time it is done.

Manual records are error prone. Figures are copied from one book to another,
handwriting is misread, and additions are done mentally or on a calculator
without any check. A single wrong entry can go unnoticed for months.

Manual records are easy to lose or damage. A book can be lost, burnt, soaked or
eaten by insects, and when it goes, the record of members' money goes with it.
There is usually no backup.

Manual records make fraud harder to detect. Because there is no automatic trail
linking a payment to a date and a member, money can be received and not recorded,
or a loan balance can be quietly altered.

Manual records make reporting painful. Producing the total savings of the SACCO
or a list of everyone with an outstanding loan means adding up hundreds of lines
by hand, so such reports are produced rarely, or not at all, and management is
left making decisions without accurate information.

The SACCO Financial Management System described in this report addresses these
problems by storing all records in one place, calculating all balances
automatically, and producing reports on demand.

---

## 4. Project Objectives

### General Objective

To design and develop a Python based SACCO Financial Management System that
records and manages members, savings, loans, repayments and transactions, and
that generates accurate financial reports.

### Specific Objectives

1. To develop a module that registers SACCO members and allows their records to
   be viewed, searched, updated and removed.
2. To develop a savings module that records deposits and withdrawals and
   calculates each member's savings balance automatically from their transaction
   history.
3. To develop a loan module that handles loan applications, approval or
   rejection, repayments, and the calculation of the outstanding loan balance.
4. To develop a reporting module that produces the member list, individual
   member statements, total SACCO savings, total loans issued, outstanding loans,
   loan repayments and a full transaction report.
5. To store all system data permanently in a file so that records remain
   available after the program is closed, and to validate all user input so that
   the system does not crash when incorrect data is entered.

---

## 5. System Features

The system presents a numbered main menu with thirteen options. The major
features implemented are as follows.

**Member registration.** New members are registered by capturing their full
name, phone number and email address. The Member ID and the date of registration
are generated by the system itself, so two members can never be given the same
ID.

**Member management.** The system can display all registered members in a table,
search for a member by ID or by part of their name, update a member's details,
and delete a member. A member who still owes the SACCO money cannot be deleted.

**Savings management.** Deposits and withdrawals are recorded against a member.
A withdrawal larger than the member's available savings is refused. The savings
balance and the full savings transaction history can be displayed for any
member.

**Loan management.** A member may apply for a loan, which is recorded with the
amount and the application date and given the status *Pending*. A pending loan
can then be approved or rejected. Repayments are recorded against approved
loans, the outstanding balance is recalculated after every repayment, and a loan
whose balance reaches zero is automatically marked as *Repaid*.

**Financial transactions.** Every deposit, withdrawal and loan repayment is
saved as a transaction record carrying the member ID, the type, the amount and
the date. These records form the audit trail of the system.

**Reports.** A separate reports menu produces the list of SACCO members, an
individual member financial statement, total SACCO savings, total loans issued,
outstanding loans, a loan repayment report and a full transaction report.

**User interface and validation.** Every screen has a clear heading, and every
action ends with a message saying whether it succeeded or failed. If the user
types text where a number is expected, enters a negative amount, leaves a field
blank, gives an invalid phone number or email, or enters a Member ID that does
not exist, the system displays a helpful message and asks again instead of
crashing.

**Data storage.** All records are stored in a JSON file named
`sacco_data.json`, which is written after every change and read back when the
program starts.

---

## 6. Technologies Used

| Technology | Purpose |
|---|---|
| Python 3 | The programming language used to build the whole system |
| `json` module | Saving and loading the system data in JSON format |
| `os` module | Checking whether the data file already exists |
| `datetime` module | Stamping every registration, loan and transaction with the date |
| Visual Studio Code | The code editor used to write and run the program |
| Windows / Linux terminal | Where the program runs and the user interacts with the menu |

No external libraries were installed. The system uses only the Python standard
library, which means it will run on any computer that has Python 3 installed.

---

## 7. System Implementation

The system is written in two Python files. `sacco.py` contains the menu and all
the operations, and `storage.py` contains the two functions that save and load
the data. Splitting the code this way is an example of modular programming: the
part that deals with the file is separate from the part that deals with the
SACCO's business rules.

All the data is held in one dictionary called `data`, which contains three
lists: `members`, `transactions` and `loans`. Each member, each transaction and
each loan is itself a dictionary. This dictionary is passed to every function
that needs it, and is written back to disk after any change.

**Member registration** is handled by `register_member()`. The function works
out the next Member ID by looking at the highest existing ID and adding one, then
collects the name, phone number and email through validated prompts, builds a
member dictionary, appends it to the members list and saves the file.

**Savings management** is handled by `deposit_savings()` and
`withdraw_savings()`. Rather than storing a balance figure, the system
recalculates it whenever it is needed using `savings_balance()`, which loops
through the transactions of that member, adding deposits and subtracting
withdrawals. This design means the displayed balance can never disagree with the
transaction history. A withdrawal is checked against the available balance
before it is accepted.

**Loan management** is handled by `apply_for_loan()`, `approve_loan()` and
`repay_loan()`. A loan dictionary stores the loan ID, the member ID, the amount,
the application date, the status and the amount repaid so far. The outstanding
balance is calculated as the loan amount minus the amount repaid. The approval
screen lists only loans whose status is *Pending*, and the repayment screen lists
only loans whose status is *Approved*, so the user is never offered a loan that
cannot be acted on. A repayment larger than the outstanding balance is rejected.

**Transactions** are written by a single helper function,
`record_transaction()`, which is called by the deposit, withdrawal and repayment
operations. Because every movement of money goes through this one function, no
transaction can be recorded in an inconsistent format.

**Reports** are produced by a set of functions grouped under their own menu.
Each report loops through the relevant list, prints the rows in a formatted
table and prints a total at the bottom. Where a report has nothing to show, it
prints a clear message such as "The SACCO has not issued any loans yet" rather
than an empty table.

**Data storage** is handled by `storage.py`. `save_data()` writes the whole data
dictionary to `sacco_data.json` using `json.dump()`, and `load_data()` reads it
back with `json.load()`. If the file does not exist yet, the program starts with
an empty structure; if the file exists but is damaged, the error is caught and
the user is warned instead of the program crashing.

---

## 8. Sample Code

### Code Snippet 1: Member Registration

```python
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
```

**Explanation:**

This function registers a new SACCO member. It first calls `next_member_id()`,
which generates the next ID in the sequence (SM001, SM002 and so on) so that no
two members can share an ID. It then collects the member's details using the
validation helpers `ask_text()`, `ask_phone()` and `ask_email()`, each of which
keeps asking until a sensible value is entered. The details are packed into a
dictionary together with today's date, the dictionary is appended to the
`members` list, and `save_data()` writes everything to the JSON file so the new
member is still there the next time the program is opened. Finally a confirmation
message is displayed.

---

### Code Snippet 2: Calculating a Member's Savings Balance

```python
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
```

**Explanation:**

This function works out how much a member currently has in savings. Instead of
storing a balance figure somewhere and trying to keep it up to date, the system
recalculates the balance from the transaction history every time it is needed.
The `for` loop goes through every transaction in the system, the first `if`
picks out only the transactions belonging to the member we are interested in,
and the inner `if` adds deposits to the balance and subtracts withdrawals from
it. Loan repayments are deliberately ignored here, because repaying a loan is
not the same as saving money. The result is rounded to two decimal places
because we are dealing with money. The advantage of this approach is that the
balance shown on screen can never disagree with the transaction history.

---

### Code Snippet 3: Validating an Amount Entered by the User

```python
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
```

**Explanation:**

This small function is the reason the system does not crash when the wrong thing
is typed into a money prompt. `float("abc")` would normally raise a `ValueError`
and stop the program, so the conversion is placed inside a `try` block and the
error is caught in the `except` block. When that happens the user is told what a
valid entry looks like and the `while True` loop asks again. A second check
rejects zero and negative amounts, since a deposit or repayment of zero shillings
is meaningless. The function only returns once a sensible positive number has
been entered, so every other part of the program can trust the amounts it
receives. This one function is reused by the deposit, withdrawal, loan
application and loan repayment screens.

---

## 9. Conclusion

The SACCO Financial Management System meets the objectives that were set for it.
It registers and manages members, records savings and withdrawals, handles loans
from application through approval to full repayment, keeps a dated record of
every transaction, and produces the seven reports a SACCO needs to understand its
financial position. All data is stored permanently in a JSON file, and all user
input is validated so that the system responds with a clear message rather than
crashing when incorrect data is entered.

Possible future improvements include moving the data from a JSON file to an
SQLite database, adding interest calculation on both savings and loans, adding
user accounts so that only authorised staff can approve loans, and exporting the
reports to PDF.
