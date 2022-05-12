import os
import json

def createDir():
    if not os.path.exists(os.path.expanduser('~/.theticketpost')):
        os.makedirs(os.path.expanduser('~/.theticketpost'))

def set( file, key, value ):
    createDir()
    print('patata')
