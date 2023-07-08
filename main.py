import time
import binascii
import sys
import shutil
import signal

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

def cleanup():
    print("Cleaning up...")
    shutil.rmtree('images')

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
        print('File saved. Waiting for more data...')
    else:
        # print("Received data from %s: %s" % (address, data))
        print(binascii.hexlify(data))
        receivedImage.append(data)
        chunk_count += 1



# See PyCharm help at https://www.jetbrains.com/help/pycharm/
def node_discovered(remote_xbee):
    print("hello")

    # Add the callback for data received from remote
    xbee.add_data_received_callback(my_data_received_callback)
    

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
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


    xbee.close() #ff00e505b8b5944d

