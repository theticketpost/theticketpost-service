import os
import json

settings_folder = '~/.theticketpost'

def check_and_create_dir():
    if not os.path.exists(os.path.expanduser(settings_folder)):
        os.makedirs(os.path.expanduser(settings_folder))


def get_json(file):

    data = {}

    check_and_create_dir()
    path_to_file = os.path.join(os.path.expanduser(settings_folder), file + ".json")

    if not os.path.exists(path_to_file):
        with open(path_to_file, 'w') as outfile:
            outfile.write('{}')

    with open(path_to_file) as json_file:
        data = json.load(json_file)

    #print(data)
    return data


def save_json(file, data):
    check_and_create_dir()
    path_to_file = os.path.join(os.path.expanduser(settings_folder), file + ".json")

    with open(path_to_file, 'w') as outfile:
        json.dump(data, outfile)


def save_value( file, key, value ):
    data = get_json( file )
    data[key] = value
    save_json( file, data )
