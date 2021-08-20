from datetime import datetime
from time import sleep
from threading import Event, Lock, Thread


class BlinkManager:
    def __init__(self):
        self.format = '%H:%M:%S.%f'
        self.strings = [
            'FALLING\n0 ON  <TIME>',
            'RISING\n1 OFF <TIME>',
        ]
        self.callbacks = [[], []]
        self.callback_lock = Lock()
        self.events = [Event(), Event()]
        self.readBlinksThread = None

    def __call__(self):
        self.readBlinksThread = Thread(target=self._readBlinks)
        self.readBlinksThread.start()

    def _readBlinks(self):
        with open('blinks') as fp:
            first_line = fp.readline()
            print
            print(f'{first_line} {self.getTimeString()}')
            i = 0 if first_line == 'OFF' else 1
            for line in fp:
                sleep(float(line))
                print(self.strings[i].replace('<TIME>', self.getTimeString()))
                self.events[i].set()
                self.callback_lock.acquire()
                for callback in self.callbacks[i]:
                    callback()
                self.callback_lock.release()
                self.events[i].clear()
                i = (i + 1) % 2  # To switch between 0 and 1

    def getTimeString(self):
        return datetime.now().strftime(self.format)[:-3]  # -3 to remove microseconds

    def _addCallback(self, callback, i):
        self.callback_lock.acquire()
        self.callbacks[i].append(callback)
        self.callback_lock.release()

    def addFallingCallback(self, callback):
        self._addCallback(callback, 0)

    def addRisingCallback(self, callback):
        self._addCallback(callback, 1)

    def _removeCallback(self, callback, i):
        self.callback_lock.acquire()
        self.callbacks[i].remove(callback)
        self.callback_lock.release()

    def removeFallingCallback(self, callback):
        self._removeCallback(callback, 0)

    def removeRisingCallback(self, callback):
        self._removeCallback(callback, 1)

    def waitForFalling(self):
        self.events[0].wait()

    def waitForRising(self):
        self.events[1].wait()


def foo():
    print('                                   foo')


def main():
    blink_manager = BlinkManager()
    blink_manager()
    sleep(3.4)
    blink_manager.addFallingCallback(foo)
    sleep(4.5)
    blink_manager.removeFallingCallback(foo)
    print(f'{blink_manager.getTimeString()} Before wait')
    blink_manager.waitForFalling()
    print(f'{blink_manager.getTimeString()} After wait')


if __name__ == '__main__':
    main()
