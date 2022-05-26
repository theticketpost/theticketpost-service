import asyncio

from bleak import BleakClient, BleakScanner
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice

from loguru import logger

POSSIBLE_SERVICE_UUIDS = [
    '0000ae30-0000-1000-8000-00805f9b34fb',
    '0000af30-0000-1000-8000-00805f9b34fb',
]

TX_CHARACTERISTIC_UUID = '0000ae01-0000-1000-8000-00805f9b34fb'

# This is a hacky solution so we don't terminate the BLE connection to the printer
# while it's still printing. A better solution is to subscribe to the RX characteristic
# and listen for printer events, so we know exactly when the printing is finished.
WAIT_AFTER_DATA_SENT_S = 30



async def scan_for_devices(timeout):
    device_ids = []

    scanner = BleakScanner()
    scanner.set_scanning_filter(filters={"UUIDs":POSSIBLE_SERVICE_UUIDS, "DuplicateData":False})

    try:
        logger.info("Scanning for BLE devices")
        await scanner.start()
        await asyncio.sleep(timeout)
        await scanner.stop()
    except:
        pass

    for d in scanner.discovered_devices:
        entry = {
            "name": d.name,
            "address": d.address,
        }
        device_ids.append(entry)

    return device_ids



def chunkify(data, chunk_size):
    return (
        data[i: i + chunk_size] for i in range(0, len(data), chunk_size)
    )



async def send_data(address, data):

    try:
        async with BleakClient(address) as client:
            chunk_size = client.mtu_size - 3
            # chunkify data and send to the client
            #for i, chunk in enumerate(chunkify(data, chunk_size)):
            #    await client.write_gatt_char(TX_CHARACTERISTIC_UUID, chunk)

            await asyncio.sleep(WAIT_AFTER_DATA_SENT_S)
            return "Send data finished: " + str(client.is_connected) + " MTU: " + str(client.mtu_size)
    except:
        return "ERROR: Not able to connect to device with address==" + address
