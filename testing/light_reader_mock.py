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

import logging
from datetime import datetime
from time import sleep
from threading import Event, Lock, Thread


class LightReaderMock:
    def __init__(self, channel):
        self.channel = channel
        self.format = '%H:%M:%S.%f'
        self.light = False
        self.callbacks = [[], []]
        self.callback_lock = Lock()
        self.events = [Event(), Event()]
        self.readBlinksThread = Thread(target=self._readBlinks)
        self.readBlinksThread.start()

    def _readBlinks(self):
        with open('testing/blinks') as fp:
            first_line = fp.readline()
            self.light = first_line.strip() == 'ON'
            logging.info('%s %s', self.getLightString(), self.getTimeString())
            for line in fp:
                sleep(float(line))
                self.light = not self.light
                logging.info('%s %s', self.getLightString(), self.getTimeString())
                i = int(self.light)
                self.events[i].set()
                self.callback_lock.acquire()
                for callback in self.callbacks[i]:
                    Thread(target=callback, args=(self.channel,)).start()
                self.callback_lock.release()
                self.events[i].clear()

    @staticmethod
    def cleanup():
        pass

    def isLightOn(self):
        return self.light

    def addCallbackLightOn(self, callback, bouncetime):
        # Put callback in 1 because it will be called when light is switched to True
        self._addCallback(callback, 1)

    def waitForLightOff(self):
        # Wait for event 0 because that is when the light just switched to False
        self.events[0].wait()

    def removeCallback(self):
        self.callback_lock.acquire()
        self.callbacks = [[], []]
        self.callback_lock.release()

    def getTimeString(self):
        return datetime.now().strftime(self.format)[:-3]  # -3 to remove microseconds

    def getLightString(self):
        return 'ON' if self.light else 'OFF'

    def _addCallback(self, callback, i):
        self.callback_lock.acquire()
        self.callbacks[i].append(callback)
        self.callback_lock.release()


def foo(dummy):
    print('                                   foo')


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s %(asctime)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    blink_manager = LightReaderMock(10)  # Dummy channel value
    sleep(3.4)
    blink_manager.addCallbackLightOn(foo, 10)  # Dummy bounce time
    sleep(4.5)
    blink_manager.removeCallback()
    print('%s Before wait' % blink_manager.getTimeString())
    blink_manager.waitForLightOff()
    print('%s After wait' % blink_manager.getTimeString())


if __name__ == '__main__':
    main()
