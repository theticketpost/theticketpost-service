# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

theticketpost-service is a Flask web service that builds a personal "newspaper" out of pluggable apps, renders it to an image, and prints it on a Bluetooth LE thermal receipt printer (384 dots per line). It targets a Raspberry Pi but runs on any Linux machine.

## Commands

```bash
# Virtualenv lives in .theticketpost/ at the repo root (Python >= 3.10)
python3 -m venv .theticketpost && source .theticketpost/bin/activate

# Install (records installed files so they can be removed later)
python3 setup.py install --record files.txt

# Uninstall
xargs rm -rf < files.txt

# Run (console entry point -> theticketpost.app:main); UI at http://localhost:8080
theticketpost-service
```

You must reinstall after changing code, templates or static files, because the entry point runs the installed package (`MANIFEST.in` bundles `templates/` and `static/`). To run from source instead, use `python -c "from theticketpost.app import main; main()"`.

Docker (state in the `/data` volume, which is `~/.theticketpost` inside the image; see `docker/README.md`):

```bash
docker build -f docker/Dockerfile -t theticketpost-service .
docker run -d -p 8080:8080 -v theticketpost-data:/data theticketpost-service
```

There are no tests, linter or CI.

## Runtime state: `~/.theticketpost/`

All state lives in `~/.theticketpost/` (`settings.py`), not in the repo:
- `config.json`: the global config (webserver port, printer device, weekly `schedule`, the app-store `repository.name`). Every page except settings, log and about redirects to `/settings` while this file is empty.
- `newspaper.json`: the ordered list of components on the ticket.
- `apps/<name>/`: installed apps. Each app's per-app config is saved here as `config.json`.
- `theticketpost.log`: the loguru log file, streamed to the UI at `/api/log/stream`.
- `last_newspaper.png`: the last rendered ticket.

The README advises deleting this folder after pulling updates, because stale config files can be incompatible with new code.

## Architecture

**Startup (`app.py:main`)**: reads config, starts the `Scheduler` thread, loads installed apps (`applications.init`), starts loading the GitHub app store catalog in a background thread (`appstore.init`), then runs Flask on `0.0.0.0`. `/api/restart` re-execs the process (closing inherited fds first, because werkzeug marks its socket inheritable).

**Plugin apps (`applications.py`, `application.py`)**: apps are hot-pluggable, so they must never register anything on Flask. Flask raises an error for setup methods (`register_blueprint`, `template_filter`...) once the first request is served. Instead:
- The core owns fixed routes: `/api/apps/<name>/<action>` dispatches through `Application.handlers()` (component, inspector, configuration, upload), and `/apps/<name>/static/<path>` serves app files.
- A Jinja `AppsTemplateLoader` finds `'<app>/component.html'` in each app's `templates/` folder.
- Apps register Jinja filters with `Application.add_template_filter`.
- Backwards compatibility: app templates still call `url_for('<name>app_blueprint.static', ...)`, which a `url_build_error_handler` maps to the new route. Old `/<name>app_blueprint/static/...` URLs saved in `newspaper.json`'s `rawhtml` are served by `legacy_app_static`.

`load_module` pip-installs unsatisfied `desc["requirements"]`, unloads the previous instance, purges from `sys.modules` every module whose file lives in the app folder (apps `sys.path.append` their folder and import helpers by bare names), imports `app.py` as `ttp_app_<name>`, and starts `App(desc, flaskApp)` as a thread. It returns True when pip changed the version of an already imported library, which needs a restart. The UI then offers one.

The apps live in the separate [theticketpost-apps](https://github.com/theticketpost/theticketpost-apps) repo, usually checked out next to this one (`../theticketpost-apps`). That repo is also the store: `appstore.py` lists it with one GitHub API call (git tree; the unauthenticated limit is 60 calls/hour), downloads files from raw.githubusercontent.com, and offers apps that aren't installed or have a newer `version`. The catalog is read again in the background every 3 hours, when the store page opens and it is over 10 minutes old, and from its "Check for updates" button (`/api/appstore/refresh?max_age=`, then poll `/api/appstore/status`), so new apps and updates show up without a restart. Bump an app's `version` in `desc.json` when you change it, so installed copies get offered the update.

**Print pipeline (`newspaper.py`)**:
1. Headless Chromium (pyppeteer) loads the service's own `/newspaper` page on localhost. It uses the system browser (`renderer.chromium_path` in config, else `chromium`/`google-chrome` on PATH). The page only shows `#newspaper` when a printer device is configured.
2. It screenshots the `#newspaper` element.
3. PIL dithers the screenshot to 1-bit.
4. `printer/cmd.py` encodes it as ESC/POS raster commands (`GS v 0`, chunks of 256 lines, with byte `0x0a` rewritten to avoid a line feed).
5. `printer/ble.py` sends the result over BLE with bleak.

Printing is triggered either by `/api/printer/<address>/print` or by the scheduler at the per-weekday times in `config.json`. Each step runs its own event loop with `asyncio.run` (`nest_asyncio` is no longer used). Because the renderer calls back into the service over HTTP, the server must be running for printing to work.

**Frontend**: Jinja templates (`templates/`) plus one Vue 3 app per page (`static/js/`), loaded from CDNs with pinned versions; there is no build step and no Bootstrap. `static/style.css` holds the design tokens and components. `static/js/common.js` (the `TTP` helpers) fills in the sidebar printer status and the store's update count. Vue uses `{ }` delimiters so they don't clash with Jinja's `{{ }}`. Flask caches templates, so restart the server after editing them.

The ticket (`ticket.html`) is shared by the editor (`home.html`, `data-editable="true"`) and `/newspaper` (the page the print pipeline screenshots). Keep editor-only styling under `.editable`. `static/newspaper.css` reproduces the Bootstrap 5.1 reboot and `.card` layout inside `#newspaper`, because app components were designed on top of it (sudoku positions its grid absolutely against `.ticket-body`, the box inside each `.ticket-item` that holds the section's HTML). Check a rendered print after changing it. A ticket entry is either a section (`appname`, `config`, `rawhtml`) or a random section (`{"type": "group", "mode": "daily"|"random", "shown": i, "items": [sections]}`): the editor shows one alternative at a time, and `/newspaper` picks the one to print when it loads (`newspaper.sections()` lists every section, including alternatives). Either kind can have `days` (weekdays it prints on, 0 Monday to 6 Sunday; missing means every day) and `link` (`"next"`/`"prev"`: printed only if that neighbour is). `skip_reasons` in `newspaper.js` works out what is left out today; `/newspaper` hides it and the editor dims it. Every attribute of the `<vuedraggable>` elements must keep the same value between renders (no object literals for `:group` or `:class`): when one changes, vuedraggable resets the Sortable options, and a drag in progress stops sorting. The editor composes the ticket by POSTing each section's config to `/api/apps/<name>/component` and saves the layout, including each section's rendered `rawhtml`, through `/api/settings/newspaper`. Generic JSON persistence goes through `/api/settings/<file>[?app=<name>]`. Saving the global `config` reschedules the print jobs; saving with `?app=` calls `refresh()` on that app. `Application.get_description()` adds `icon_url` (only when `icon.svg` has a `layer1` group, which the UI draws with `<use>`) and `needs_setup` (an empty key/token setting not marked `"optional"`).

**Google auth (`googleauth.py`)**: work in progress. The import in `app.py` is commented out, and the OAuth flow is incomplete.
