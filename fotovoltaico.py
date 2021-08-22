########################################################################
# Software for collecting data from PV energy meters
# Copyright (C) 2014 Axel Bernardinis <abernardinis@hotmail.com>
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

"""
    Read the LED of the PV system power meter and store energy production data in a database
    VERSION : 6.0 (RPi.GPIO v0.5.8 required)
        -Split code in modules to make it testable
"""
import logging
import subprocess
from datetime import datetime, timedelta
from threading import Event, Lock, Thread
from time import sleep

from queue import Empty, Queue
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from config import HOME, EMAIL

TEST = False

LOGGING_LEVEL = logging.INFO if not TEST else logging.DEBUG
LOGGING_FORMAT = '[%(levelname)s %(asctime)s] %(funcName)s: %(message)s'
LOGGING_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

CHANNEL = 16  #GPIO pin for input signal
BOUNCETIME = 20  #50#500
LIGHT_READER = None
DB_MANAGER = None
TIMEOUT = 360  # If more than 360 seconds between blinks then PV system is off

QUEUE = Queue()
IS_OFF = Event()
LOCK_IS_OFF = Lock()
QUEUE_IST = Queue()
HTTPD = None  # Server object as global so I can stop it
ORAULTLAMP = datetime(1970,1,1)  # Last blink time needed for instantaneous power, used by one thread so no lock


class RequestHandler(BaseHTTPRequestHandler):
    port = 8001
    address = ('', port)
    def do_GET(self):
        global QUEUE_IST, ORAULTLAMP, LOCK_IS_OFF
        potenza = 0
        LOCK_IS_OFF.acquire()
        is_off = IS_OFF.isSet()
        LOCK_IS_OFF.release()
        if is_off:
            potenza = -1
        else:
            if (QUEUE_IST.qsize() == 2):
                logging.debug('Queue size == 2')
                t1 = QUEUE_IST.get() # sono sicuro ci sono quindi niente timeout
                t2 = QUEUE_IST.get() # sono sicuro ci sono quindi niente timeout
            else:
                logging.debug('Queue size != 2')
                try:
                    giaLampeggiato = (ORAULTLAMP.date() == datetime.now().date()) # controlla la data
                except NameError: # cioe' ORAULTLAMP not defined
                    logging.debug('NameError')
                    giaLampeggiato = False
                logging.debug('Already blinked: %s', giaLampeggiato)
                try:
                    if (giaLampeggiato):
                        t1 = ORAULTLAMP
                        t2 = QUEUE_IST.get(timeout=TIMEOUT)  # would be 10 watt so PV system is off
                    else: # non ha gia lampeggiato
                        t1 = QUEUE_IST.get(timeout=TIMEOUT)  # would be 10 watt so PV system is off
                        t2 = QUEUE_IST.get(timeout=TIMEOUT)  # very unlikely. Maybe not needed?
                except Empty:
                    logging.debug('Timeout, empty queue')
                    potenza = -1

        if (potenza != -1):
            timeDifference = t2 - t1
            potenza = 3600/(timeDifference.seconds + timeDifference.microseconds*0.000001)  # microseconds 10^-6
            ORAULTLAMP = t2
            logging.info('Power: %s LastBlinkTime: %s', potenza, ORAULTLAMP)
        potenza = int(round(potenza))
        parameters = parse_qs(urlparse(self.path).query)
        # mi restituisce i parametri GET come dizionario
            # {'callback':['nomefunzione']}
        self.send_response(200)
        self.send_header('Content-type','application/json')
        self.end_headers()
        # Send the html message
        # Per far funzionare JSONP devo restituire una roba tipo
            # nomefunzione({JSONOBJECT});
            # nomefunzione deve essere il parametro callback="stringanomefuzione"
        try:
            parameter_name = str(parameters['callback'][0])
        except KeyError:
            parameter_name = 'potenza'
        response_string = parameter_name + '({"potenza":'+str(potenza)+'});'
        self.wfile.write(response_string.encode('utf-8'))



def instantServer():
    logging.info('Starting server')
    HTTPD.serve_forever()
    logging.info('Server closed')


def insertValues():
    global QUEUE
    lastBlinkTime = datetime.now()
    logging.info('Just started, so extra wait for next clean 5 minutes')
    sleep(secondsUntilNext5min())

    while True:
        LOCK_IS_OFF.acquire()
        is_off = IS_OFF.isSet()
        LOCK_IS_OFF.release()
        logging.info('Wait for next clean 5 minutes. System: %s', 'OFF' if is_off else 'ON')
        sleep(secondsUntilNext5min())
        insertTime = datetime.now()
        insertTime = insertTime + timedelta(seconds=1)  # To be sure of having 5 minutes instead of 4:59
        insertTime = insertTime.replace(second=0, microsecond=0)  # Cleanup seconds and microseconds for clean DB
        blinkTimes = []
        while (not QUEUE.empty()):
            blinkTimes.append(QUEUE.get_nowait())
        watt = len(blinkTimes)
        if watt == 0:
            if is_off:
                logging.debug('PV system was off and no new watts, so go to next loop and wait another 5 minutes')
            else:
                if (datetime.now() - lastBlinkTime).seconds > TIMEOUT:
                    logging.info('PV system is off')
                    LOCK_IS_OFF.acquire()
                    IS_OFF.set()  # True
                    LOCK_IS_OFF.release()
                    wattsProduced = DB_MANAGER.updateDatabase()
                    logging.info('Wh produced: %s', wattsProduced)
                    mail = sendMail(wattsProduced)
                    if (mail != 0):
                        logging.error('Failed sending email')
                    else:
                        logging.info('Sent mail')
                    logging.info('Empty instant queue')
                    emptyQueue(QUEUE_IST)
                else:
                    logging.debug('PV system on and no new watts, but last blink not older than timeout, so still on')
            # Since it is 0 watts, go to the next loop and wait for more blinks
            continue
        if is_off:
            logging.info('PV system back on')
            LOCK_IS_OFF.acquire()
            IS_OFF.clear()  # False
            is_off = IS_OFF.isSet()
            LOCK_IS_OFF.release()
        lastBlinkTime = blinkTimes[-1]
        maxPower = 0
        indexMaxPower = 0
        for i in range(1, len(blinkTimes)):
            timeDifference = (blinkTimes[i] - blinkTimes[i-1])  # timedelta between blinks
            power = 3600/(timeDifference.seconds + timeDifference.microseconds*0.000001)  # microseconds 10^-6
            if (power > maxPower):
                maxPower = power
                indexMaxPower = i
        maxPowerTime = blinkTimes[indexMaxPower]
        if (watt == 1 or watt == 2):
            timeForQuery = lastBlinkTime
        else:
            timeForQuery = insertTime
        insertQuery = 'insert into potenza(GIORNO, ORA, WATT, PICCO_WATT, PICCO_ORA) values ' \
            "(curdate(),'%s', %d, %d, '%s')" % \
            (timeForQuery.strftime('%H:%M:%S'), watt, round(maxPower), maxPowerTime.strftime('%H:%M:%S'))
        logging.info('Insert 5 minutes data in database')
        DB_MANAGER.insertDatabase(insertQuery)


