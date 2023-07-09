import os
import subprocess
from subprocess import Popen, PIPE
import time
import binascii
import sys
import shutil
import signal
import concurrent.futures
import json

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice, XBeeNetwork
from digi.xbee.devices import XBee64BitAddress
from digi.xbee.devices import DiscoveryOptions

# Reference to our local device
xbee = XBeeDevice("COM16", 230400)

dataReceived = False

# This list stores the raw bytes of the receieved image
receivedImage = []

chunk_count = 0

start_time = 0.00
end_time = 0.00

images_received = 0

# A reference to the remote xbee device
remote = None

# Returns the desired indicator state based on the current occupancy of each zone
# The return value is an integer corresponding to 1 of 4 states as follows:
#   1: <- (left)-
#   2: > (right)
#   3: ^ (up)
#   4: x (out)
def get_new_indicator_state():
    # JSON file containing the zone capacities
    file_path = './garage_status.json'
    with open(file_path, 'r') as file:
        data = json.load(file)

    # extract the Occupancy of each zone
    zone1_count = data.get("zone1_count")
    zone2_count = data.get("zone2_count")
    zone3_count = data.get("zone3_count")

    zone1_capacity = data.get("zone1_capacity")
    zone2_capacity = data.get("zone2_capacity")
    zone3_capacity = data.get("zone3_capacity")

    print(f'Occupancies: Zone 1 - {zone1_count}\tZone 2 - {zone2_count}\tZone 3 - {zone3_count}')


    file.close()

    # The indicator should direct to the car to the least full lower zone (1 or 2)
    # preferring zone 1 if both zones have equal occupancy. If both zones 1 and 2
    # are full, the indicator should direct the car to zone 3. If zone 3 is full
    #, the indicator should direct the car to zone 4 (out)

    # Check if the capacities are greater than zero to avoid division by zero
    assert zone1_capacity > 0, "zone1_capacity should be greater than 0"
    assert zone2_capacity > 0, "zone2_capacity should be greater than 0"
    assert zone3_capacity > 0, "zone3_capacity should be greater than 0"

    # Compute the ratio of occupancy for each zone
    zone1_ratio = zone1_count / zone1_capacity
    zone2_ratio = zone2_count / zone2_capacity
    zone3_ratio = zone3_count / zone3_capacity

    # Decide the zone based on the occupancy ratio
    if zone1_ratio < 1 or zone2_ratio < 1:
        # Both zone 1 and 2 are not full, prefer the least full one,
        # if they are equally full, zone 1 is preferred
        return 1 if zone1_ratio <= zone2_ratio else 2
    elif zone3_ratio < 1:
        # Zone 1 and 2 are full, but zone 3 is not
        return 3
    else:
        # All zones are full
        return 4


# def run_subprocess(command):
#     # runs a command in a subprocess and returns the return code
#     result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     return result.returncode
#
# def callback(future):
#     # callback function that gets called when run_subprocess is done
#     return_code = future.result()
#     print(f'Subprocess finished with return code: {return_code}')


# Called when the main loop of the program is killed by a keyboard interrupt
def cleanup():
    print("Cleaning up...")
    shutil.rmtree('images')
    xbee.close()  # ff00e505b8b5944d

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

def save_image_to_file(zone_number):
    global images_received
    images_received = images_received + 1
    global receivedImage, dataReceived
    # Combine all the received chunks.
    full_data = b''.join(receivedImage)


    # Save the file with a name that indicates the order in which it was taken and the zone
    filename = f'images/zone{zone_number}_{images_received}'

    # Ensure the directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Save the data to an image file.
    with open(f'{filename}.jpg', 'wb') as image_file:
        image_file.write(full_data)
    image_file.close()



    # Clear the accumulated data for future usage.
    receivedImage = []

    # Signal for the program to exit
    dataReceived = True


# Callback for data received from remote
def my_data_received_callback(xbee_message):
    global  dataReceived, receivedImage, chunk_count, start_time, end_time
    if chunk_count == 0:
        start_time = time.time()
    #address = xbee_message.remote_device.get_64bit_addr()
    #data = xbee_message.data.decode("utf8")

    # Extract the raw byte array from the message
    data = xbee_message.data

    # a var to store the most recently passed in zone number
    zone_number = None
    # Listen for the last packet
    try:
        #all_data_received = data.decode("utf8") == "done"
        decoded_data = data.decode("utf8")
        if decoded_data.startswith("zone"):
            all_data_received = True
            zone_number = int(decoded_data.split(' ')[1])
            print(f'Zone number: {zone_number}')
    except Exception:
        all_data_received = False


    # Once we have every frame, save the image to a file
    if all_data_received:

        # Calculate the elapsed time in seconds
        end_time = time.time()
        elapsed_time = end_time - start_time

        # Print the elapsed time
        print(f"Elapsed time: {elapsed_time:.1f} seconds")

        print(f'Done. Chunks recieved: {chunk_count}. Bytes received: {chunk_count * 45}')
        save_image_to_file(zone_number)
        print('File saved. Running image through LPR pipeline...')

        # Pass the image through the LPR pipeline
        lpr_command = 'python ./automatic_script.py 1 C:/Users/Paula/PycharmProjects/xbee_test/samples/us-1.jpg'
        subprocess.run(lpr_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Once the zone occupancy file is updated, fetch the new indicator state
        new_state = get_new_indicator_state()

        # Send the new indicator state as a response to the remote xbee (the node which sent the image)
        xbee.send_data(remote, str(new_state))

    else:
        # print("Received data from %s: %s" % (address, data))
        print(binascii.hexlify(data))
        receivedImage.append(data)
        chunk_count += 1


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
def node_discovered(remote_xbee):
    global remote
    print("hello")

    # Save a global reference to the remote xbee module
    remote = remote_xbee

    # Add the callback for data received from remote
    xbee.add_data_received_callback(my_data_received_callback)
    

# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    #lpr_command = 'python ./automatic_script.py 1 C:/Users/Paula/PycharmProjects/xbee_test/samples/us-1.jpg'

    # # create an Executor (uses a pool of threads by default)
    # executor = concurrent.futures.ThreadPoolExecutor()
    #
    # # start running the subprocess, return a Future representing the execution
    # future = executor.submit(run_subprocess, lpr_command)
    #
    # # add a callback to be run when the subprocess is done
    # future.add_done_callback(callback)


    #subprocess.run(lpr_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    #print('CWD: ' + os.getcwd())


    # Ensure files are cleaned up on exit
    signal.signal(signal.SIGINT, signal_handler)

    # Open a connection with the local XBee device
    xbee.open()

    xbee.flush_queues()

    # Send a broadcast message
    xbee.send_data_broadcast("Hello, XBee router!")



    # Instantiate the remote xbee device and read its info
    remote = RemoteXBeeDevice(xbee, XBee64BitAddress.from_hex_string("0013A2004219170D"))
    remote.read_device_info()
    remote_node_id = remote.get_node_id()
    print(remote_node_id)

    # Instantiate the xbee network and attempt to discover nodes on the network
    xnet = xbee.get_network()
    xnet.add_device_discovered_callback(node_discovered)
    xnet.set_discovery_options({DiscoveryOptions.APPEND_DD})
    xnet.set_discovery_timeout(25)

    # Start the discovery process and wait for it to be over.
    xnet.start_discovery_process()
    while xnet.is_discovery_running():
        time.sleep(0.2)

    # Get the list of the nodes in the network.
    nodes = xnet.get_devices()

    # Keep the connection open until data is received from the remote xbee
    while True:
        time.sleep(0.1) # TODO: replace busy-wait with non-blocking logic




