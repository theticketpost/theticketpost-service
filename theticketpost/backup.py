"""Export and import the service's configuration as a .zip.

Two parts, exported together or on their own:
- settings: config.json (printer, schedule, AI providers, app store).
- newspaper: newspaper.json (the sections), and each app's config.json and
  uploaded files (e.g. the image section's picture).

Layout of the zip:
    manifest.json
    settings/config.json
    newspaper/newspaper.json
    newspaper/apps/<app>/config.json
    newspaper/apps/<app>/files/<file>
"""

import datetime
import io
import json
import os
import re
import zipfile

from loguru import logger
from werkzeug.utils import secure_filename

import theticketpost.applications
import theticketpost.appstore
import theticketpost.newspaper
import theticketpost.settings

FORMAT = 1
PARTS = ("settings", "newspaper")
# settings that belong to the machine, not to the configuration
MACHINE_SETTINGS = ("webserver", "renderer")
MAX_SIZE = 50 * 1024 * 1024

APP_NAME = r"[A-Za-z0-9_.-]+"
ALLOWED = re.compile(
    r"^(manifest\.json"
    r"|settings/config\.json"
    r"|newspaper/newspaper\.json"
    rf"|newspaper/apps/{APP_NAME}/config\.json"
    rf"|newspaper/apps/{APP_NAME}/files/[^/]+)$"
)


class BackupError(Exception):
    pass


def storage(*path):
    return os.path.join(theticketpost.settings.get_storage_path(), *path)


def app_folder(name):
    return storage("apps", name)


def read_json(path, default):
    try:
        with open(path) as json_file:
            return json.load(json_file)
    except (OSError, ValueError):
        return default


def export(parts, service_version):
    """The backup as zip bytes."""
    parts = [part for part in PARTS if part in parts]
    if not parts:
        raise BackupError("Choose what to export")

    apps = theticketpost.applications.list()
    manifest = {
        "format": FORMAT,
        "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "service_version": service_version,
        "parts": parts,
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        if "settings" in parts:
            archive.writestr("settings/config.json", json.dumps(read_json(storage("config.json"), {}), indent=2))

        if "newspaper" in parts:
            archive.writestr("newspaper/newspaper.json", json.dumps(read_json(storage("newspaper.json"), []), indent=2))
            manifest["apps"] = {name: app.desc.get("version", "") for name, app in apps.items()}
            for name in apps:
                folder = app_folder(name)
                config = os.path.join(folder, "config.json")
                if os.path.isfile(config):
                    archive.write(config, f"newspaper/apps/{name}/config.json")
                files = os.path.join(folder, "static", "files")
                if os.path.isdir(files):
                    for filename in sorted(os.listdir(files)):
                        path = os.path.join(files, filename)
                        if os.path.isfile(path):
                            archive.write(path, f"newspaper/apps/{name}/files/{filename}")

        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
    return buffer.getvalue()


def open_archive(data):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise BackupError("This is not a TheTicketPost backup (.zip)")

    if sum(info.file_size for info in archive.infolist()) > MAX_SIZE:
        raise BackupError("The backup is too big")
    for info in archive.infolist():
        if not info.is_dir() and not ALLOWED.match(info.filename):
            raise BackupError(f"Unexpected file in the backup: {info.filename}")

    try:
        manifest = json.loads(archive.read("manifest.json"))
    except (KeyError, ValueError):
        raise BackupError("This is not a TheTicketPost backup: manifest.json is missing")
    if manifest.get("format") != FORMAT:
        raise BackupError("This backup was made by a different version and can't be imported")
    return archive, manifest


def read_member_json(archive, name):
    try:
        return json.loads(archive.read(name))
    except (KeyError, ValueError):
        raise BackupError(f"{name} in the backup is damaged")


def import_backup(data):
    """Restores what the backup has. Returns a report:
    {"parts": [...], "installed": [...], "missing": [...], "restart": bool,
     "settings": the new config.json or None}"""
    archive, manifest = open_archive(data)
    names = set(archive.namelist())
    report = {"parts": [], "installed": [], "missing": [], "restart": False, "settings": None}

    if "settings/config.json" in names:
        config = read_member_json(archive, "settings/config.json")
        if not isinstance(config, dict):
            raise BackupError("settings/config.json in the backup is damaged")
        current = read_json(storage("config.json"), {})
        for key in MACHINE_SETTINGS:
            if key in current:
                config[key] = current[key]
            else:
                config.pop(key, None)
        theticketpost.settings.save_json("config", config)
        report["parts"].append("settings")
        report["settings"] = config

    if "newspaper/newspaper.json" in names:
        newspaper = read_member_json(archive, "newspaper/newspaper.json")
        if not isinstance(newspaper, list):
            raise BackupError("newspaper/newspaper.json in the backup is damaged")

        # apps the backup needs: the ones it has settings for and the ones on the ticket
        wanted = set(manifest.get("apps", {}))
        wanted |= {section.get("appname") for section in theticketpost.newspaper.sections(newspaper) if section.get("appname")}
        wanted |= {name.split("/")[2] for name in names if name.startswith("newspaper/apps/")}
        installed = theticketpost.applications.list()
        for name in sorted(wanted - set(installed)):
            if not re.fullmatch(APP_NAME, name):
                continue
            code, message, restart = theticketpost.appstore.install_application(name)
            if code == 200:
                report["installed"].append(name)
                report["restart"] = report["restart"] or restart
            else:
                report["missing"].append(name)
                logger.warning(f"Backup: could not install {name}: {message}")
        installed = theticketpost.applications.list()

        for name in names:
            match = re.match(rf"^newspaper/apps/({APP_NAME})/(config\.json|files/([^/]+))$", name)
            if not match or match.group(1) not in installed:
                continue
            app, filename = match.group(1), match.group(3)
            if filename is None:
                destination = os.path.join(app_folder(app), "config.json")
            else:
                filename = secure_filename(filename)
                if not filename:
                    continue
                destination = os.path.join(app_folder(app), "static", "files", filename)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, "wb") as out:
                out.write(archive.read(name))

        theticketpost.settings.save_json("newspaper", newspaper)
        for app in installed.values():
            try:
                app.refresh()
            except Exception as e:
                logger.warning(f"Backup: {app.name} could not reload its settings: {e!r}")
        report["parts"].append("newspaper")

    if not report["parts"]:
        raise BackupError("The backup is empty")
    logger.info(f"Backup imported: {', '.join(report['parts'])}"
                + (f"; installed {', '.join(report['installed'])}" if report["installed"] else "")
                + (f"; not available: {', '.join(report['missing'])}" if report["missing"] else ""))
    return report
