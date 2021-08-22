import subprocess
from config import HOME
BASEPATH = HOME + '/PhotoBerry/github/PhotoBerry'


def insertDatabase(inserimento):
    subprocess.call(['python', BASEPATH + '/insertDatabase.py', inserimento])


def updateDatabase():
    subprocess.call(['python', BASEPATH + '/updateDatabase.py'])
