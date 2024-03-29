########################################################################
# Software for collecting data from PV energy meters
# Copyright (C) 2021 Axel Bernardinis <abernardinis@hotmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
########################################################################

import subprocess
from config import HOME
BASEPATH = HOME + '/PhotoBerry/github/PhotoBerry'


def insertDatabase(inserimento):
    subprocess.call(['python', BASEPATH + '/insertDatabase.py', inserimento])


def updateDatabase():
    line = subprocess.check_output(['python', BASEPATH + '/updateDatabase.py'], universal_newlines=True)
    lines = [line for line in line.split('\n') if line]
    watts = 0
    for line in lines:
        if 'Return Watt:' in line:
            watts = int(line.split(':')[1])
        else:
            print(line)
    return watts