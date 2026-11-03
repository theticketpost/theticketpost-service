"""Loads, reloads and unloads apps at runtime.

Apps never register routes on Flask (Flask forbids it after the first request).
Instead the core has fixed routes that look the app up in `applications`, a
Jinja loader that finds app templates, and a url_for fallback that keeps the old
'<name>app_blueprint.static' endpoint used by app templates working.
"""
import theticketpost.newspaper
import theticketpost.settings

import os
import sys
import json
import shutil
import threading
import subprocess
import importlib
import importlib.util
from importlib import metadata

from flask import url_for
from jinja2 import BaseLoader, ChoiceLoader, FileSystemLoader, TemplateNotFound
from loguru import logger
from packaging.requirements import Requirement

LEGACY_STATIC_SUFFIX = 'app_blueprint.static'
STOP_TIMEOUT = 5

applications = {}
_lock = threading.RLock()
flaskApp = None
apps_folder = ""


def list():
    return applications


def get(name):
    return applications.get(name)



# ---------------------------------------------------------------------------
# Flask / Jinja integration
# ---------------------------------------------------------------------------

class AppsTemplateLoader(BaseLoader):
    """Finds templates in the apps' `templates` folders.
    Templates are named '<app>/<file>', so the app with that name is tried first."""

    def get_source(self, environment, template):
        prefix = template.split('/', 1)[0]
        apps = sorted(applications.values(), key=lambda app: app.name != prefix)
        for app in apps:
            try:
                return FileSystemLoader(app.template_folder).get_source(environment, template)
            except TemplateNotFound:
                continue
        raise TemplateNotFound(template)


def legacy_static_url(error, endpoint, values):
    """Apps' templates call url_for('<name>app_blueprint.static', filename=...)."""
    if endpoint.endswith(LEGACY_STATIC_SUFFIX):
        name = endpoint[:-len(LEGACY_STATIC_SUFFIX)]
        return url_for('app_static', name=name, **values)
    return None


def clear_template_cache():
    cache = flaskApp.jinja_env.cache
    if cache is not None:
        cache.clear()



# ---------------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------------

def installed_distributions():
    versions = {}
    for dist in metadata.distributions():
        name = dist.metadata['Name']
        if name:
            versions[name.lower()] = dist.version
    return versions


def unsatisfied_requirements(requirements):
    pending = []
    for requirement in requirements:
        req = Requirement(requirement)
        try:
            version = metadata.version(req.name)
            if req.specifier and not req.specifier.contains(version, prereleases=True):
                pending.append(requirement)
        except metadata.PackageNotFoundError:
            pending.append(requirement)
    return pending


def imported_distributions():
    """Names of the distributions whose modules are already imported."""
    imported = set()
    for module, dists in metadata.packages_distributions().items():
        if module in sys.modules:
            imported.update(dist.lower() for dist in dists)
    return imported


def install_requirements(requirements):
    """pip-installs what's missing. Returns True if an already imported
    library changed version, which Python can't swap without a restart."""
    pending = unsatisfied_requirements(requirements)
    if not pending:
        return False

    logger.info("Installing requirements: " + ", ".join(pending))
    before = installed_distributions()
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + pending)
    importlib.invalidate_caches()
    after = installed_distributions()

    changed = {name for name, version in before.items() if after.get(name, version) != version}
    stale = changed & imported_distributions()
    if stale:
        logger.warning("Libraries already in use were updated, restart needed: " + ", ".join(sorted(stale)))
        return True
    return False



# ---------------------------------------------------------------------------
# Load / unload
# ---------------------------------------------------------------------------

def purge_modules(path):
    """Forget every module imported from `path` so the next import reads the new code.
    Apps add their folder to sys.path and import helpers by plain names (e.g. 'board')."""
    path = os.path.realpath(path)
    for module_name, module in tuple(sys.modules.items()):
        module_file = getattr(module, '__file__', None)
        if module_file and os.path.realpath(module_file).startswith(path + os.sep):
            del sys.modules[module_name]
    sys.path[:] = [p for p in sys.path if os.path.realpath(p) != path]


def unload(name):
    with _lock:
        app = applications.pop(name, None)
        if app is None:
            return None

        logger.info("Stopping application " + name)
        app.stop()
        app.join(STOP_TIMEOUT)
        if app.is_alive():
            logger.warning(f"Application {name} did not stop in {STOP_TIMEOUT}s")

        purge_modules(app.root_path)
        clear_template_cache()
        return app


def load_module(path, desc):
    """Loads (or reloads) the app in `path`. Returns True if a restart is needed
    for the app to run with its updated libraries."""
    name = desc["name"]
    with _lock:
        restart_needed = install_requirements(desc.get("requirements", []))

        unload(name)
        purge_modules(path)

        logger.info("Loading application " + name)
        module_name = "ttp_app_" + name
        spec = importlib.util.spec_from_file_location(module_name, os.path.join(path, "app.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            app = module.App(desc, flaskApp)
        except Exception:
            sys.modules.pop(module_name, None)
            purge_modules(path)
            raise

        app.start()
        applications[name] = app
        clear_template_cache()
        return restart_needed


def uninstall_application(app_name):
    app = unload(app_name)
    if app is None:
        return 500, "Application not found"

    # In development the apps folder is usually a symlink to the apps repository: never delete it
    if os.path.islink(apps_folder) or os.path.islink(app.root_path.rstrip(os.sep)):
        logger.warning(f"{app.root_path} is a symlinked folder, files not deleted")
    else:
        shutil.rmtree(app.root_path)

    theticketpost.newspaper.delete_app_from_ticket(app_name)

    return 200, "Application uninstalled successfully"


def find_apps(folder):
    for root, dirs, files in os.walk(folder, topdown=True, followlinks=True):
        dirs[:] = [d for d in dirs if d != '.git' and not d.startswith('{{')]
        if "desc.json" in files:
            yield root


def init(flask_app):
    global flaskApp
    global apps_folder
    flaskApp = flask_app

    flask_app.jinja_env.loader = ChoiceLoader([flask_app.jinja_env.loader, AppsTemplateLoader()])
    flask_app.url_build_error_handlers.append(legacy_static_url)

    apps_folder = os.path.join(theticketpost.settings.get_storage_path(), "apps")
    os.makedirs(apps_folder, exist_ok=True)

    apps = []
    for root in find_apps(apps_folder):
        try:
            with open(os.path.join(root, "desc.json")) as json_file:
                apps.append((root, json.load(json_file)))
        except Exception as e:
            logger.error(f"Could not read the description of the application in {root}: {e!r}")

    # Install every app's libraries before importing any app: installing them
    # one app at a time can update a library an earlier app already imported
    # (e.g. python-dateutil after pandas), which needs a restart
    requirements = [requirement for root, desc in apps for requirement in desc.get("requirements", [])]
    try:
        install_requirements(requirements)
    except Exception as e:
        logger.error(f"Could not install the apps' requirements: {e!r}")

    for root, description in apps:
        # A broken app must not stop the service from starting
        try:
            load_module(root, description)
        except Exception as e:
            logger.error(f"Could not load application in {root}: {e!r}")
