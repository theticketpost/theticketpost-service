# theticketpost-service

## How to install

```bash
$bash> sudo apt install python3-pip
$bash> pip3 install setuptools

# Virtual environment creation
$bash> python -m venv .theticketpost
$bash> source .theticketpost/bin/activate
$bash> pip install --upgrade pip

# Service installation
$bash> python3 setup.py install --record files.txt

# Service uninstallation
$bash> xargs rm -rf < files.txt
```

## How to run

```bash
$bash> theticketpost-service
```

Open a browser and navigates to `localhost:8080`

## Mockup

You can find the mockup [here](https://mydraft.cc/c9t85hh6j4edn171387g)

## Raspberry Pi

Tested on RaspberryPi 3 with Raspberry Pi OS Lite (64-bit) Debian Bullseye 

```bash
$bash> sudo apt update
$bash> sudo apt upgrade
$bash> sudo apt install git python3-pip chromium-browser
$bash> pip3 install setuptools
$bash> git clone https://github.com/theticketpost/theticketpost-service.git
$bash> cd theticketpost-service
$bash> python3 setup.py install --record files.txt
```
For fix `OSError: [Errno 8] Exec format error: '/home/pi/.local/share/pyppeteer/local-chromium/575458/chrome-linux/chrome'` -> [pyppetter issue 250](https://github.com/miyakogi/pyppeteer/issues/250)
