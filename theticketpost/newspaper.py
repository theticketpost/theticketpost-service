import theticketpost.printer.ble
import theticketpost.printer.cmd
import theticketpost.settings

import asyncio
from pyppeteer import launch
from PIL import Image
from loguru import logger
import io
import os
import shutil
import threading

# one print at a time: two jobs on the same BLE connection interleave their data
print_lock = threading.Lock()

CHROMIUM_CANDIDATES = ['chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable']



def sections(newspaper):
    """Every section of the ticket, including the alternatives inside random
    sections ({"type": "group", "items": [...]})."""
    for item in newspaper if isinstance(newspaper, list) else []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "group":
            yield from (section for section in item.get("items", []) if isinstance(section, dict))
        else:
            yield item


def delete_app_from_ticket(app_name):
    json = theticketpost.settings.get_json("newspaper")
    if not isinstance(json, list):
        return
    kept = []
    for item in json:
        if item.get("type") == "group":
            item["items"] = [section for section in item.get("items", []) if section.get("appname") != app_name]
            if not item["items"]:
                continue
            if len(item["items"]) == 1:
                # one alternative left: it's an ordinary section again
                kept.append(item["items"][0])
                continue
            item["shown"] = min(item.get("shown", 0), len(item["items"]) - 1)
        elif item.get("appname") == app_name:
            continue
        kept.append(item)
    for index, item in enumerate(kept):
        item["id"] = index
    theticketpost.settings.save_json("newspaper", kept)


def chromium_path():
    """Browser used to render the ticket: `renderer.chromium_path` in config.json,
    else the system one. pyppeteer's own download doesn't work on ARM (Raspberry Pi)."""
    config = theticketpost.settings.get_json("config")
    path = config.get("renderer", {}).get("chromium_path")
    if path:
        return path
    for candidate in CHROMIUM_CANDIDATES:
        path = shutil.which(candidate)
        if path:
            return path
    return None


RENDER_TIMEOUT_MS = 5 * 60 * 1000


async def to_img_thread(path, port):

    # launch chromium browser in the background
    options = {}
    executable = chromium_path()
    if executable:
        options["executablePath"] = executable
    browser = await launch(
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
        autoClose=False,
        headless=True,
        # --disable-dev-shm-usage: /dev/shm is tiny in containers and makes Chromium crash
        args=["--no-sandbox", "--disable-dev-shm-usage"],
        **options
    )
    try:
        await screenshot_newspaper(browser, path, port)
    finally:
        await browser.close()


async def screenshot_newspaper(browser, path, port):
    # open a new tab in the browser
    page = await browser.newPage()
    # add URL to a new page and then open it
    # networkidle0 waits for every section to render; AI apps (a coloring page
    # drawn by an image model) can take minutes, well over the 30 s default
    await page.goto("http://localhost:" + str(port) + "/newspaper",
                    {'waitUntil': 'networkidle0', 'timeout': RENDER_TIMEOUT_MS})

    await page.waitForSelector("#newspaper", {"visible": True, "timeout": RENDER_TIMEOUT_MS})

    dimensions = await page.evaluate('''() => {

        return {
            width: document.getElementById("newspaper").offsetWidth,
            height: document.getElementById("newspaper").offsetHeight,
            deviceScaleFactor: window.devicePixelRatio,
        }
    }''')

    await page.setViewport(dimensions)

    # create a screenshot of the page and save it
    await page.screenshot({"path": path})


def to_img(path, port):
    asyncio.run(to_img_thread(path, port))


def print(address, port):
    if not print_lock.acquire(blocking=False):
        logger.warning("A ticket is already printing, ignoring the new request")
        return 409, "A ticket is already printing"
    try:
        return print_locked(address, port)
    finally:
        print_lock.release()


def printable(img):
    """The 1-bit image the printer gets, from the rendered screenshot."""
    # the printer needs lines of exactly dots_per_line pixels: a wider or
    # narrower image prints as garbage
    device = theticketpost.settings.get_json("config").get("printer", {}).get("device") or {}
    width = int(device.get("dots_per_line", 384))
    if img.width != width:
        logger.warning(f"Ticket is {img.width}px wide, the printer needs {width}px: resizing")
        img = img.resize((width, round(img.height * width / img.width)))
    return img.convert("1")


def last_print_png():
    """The last printed ticket as the printer got it (PNG bytes), or None."""
    path = os.path.join(theticketpost.settings.get_storage_path(), 'last_newspaper.png')
    if not os.path.exists(path):
        return None
    with Image.open(path) as img:
        out = io.BytesIO()
        printable(img).save(out, "PNG")
        return out.getvalue()


def print_locked(address, port):
    path = os.path.join(theticketpost.settings.get_storage_path(), 'last_newspaper.png')
    try:
        to_img(path, port)
    except Exception as e:
        logger.error(f"Error rendering the ticket: {e}")
        return 500, str(e)
    logger.info("Ticket rendered and saved in folder " + path)

    printer = theticketpost.settings.get_json("config").get("printer", {})
    with Image.open(path) as img:
        dithered = printable(img)
        logger.info("Applied Floyd-Steinberg dither...")
        density = printer.get("density", theticketpost.printer.cmd.DEFAULT_DENSITY)
        data = theticketpost.printer.cmd.cmds_print_img(dithered, density)
        try:
            asyncio.run(theticketpost.printer.ble.send_data(address, data, pace=printer.get("pace", True)))
        except Exception as e:
            return 500, str(e)

        return 200, "Printed successfully"
