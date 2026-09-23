# storage.py
# This module is responsible for saving and loading the SACCO data.
# All the information is kept in one JSON file called sacco_data.json.

import json
import os

# The name of the file where all SACCO data is stored
DATA_FILE = "sacco_data.json"


def empty_data():
    """Return a fresh, empty data structure for a brand new SACCO."""
    return {
        "members": [],
        "transactions": [],
        "loans": []
    }


def load_data():
    """Read the saved data from the JSON file and return it as a dictionary."""

    # If the file does not exist yet, the system is running for the first time
    if not os.path.exists(DATA_FILE):
        return empty_data()

    try:
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    except (ValueError, OSError):
        # The file exists but is damaged or unreadable.
        # We warn the user instead of allowing the program to crash.
        print("Warning: the data file could not be read. Starting with empty data.")
        return empty_data()


def save_data(data):
    """Write the whole data dictionary back to the JSON file."""
    try:
        with open(DATA_FILE, "w") as file:
            json.dump(data, file, indent=4)
    except OSError:
        print("Error: the data could not be saved to disk.")
