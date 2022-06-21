import os
import json
from loguru import logger

settings_folder = '~/.theticketpost'

def check_and_create_dir():
    if not os.path.exists(os.path.expanduser(settings_folder)):
        os.makedirs(os.path.expanduser(settings_folder))


def get_storage_path():
    return os.path.expanduser(settings_folder)


def get_json(file, folder=""):
    data = {}

    check_and_create_dir()
    path_to_file = os.path.join(get_storage_path(), folder, file + ".json")

    if not os.path.exists(path_to_file):
        logger.warning("File for " + file + " does not exists. Created an empty file")
        with open(path_to_file, 'w') as outfile:
            outfile.write('{}')

    with open(path_to_file) as json_file:
        data = json.load(json_file)

    return data


def save_json(file, data, folder=""):
    check_and_create_dir()
    path_to_file = os.path.join(os.path.expanduser(settings_folder), folder, file + ".json")

    with open(path_to_file, 'w') as outfile:
        json.dump(data, outfile)


def save_value( file, key, value, folder="" ):
    data = get_json( file, folder )
    data[key] = value
    save_json( file, data, folder )
