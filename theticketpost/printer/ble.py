import asyncio

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakDeviceNotFoundError
from dbus_fast import BusType, Message, MessageType
from dbus_fast.aio import MessageBus
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice

from loguru import logger


PRINT_WIDTH = 384

POSSIBLE_SERVICE_UUIDS = [
    '0000ae30-0000-1000-8000-00805f9b34fb',
    '0000af30-0000-1000-8000-00805f9b34fb',
]

TX_CHARACTERISTIC_UUID = '0000ff02-0000-1000-8000-00805f9b34fb'
NOTIFICATION_CHARACTERISTIC_UUI = '0000ff03-0000-1000-8000-00805f9b34fb'


DBUS_SOCKET = "/run/dbus/system_bus_socket"


# Measured on a laptop (MediaTek MT7925): ~70% of connections take 1-7 s, the
# rest hang for ~40 s or fail. Cutting a slow attempt and retrying with a new
# scan prints sooner than waiting on it.
CONNECT_TIMEOUT = 20
CONNECT_ATTEMPTS = 6
# After a disconnect the printer can go quiet for a while before advertising again
SCAN_TIMEOUT = 20
# How long to wait for the printer's "done" notification after sending everything
DONE_TIMEOUT = 120
DONE_NOTIFICATION = bytearray(b'\x1a\x0f\x0c')
# Pacing, for printers without flow control (see FlowControl): the printer
# slows down on dark areas, but writes without response don't wait for it:
# sending dark areas faster than it prints them can make it lose steps and
# squash what follows.
# 384 dots per line: about 60 full black lines per second.
DARK_DOTS_PER_SECOND = 384 * 60
# don't sleep for less than this (asyncio.sleep overhead)
MIN_SLEEP = 0.01


def explain_error(e):
    """Turn bleak's low-level errors into something the user can act on."""
    msg = str(e)
    if isinstance(e, (asyncio.TimeoutError, TimeoutError)):
        return "Timed out talking to the printer. Check that it is on, in range and not connected to another device."
    if isinstance(e, FileNotFoundError) or "No such file or directory" in msg:
        return (f"Bluetooth is not reachable: {DBUS_SOCKET} not found. "
                "On Linux, start the bluetooth service. In Docker, mount the host's "
                "D-Bus socket (see docker/README.md).")
    if "AppArmor" in msg or "AccessDenied" in msg:
        return ("Bluetooth access denied by D-Bus. In Docker, run the container with "
                "--security-opt apparmor=unconfined (see docker/README.md).")
    if "org.bluez" in msg and ("ServiceUnknown" in msg or "not provided" in msg):
        return "BlueZ is not running on the host. Start the bluetooth service."
    return msg or repr(e)


async def scan_for_devices(timeout):
    device_ids = []

    scanner = BleakScanner(service_uuids=POSSIBLE_SERVICE_UUIDS)

    try:
        logger.info("Scanning for BLE devices")
        await scanner.start()
        await asyncio.sleep(timeout)
        await scanner.stop()

        for d in scanner.discovered_devices:
            entry = {
                "name": d.name,
                "address": d.address,
                "dots_per_line": PRINT_WIDTH
            }
            device_ids.append(entry)

    except Exception as e:
        msg = explain_error(e)
        logger.error(msg)
        return device_ids, 500, msg

    return device_ids, 200, "Success"


def chunkify(data, chunk_size):
    return (
        data[i: i + chunk_size] for i in range(0, len(data), chunk_size)
    )


