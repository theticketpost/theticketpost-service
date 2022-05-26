import asyncio
from pyppeteer import launch

async def to_img_thread(path, port):
    # launch chromium browser in the background
    browser = await launch()
    # open a new tab in the browser
    page = await browser.newPage()
    # add URL to a new page and then open it
    await page.goto("http://localhost:" + str(port) + "/newspaper")

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
