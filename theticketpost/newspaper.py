import theticketpost.printer.ble
import theticketpost.printer.cmd
import theticketpost.settings

import asyncio
from pyppeteer import launch
from PIL import Image
from loguru import logger
import os

async def to_img_thread(path, port):

    # launch chromium browser in the background
    browser = await launch(
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False
    )
    # open a new tab in the browser
    page = await browser.newPage()
    # add URL to a new page and then open it
    await page.goto("http://localhost:" + str(port) + "/newspaper")

    await page.waitForSelector("#newspaper", { "visible": True })

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
    # close the browser
    await browser.close()


def to_img(path, port):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(to_img_thread(path, port))


def print(address, port):
    path = os.path.join(theticketpost.settings.get_storage_path(), 'last_newspaper.png')
    to_img(path, port)
    logger.info("Ticket rendered and saved in folder " + path)

    with Image.open(path) as img:
        dithered = img.convert("1")
        logger.info("Applied Floyd-Steinberg dither...")
        data = theticketpost.printer.cmd.cmds_print_img( dithered, True )
        loop = asyncio.get_event_loop()
        logger.info("Sending commands to device with address==" + address)
        loop.run_until_complete(theticketpost.printer.ble.send_data(address, data))
