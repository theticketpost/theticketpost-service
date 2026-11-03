# theticketpost-service

## How to install

```bash
$bash> sudo apt install python3-pip
$bash> pip3 install setuptools

# Virtual environment creation (Python >= 3.10)
$bash> python3 -m venv .theticketpost
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

> After each repository update, clean config files hosted on local (~/.theticketpost) to avoid unwanted behaviours because of not compatible config files :)

## Docker

```bash
$bash> docker build -f docker/Dockerfile -t theticketpost-service .
$bash> docker run -d -p 8080:8080 -v theticketpost-data:/data theticketpost-service
```

See [docker/README.md](docker/README.md) for compose, Bluetooth printing and local apps.

## Applications
**theticketpost-service** will load automatically all the applications located in the folder `~/.theticketpost/apps`. So place there the applications you desire to load from the [apps repository](https://github.com/theticketpost/theticketpost-apps) or create a symbolic link named `apps` in `~/.theticketpost` pointing to the **apps repository folder** to load all the applications hosted in the repo.

Apps can be installed, updated and uninstalled from the store without restarting the service. A restart is only needed when an update changes the version of a library that is already in use; the store page then shows a "Restart now" button.

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
The ticket is rendered with the system Chromium (`chromium`, `chromium-browser` or `google-chrome` found in the PATH). To use another browser set `"renderer": {"chromium_path": "/path/to/chromium"}` in `~/.theticketpost/config.json`.
