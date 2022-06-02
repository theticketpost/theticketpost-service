import asyncio

from bleak import BleakClient, BleakScanner
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice

from loguru import logger

POSSIBLE_SERVICE_UUIDS = [
    '0000ae30-0000-1000-8000-00805f9b34fb',
    '0000af30-0000-1000-8000-00805f9b34fb',
]

TX_CHARACTERISTIC_UUID = '0000ff02-0000-1000-8000-00805f9b34fb'
NOTIFICATION_CHARACTERISTIC_UUI = '0000ff03-0000-1000-8000-00805f9b34fb'


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
        logger.info("Connecting to device with address==" + address + " ...")
        async with BleakClient(address) as client:
            logger.info("Connected to device with address==" + address + " MTU: " + str(client.mtu_size))
            chunk_size = client.mtu_size - 3

            # DEBUG INFO
            for service in client.services:
                logger.debug("[Service] {0}: {1}".format(service.uuid, service.description))
                for char in service.characteristics:
                    if "read" in char.properties:
                        try:
                            value = bytes(await client.read_gatt_char(char.uuid))
                        except Exception as e:
                            value = str(e).encode()
                    else:
                        value = None
                    logger.debug(
                        "\t[Characteristic] {0}: (Handle: {1}) ({2}) | Name: {3}, Value: {4} ".format(
                            char.uuid,
                            char.handle,
                            ",".join(char.properties),
                            char.description,
                            value,
                        )
                    )
                    for descriptor in char.descriptors:
                        value = await client.read_gatt_descriptor(descriptor.handle)
                        logger.debug(
                            "\t\t[Descriptor] {0}: (Handle: {1}) | Value: {2} ".format(
                                descriptor.uuid, descriptor.handle, bytes(value)
                            )
                        )
            # DEBUG INFO END

            async def notification_callback(sender, data):
                if data == bytearray(b'\x1a\x0f\x0c'):
                    await client.disconnect()

            await client.start_notify(NOTIFICATION_CHARACTERISTIC_UUI, notification_callback)

            # chunkify data and send to the client
            logger.info("Transmiting data to device with address==" + address)
            for i, chunk in enumerate(chunkify(data, chunk_size)):
                await client.write_gatt_char(TX_CHARACTERISTIC_UUID, chunk)

            logger.info("Finished data transmission." )

            while client.is_connected:
                await asyncio.sleep(1)


    except Exception as e:
        logger.error(str(e))
