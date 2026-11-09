import theticketpost.settings
import theticketpost.applications
import os
from loguru import logger
from github import Github
import requests
import json
from packaging import version
import threading
import time
import urllib.parse
import re

RAW_URL = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
# The catalog is read again in the background every few hours, so new apps and
# updates show up without restarting. Each read is one GitHub API call
# (unauthenticated calls are limited to 60/hour).
AUTO_REFRESH_SECONDS = 3 * 3600
# The service checks for a newer version of itself in the same round. Reading
# setup.py from raw.githubusercontent.com doesn't count against the API limit.
CORE_REPOSITORY = "theticketpost/theticketpost-service"
CORE_SETUP_URL = RAW_URL.format(repo=CORE_REPOSITORY, ref="main", path="setup.py")

# Every app published in the repository: {name: {'desc': desc, 'path': path in the repo}}
catalog = {}
apps_folder = ""
repository_name = ""
branch = ""
repo_files = []

# Catalog refresh state: one read at a time
refresh_lock = threading.Lock()
loading = False
checked_at = 0.0     # time.time() of the last read, failed or not
loaded_at = 0.0      # time.time() of the last successful read
last_error = ""
auto_refresh_started = False
core_version = ""    # latest published version of the service, "" until known


def compare_version_number(a, b):
    if version.parse(a) > version.parse(b):
        return 1
    elif version.parse(a) < version.parse(b):
        return -1
    else:
        return 0


def list():
    """Apps that are not installed or have a newer version in the repository."""
    available = {}
    for name, entry in catalog.items():
        installed = theticketpost.applications.get(name)
        if installed is None:
            available[name] = {'update': False, **entry}
        elif compare_version_number(installed.desc.get('version', '0'), entry['desc']['version']) < 0:
            available[name] = {'update': True, **entry}
    return available



def write_file(bytes_file, dest_path):
    with open(dest_path, 'wb') as f:
        f.write(bytes_file)



def repo_get_file(path):
    url = RAW_URL.format(repo=repository_name, ref=branch, path=urllib.parse.quote(path))
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content



def repo_download_app(path):
    for file_path in repo_files:
        if file_path.startswith(path + "/"):
            dest_path = os.path.join(apps_folder, file_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            write_file(repo_get_file(file_path), dest_path)



icons = {}

def get_icon(app_name):
    """icon.svg of a store app (the UI can't <use> an svg from another origin)"""
    entry = catalog.get(app_name)
    if entry is None:
        return None
    path = entry['path'] + '/static/icon.svg'
    if path not in repo_files:
        return None
    if path not in icons:
        icons[path] = repo_get_file(path)
    return icons[path]



def install_application(app_name):
    """Returns (http code, message, restart needed)."""
    available = list()
    if app_name not in available:
        return 500, "Application not found", False

    entry = available[app_name]
    action = 'updated' if entry["update"] else 'installed'

    # Files are written over the existing folder, so config.json and uploaded files are kept
    app_folder = os.path.join(apps_folder, entry['path'])
    try:
        os.makedirs(app_folder, exist_ok=True)
        repo_download_app( entry['path'] )
        restart_needed = theticketpost.applications.load_module(app_folder, entry['desc'])
    except Exception as e:
        logger.exception(f"Error installing {app_name}")
        return 500, f"Error installing {app_name}: {e}", False

    if restart_needed:
        return 200, f"Application {action}. Restart the service to use its updated libraries", True

    return 200, f"Application {action} successfully", False



def load_catalog():
    """Three GitHub API calls (repository, branch, tree) list the whole repository
    (unauthenticated calls are limited to 60/hour); files are downloaded from
    raw.githubusercontent.com."""
    global repo_files, branch, catalog

    repository = repository_name
    repo = Github(retry=None, timeout=15).get_repo(repository)
    # files are read at the branch's last commit, not at the branch name:
    # raw.githubusercontent.com caches a branch's files for ~5 minutes, and
    # a push showed up in the tree but with the old desc.json (no update offered)
    commit = repo.get_branch(repo.default_branch).commit.sha
    tree = repo.get_git_tree(commit, recursive=True)
    files = [element.path for element in tree.tree if element.type == "blob"]

    apps = {}
    for file_path in files:
        folder, _, filename = file_path.partition("/")
        if filename == "desc.json" and not folder.startswith("{{"):
            try:
                url = RAW_URL.format(repo=repository, ref=commit, path=urllib.parse.quote(file_path))
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                desc = json.loads(response.content)
                apps[desc['name']] = {'desc': desc, 'path': folder}
            except (ValueError, KeyError, requests.RequestException) as e:
                logger.error(f"Invalid app description in {file_path}: {e}")

    if repository != repository_name:
        # the repository was changed in Settings while this one was being read
        return False
    # installs download the same commit the catalog was read from
    branch, repo_files, catalog = commit, files, apps
    icons.clear()
    logger.info(f"App store loaded {len(catalog)} applications from {repository}")
    return True



def load_core_version():
    global core_version
    try:
        response = requests.get(CORE_SETUP_URL, timeout=15)
        response.raise_for_status()
        match = re.search(r'version\s*=\s*"([^"]+)"', response.text)
        if match:
            core_version = match.group(1)
    except requests.RequestException as e:
        logger.warning(f"Could not check for a new version of the service: {e}")



def load_catalog_safe():
    # A store failure (no network, GitHub rate limit...) must not affect the service;
    # the previous catalog stays
    global loading, checked_at, loaded_at, last_error
    try:
        load_core_version()
        if repository_name:
            # False: the repository changed in Settings during the read, read the new one
            while not load_catalog():
                pass
            loaded_at = time.time()
        last_error = ""
    except Exception as e:
        last_error = str(e)
        logger.error(f"Could not load the app store from {repository_name}: {e}")
    finally:
        checked_at = time.time()
        loading = False



def refresh(max_age=0):
    """Reads the catalog again in the background, unless the last read is less
    than max_age seconds old. Returns True when a read is going on."""
    global loading
    with refresh_lock:
        if loading:
            return True
        if max_age and time.time() - checked_at < max_age:
            return False
        loading = True
    threading.Thread(target=load_catalog_safe, name="appstore", daemon=True).start()
    return True



def status():
    return {
        "loading": loading,
        "checked_at": checked_at or None,
        "loaded_at": loaded_at or None,
        "error": last_error,
    }



def auto_refresh():
    while True:
        time.sleep(AUTO_REFRESH_SECONDS)
        # a refresh from the store page in the meantime counts
        refresh(max_age=AUTO_REFRESH_SECONDS - 60)



def init(flaskApp):
    global apps_folder
    global repository_name
    global catalog
    global checked_at, loaded_at, last_error
    global auto_refresh_started

    catalog = {}
    checked_at = loaded_at = 0.0
    last_error = ""

    # Folder where applications will be installed
    apps_folder = os.path.join(theticketpost.settings.get_storage_path(), "apps")
    os.makedirs(apps_folder, exist_ok=True)

    # Get repository name configured in theticketpost settings file
    config = theticketpost.settings.get_json("config")
    repository_name = config.get('repository', {}).get('name', "")
    if not repository_name:
        logger.warning("No apps repository configured, the app store will be empty")

    refresh()
    if not auto_refresh_started:
        auto_refresh_started = True
        threading.Thread(target=auto_refresh, name="appstore-refresh", daemon=True).start()