async def drop_stale_connection(address):
    """Disconnect the printer if BlueZ still holds a connection to it.

    bleak doesn't disconnect when the process dies (a restart, a crash, a job cut
    short), so BlueZ keeps the printer connected. A connected printer stops
    advertising, the scan can't find it and every print fails until it's dropped.
    Linux (BlueZ) only: elsewhere this does nothing."""
    try:
        from bleak.backends.bluezdbus.utils import get_dbus_authenticator
        bus = await MessageBus(bus_type=BusType.SYSTEM, auth=get_dbus_authenticator()).connect()
    except Exception as e:
        logger.debug(f"Can't check BlueZ for a stale connection: {e}")
        return
    try:
        reply = await bus.call(Message(destination="org.bluez", path="/", member="GetManagedObjects",
                                       interface="org.freedesktop.DBus.ObjectManager"))
        if reply.message_type == MessageType.ERROR:
            return
        for path, interfaces in reply.body[0].items():
            device = interfaces.get("org.bluez.Device1")
            if not device or device["Address"].value.upper() != address.upper():
                continue
            if "Connected" in device and device["Connected"].value:
                logger.warning(f"BlueZ was still connected to {address} (a previous job didn't finish), disconnecting")
                await bus.call(Message(destination="org.bluez", path=path, member="Disconnect",
                                       interface="org.bluez.Device1"))
                # give the printer time to start advertising again
                await asyncio.sleep(2)
    finally:
        bus.disconnect()


async def find_printer(address):
    """Scan (LE only: the printer is BLE) until the printer shows up.

    Not BleakScanner.find_device_by_address: it stops the scan on the first
    advertisement, and on a laptop (MediaTek MT7925) the connection that follows
    took 2-80 s. Polling the scan like this connected in under 2 s."""
    scanner = BleakScanner(bluez={"filters": {"Transport": "le"}})
    await scanner.start()
    try:
        deadline = asyncio.get_running_loop().time() + SCAN_TIMEOUT
        while asyncio.get_running_loop().time() < deadline:
            for device in scanner.discovered_devices:
                if device.address.upper() == address.upper():
                    return device
            await asyncio.sleep(0.5)
        return None
    finally:
        await scanner.stop()


async def connect(address):
    """Find the printer with a scan, then connect to it.

    BlueZ forgets devices it hasn't seen recently, and connecting can take tens of
    seconds on some adapters, so retry with a generous timeout."""
    await drop_stale_connection(address)
    last_error = None
    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        device = await find_printer(address)
        if device is None:
            last_error = BleakDeviceNotFoundError(address, f"Printer {address} not found. Is it on and in range?")
            logger.warning(f"Attempt {attempt}/{CONNECT_ATTEMPTS}: printer {address} not found")
            continue
        client = BleakClient(device, timeout=CONNECT_TIMEOUT)
        try:
            await client.connect()
            return client
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt}/{CONNECT_ATTEMPTS}: could not connect to {address}: {explain_error(e)}")
    raise last_error


async def log_services(client):
    for service in client.services:
        logger.debug("[Service] {0}: {1}".format(service.uuid, service.description))
        for char in service.characteristics:
            logger.debug("\t[Characteristic] {0}: (Handle: {1}) ({2})".format(
                char.uuid, char.handle, ",".join(char.properties)))


async def read_mtu(client):
    """Ask BlueZ for the negotiated MTU.

    Without this, bleak on Linux reports the minimum (23), and the data went
    out in 20 byte chunks: too slow, the printer ran out of data mid-ticket,
    stopped and lost steps when it started again."""
    acquire = getattr(client._backend, "_acquire_mtu", None)
    if acquire is None:
        return
    try:
        await acquire()
    except Exception as e:
        logger.warning(f"Couldn't read the MTU, sending small chunks: {explain_error(e)}")