def secondsUntilNext5min():
    oraWakeUp = datetime.now() + timedelta(seconds = 5)  # aggiungo secondi per evitare di chimare stesso 5 min
    # ESEMPIO:
    # ora = 14:52:00.0 mi dara' oraWakeUp = 14:55:00.0 ma poi io faro' sleep dei secondi di differenza tra oraWakeUp e
    # adesso, quindi trascuro i microsecondi quindi quando mi risvegliero', avendo trascurato i microsecondi non saranno
    # le 14:55:00.0 ma tipo 14:54:59.45 quindi se la funzione (insertValues) dura tipo 200 ms, avro' come 'ora inizio'
    # 14:54:59.65 e quindi avrei come wakeup di nuovo 14:55:00.0 per evitare questo, anche se viene di nuovo chiamata
    # alle 14:54:59.65, aggiungo 5 secondi cosi' sono sicuro di cadere nella prossima fascia
    secondsToAdd = (4 - oraWakeUp.minute % 5) * 60 + 60 - oraWakeUp.second
    oraWakeUp = oraWakeUp + timedelta(seconds=secondsToAdd)
    oraWakeUp = oraWakeUp.replace(microsecond=0)
    return (oraWakeUp - datetime.now()).seconds


def emptyQueue(queue):
    empty = False
    while not empty:
        try:
            queue.get_nowait()
        except Empty:
            empty = True


def readLED(channel): # parameter needed by callbacks passed to GPIO
    global QUEUE, QUEUE_IST
    blinkTime = datetime.now()
    logging.info('Light turned on: %s', blinkTime)
    timeToEnd = blinkTime + timedelta(seconds=10)  # 10 seconds timeout to wait for light to turn off (so it blinked)
    while (datetime.now() < timeToEnd):
        led = LIGHT_READER.isLightOn()
        if not led:
            logging.info('Light turned off, so it blinked')
            QUEUE.put_nowait(blinkTime)
            QUEUE_IST.put_nowait(blinkTime)
            # If queue for instant has more than 2 blink times, remove the oldest (third)
            if (QUEUE_IST.qsize() > 2):
                QUEUE_IST.get()  # remove oldest (FIFO)
            return
    logging.error('Light did not turn off after 10 seconds')


def sendMail(wattProdotti):
    if (wattProdotti != 0):
        statusForm = subprocess.call(
            'sed s/NNN/'+str(wattProdotti)+'/ < '+HOME+'/PhotoBerry/mail/form > '+HOME+'/PhotoBerry/mail/final',
            shell=True,
        )
        statusMail = subprocess.call('ssmtp '+EMAIL+' < '+HOME+'/PhotoBerry/mail/final', shell=True)
    else:
        statusForm = 0  # no error
        statusMail = subprocess.call('ssmtp '+EMAIL+' < '+HOME+'/PhotoBerry/mail/errore', shell=True)
    return 2*statusForm + statusMail


def setup():
    global HTTPD, LIGHT_READER, DB_MANAGER
    logging.basicConfig(level=LOGGING_LEVEL, format=LOGGING_FORMAT, datefmt=LOGGING_DATE_FORMAT)
    HTTPD = HTTPServer(RequestHandler.address, RequestHandler)
    if not TEST:
        import db_manager
        from light_reader import LightReader
        LIGHT_READER = LightReader(CHANNEL)
        DB_MANAGER = db_manager
    else:
        # logging.debug('sleep(secondsUntilNext5min())')
        # sleep(secondsUntilNext5min())
        import testing.db_manager_mock
        from testing.light_reader_mock import LightReaderMock
        LIGHT_READER = LightReaderMock(CHANNEL)
        DB_MANAGER = testing.db_manager_mock


def run():
    try:
        LIGHT_READER.addCallbackLightOn(readLED, BOUNCETIME)
        threadInstant = Thread(target=instantServer)
        threadInstant.start()
        insertValues()
    except KeyboardInterrupt:
        logging.info('keyboard interrupt')
    finally:
        LIGHT_READER.cleanup()
        HTTPD.shutdown()  # Kills threadInstant


def main():
    setup()
    run()


if __name__ == '__main__':
    main()
