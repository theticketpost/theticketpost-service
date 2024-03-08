import theticketpost.settings
import os
from loguru import logger

import subprocess
import importlib.util
import sys
import json

applications = {}

def list():
    global applications
    return  applications


def load_module(path, desc,flaskApp):
    global applications

    logger.info("Loading application " + desc["name"])
    
    if "requirements" in desc:
        requirements = desc["requirements"]
        subprocess.check_call(["pip", "install"] + requirements)
    
    spec = importlib.util.spec_from_file_location(desc["name"], path)
    foo = importlib.util.module_from_spec(spec)
    sys.modules[desc["name"]] = foo
    spec.loader.exec_module(foo)

    app = foo.App(desc, flaskApp)
    app.start()
    applications[desc["name"]] = app
    flaskApp.register_blueprint(app.blueprint)


def init(flaskApp):
    apps_folder = os.path.join(theticketpost.settings.get_storage_path(), "apps")
    if not os.path.exists(apps_folder):
        os.makedirs(apps_folder)

    for root, dirs, files in os.walk(apps_folder, topdown=True, followlinks=True):
        dirs[:] = [d for d in dirs if d not in ['.git']]
        for file in files:
            if file == "desc.json":
                #Load this library
                with open(os.path.join(root, file)) as json_file:
                    description = json.load(json_file)
                module_path = os.path.join(root, "app.py")
                load_module(module_path, description, flaskApp)