class FlowControl:
    """Credit based flow control, as these printers do it on the notify characteristic.

    Seen on a printer (MTU 200): right after the first data it sends 02 b6 00,
    the packets it can hold (0x00b6 = 182, little-endian), then 01 01 each time
    it prints one. Sending everything at once (~400 packets ahead) made it lose
    steps. Printers that don't send 02 get no flow control (and the dark-area
    pacing instead)."""

    # packets sent before the printer announces its window
    BEFORE_WINDOW = 4
    WINDOW_TIMEOUT = 1
    # waiting longer than this for room means the printer stopped confirming
    ROOM_TIMEOUT = 10

    def __init__(self):
        self.window = None
        self.sent = 0
        self.acked = 0
        self.max_outstanding = 0
        self.disabled = False
        self.changed = asyncio.Event()

    @property
    def active(self):
        return self.window is not None and not self.disabled

    def notification(self, value):
        """Take a flow control notification; False if it's something else."""
        if len(value) == 3 and value[0] == 0x02:
            self.window = int.from_bytes(value[1:3], 'little')
            logger.info(f"Printer buffer: {self.window} packets")
        elif len(value) == 2 and value[0] == 0x01:
            # one arrives before any data: never count more than was sent
            self.acked = min(self.acked + value[1], self.sent)
        else:
            return False
        self.changed.set()
        return True

    def has_room(self):
        outstanding = self.sent - self.acked
        limit = self.window if self.window is not None else self.BEFORE_WINDOW
        return outstanding < limit

    async def wait_for_room(self):
        if self.disabled:
            return
        loop = asyncio.get_running_loop()
        timeout = self.ROOM_TIMEOUT if self.window is not None else self.WINDOW_TIMEOUT
        deadline = loop.time() + timeout
        while not self.has_room():
            self.changed.clear()
            remaining = deadline - loop.time()
            try:
                if remaining <= 0:
                    raise asyncio.TimeoutError
                await asyncio.wait_for(self.changed.wait(), remaining)
            except asyncio.TimeoutError:
                if self.window is None:
                    logger.info("The printer doesn't report its buffer, sending without flow control")
                else:
                    logger.warning(f"The printer stopped confirming packets ({self.sent - self.acked} pending), "
                                   "sending the rest without flow control")
                self.disabled = True
                return
        self.max_outstanding = max(self.max_outstanding, self.sent - self.acked + 1)

    def summary(self):
        if self.window is None:
            return "not reported by the printer"
        return (f"buffer {self.window} packets, {self.acked}/{self.sent} confirmed, "
                f"at most {self.max_outstanding} pending" + (" (gave up)" if self.disabled else ""))


def black_dots(chunk):
    return sum(byte.bit_count() for byte in chunk)


async def send_data(address, data, pace=True):

    try:
        logger.info("Connecting to device with address==" + address + " ...")
        client = await connect(address)
        try:
            await read_mtu(client)
            logger.info("Connected to device with address==" + address + " MTU: " + str(client.mtu_size))
            await log_services(client)
            chunk_size = client.mtu_size - 3

            done = asyncio.Event()
            flow = FlowControl()

            def notification_callback(sender, value):
                if value == DONE_NOTIFICATION:
                    done.set()
                elif not flow.notification(value):
                    logger.debug(f"Printer notification: {bytes(value).hex(' ')}")

            await client.start_notify(NOTIFICATION_CHARACTERISTIC_UUI, notification_callback)

            # chunkify data and send to the client. Write without response, as
            # bleak < 0.21 did by default: with response every 20 byte chunk
            # waits for a round trip and printing takes minutes.
            logger.info("Transmiting data to device with address==" + address)
            started = asyncio.get_running_loop().time()
            owed = 0.0
            for chunk in chunkify(data, chunk_size):
                await flow.wait_for_room()
                await client.write_gatt_char(TX_CHARACTERISTIC_UUID, chunk, response=False)
                flow.sent += 1
                if pace and not flow.active:
                    # no flow control: give the printer time to print the dark dots just sent
                    owed += black_dots(chunk) / DARK_DOTS_PER_SECOND
                    if owed >= MIN_SLEEP:
                        await asyncio.sleep(owed)
                        owed = 0.0

            elapsed = asyncio.get_running_loop().time() - started
            logger.info(f"Finished data transmission: {len(data)} bytes in {elapsed:.1f} s "
                        f"({len(data) / max(elapsed, 0.001) / 1024:.1f} KB/s)")

            # wait until the printer says it's done, so we don't cut the job short
            try:
                await asyncio.wait_for(done.wait(), DONE_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning("The printer didn't report the end of the job, disconnecting anyway")
            logger.info(f"Flow control: {flow.summary()}")
        finally:
            await client.disconnect()

    except Exception as e:
        logger.error(explain_error(e))
        raise RuntimeError(explain_error(e)) from e
