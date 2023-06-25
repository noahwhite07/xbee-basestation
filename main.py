# This is a sample Python script.
import time
import binascii

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice, XBeeNetwork
from digi.xbee.devices import XBee64BitAddress
from digi.xbee.devices import DiscoveryOptions

# Reference to our local device
xbee = XBeeDevice("COM16", 115200)

dataReceived = False

# This list stores the raw bytes of the receieved image
receivedImage = []

chunk_count = 0

def save_image_to_file():
    global receivedImage, dataReceived
    # Combine all the received chunks.
    full_data = b''.join(receivedImage)

    # Save the data to an image file.
    with open('received_image.jpg', 'wb') as image_file:
        image_file.write(full_data)

    # Clear the accumulated data for future usage.
    received_data = []

    # Signal for the program to exit
    dataReceived = True


# Callback for data received from remote
def my_data_received_callback(xbee_message):
    global  dataReceived, receivedImage, chunk_count
    address = xbee_message.remote_device.get_64bit_addr()
    #data = xbee_message.data.decode("utf8")

    # Extract the raw byte array from the message
    data = xbee_message.data

    # Listen for the last packet
    try:
        all_data_received = data.decode("utf8") == "done"
    except Exception:
        all_data_received = False



    # Once we have every frame, save the image to a file
    if all_data_received:
        print(f'Done. Chunks recieved: {chunk_count}. Bytes received: {chunk_count * 12}') # 2792, 2737, 1510
        save_image_to_file()
    else:
        # print("Received data from %s: %s" % (address, data))
        print(binascii.hexlify(data))
        receivedImage.append(data)
        chunk_count += 1



# See PyCharm help at https://www.jetbrains.com/help/pycharm/
def node_discovered(remote_xbee):
    print("hello")
    #xbee.send_data(remote_xbee, "I'm the shit; I'm fartin'")

    # Add the callback for data received from remote
    xbee.add_data_received_callback(my_data_received_callback)
    





# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    # Open a connection with the local XBee device
    xbee.open()

    # Send a broadcast message
    xbee.send_data_broadcast("Hello, XBee router!")

    # Instantiate the remote xbee device and read its info
    remote = RemoteXBeeDevice(xbee, XBee64BitAddress.from_hex_string("0013A20042191769"))
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
        time.sleep(0.5)

    # Get the list of the nodes in the network.
    nodes = xnet.get_devices()

    # Keep the connection open until data is received from the remote xbee
    while not dataReceived:
        time.sleep(0.1)

    xbee.close()

