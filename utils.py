import json

def load_data():
    try:
        with open('data.json', 'r') as file:
            data = json.load(file)
            # Ensure both "users" and "customers" tables exist
            if "users" not in data:
                data["users"] = []
            if "customers" not in data:
                data["customers"] = []
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        # Initialize the data with empty "users" and "customers" tables if file is not found or unreadable
        return {"users": [], "customers": []}

def save_data(data):
    with open('data.json', 'w') as file:
        json.dump(data, file, indent=4)
