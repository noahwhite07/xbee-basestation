import os.path
import json
from difflib import SequenceMatcher
import sys


# Plate similarity function
def similar(plate1, plate2):
    return SequenceMatcher(None, plate1, plate2).ratio()


def update_zone_counter(previous_zone, new_zone, capacity_data):
    # Vehicle enters and immediately exits
    if (previous_zone == 0 and new_zone == 4):
        return capacity_data

    # Vehicle entering
    elif (previous_zone == 0):
        zone = f"zone{new_zone}_count"
        capacity_data[zone] += 1

    # Vehicle exiting
    elif (new_zone == 4):
        old_zone = f"zone{previous_zone}_count"
        if (capacity_data[old_zone] != 0):
            capacity_data[old_zone] -= 1
        else:
            print("Error: Zone updated to -1 vehicles")

    # Vehicle moving to a different zone
    else:
        old_zone = f"zone{previous_zone}_count"
        if (capacity_data[old_zone] != 0):
            capacity_data[old_zone] -= 1
        else:
            print("Error: Zone updated to -1 vehicles")
        new_zone = f"zone{new_zone}_count"
        capacity_data[new_zone] += 1

    return capacity_data


def check_zone_availability(capacity_data):
    if (capacity_data['zone1_count'] / capacity_data['zone1_capacity'] < 1):
        return 1
    elif (capacity_data['zone2_count'] / capacity_data['zone2_capacity'] < 1):
        return 2
    elif (capacity_data['zone3_count'] / capacity_data['zone3_capacity'] < 1):
        return 3
    else:
        return 0


def check_files_exist(log_path, cap_path):
    # Check if log file already exists
    file_exists = os.path.isfile(log_path)
    if (file_exists is False):
        with open(log_path, 'w') as f:
            print("Log file has been created")
            f.write(json.dumps([]))

    # Check if capacity file already exists
    file_exists = os.path.isfile(cap_path)
    if (file_exists is False):
        with open(cap_path, 'w') as f:
            status = {
                "zone1_count": 0,
                "zone2_count": 0,
                "zone3_count": 0,
                "zone1_capacity": 20,
                "zone2_capacity": 20,
                "zone3_capacity": 20,
            }
            f.write(json.dumps(status, indent=4))
            print("Capacity file has been created")


def read_json(file_path):
    with open(file_path, 'r') as file:
        json_data = json.load(file)
    return json_data


def write_json(file_path, json_data):
    with open(file_path, 'w') as file:
        json.dump(json_data, file, indent=4)


def match_and_log(new_detection):
    # Data to be written
    # Zones 1 and 2 represent ground floor
    # Zone 3 is anywhere from the ramp and above
    # Zone 4 is anywhere outside garage (exit)

    # Check if files exists
    log_file_path = "vehicle_log.json"
    capacity_file_path = "garage_status.json"
    check_files_exist(log_file_path, capacity_file_path)

    # Get JSON data from files
    log_data = read_json(log_file_path)
    capacity_data = read_json(capacity_file_path)

    # Check if license plate has already been detected
    # Update threshold according to system sensitivity
    threshold_correlation = 0.54
    unique_plate = True

    for element in log_data:
        plate = element["plate"]
        new_plate = new_detection["plate"]
        plate_similarity = similar(plate, new_plate)
        # For debugging/testing
        print("Correlation between ", plate, " and ", new_plate, " is: ", plate_similarity)

        # Similar plate found
        if (plate_similarity > threshold_correlation):
            # Vehicle is reentering
            if (element["zone"] == 4):
                update_zone_counter(0, new_detection["zone"], capacity_data)
            # Vehicle is moving to a different zone
            else:
                update_zone_counter(element["zone"], new_detection["zone"], capacity_data)

            # Update the log data
            element["zone"] = new_detection["zone"]
            element["lastSeen"] = new_detection["lastSeen"]
            unique_plate = False
            break

    # Append to log if new plate
    if (unique_plate):
        update_zone_counter(0, new_detection["zone"], capacity_data)
        log_data.append(new_detection)

    # Sort the data based on the "plate" key
    sorted_log_data = sorted(log_data, key=lambda x: x["plate"])

    # Write modified data back to the JSON files
    write_json(log_file_path, sorted_log_data)
    write_json(capacity_file_path, capacity_data)

    available_zone = check_zone_availability(capacity_data)
    return available_zone
