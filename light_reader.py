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

try:
    import RPi.GPIO as GPIO
except:
    logging.error('No root privileges.\nSkipping RPi.GPIO import')


class LightReader:
    """
    The circuit is such that a low voltage means that the light is on.
    """
    def __init__(self, channel):
        self.channel = channel
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.channel, GPIO.IN)  # phototransistor is an input

    @staticmethod
    def cleanup():
        GPIO.cleanup()

    def isLightOn(self):
        # Negate because the circuit is such that low voltage means the light is on
        return not bool(GPIO.input(self.channel))

    def addCallbackLightOn(self, callback, bouncetime):
        # When light turns on, the voltage goes from high to low, so GPIO.FALLING
        GPIO.add_event_detect(self.channel, GPIO.FALLING, callback=callback, bouncetime=bouncetime)

    def waitForLightOff(self):
        # When light turns off, the voltage goes from low to high, so GPIO.RISING
        GPIO.wait_for_edge(self.channel, GPIO.RISING)

    def removeCallback(self):
        GPIO.remove_event_detect(self.channel)
