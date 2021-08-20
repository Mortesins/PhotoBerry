#!/usr/bin/env python
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
    Legge la lucetta del contatore dei fotovoltaici e crea un database
    VERSION : 4.4 (RPi.GPIO v0.5.8 required)
        -4 thread:
            -main: manageGPIO
                -insertValues (daemon of manageGPIO)
                -readLED (run on event detect)
            -instant: HTTPD
        -channel 16
        -queue empty exception
        -mail sempre global parameter
        -importabile così si può usare updateDatabase nel webServer
        BUG FIX: global SPENTO in do_get
"""
import logging
import subprocess
from datetime import datetime, timedelta
from threading import Event, Lock, Thread
from time import sleep

from queue import Empty, Queue
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from db_manager import updateDatabase, inserisciDatabase


LOGGING_LEVEL = logging.INFO
LOGGING_FORMAT = '[%(levelname)s %(asctime)s] %(message)s'
LOGGING_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
HOME = '/home/pi'
EMAIL = 'axelbernardinis@gmail.com'
MAILSEMPRE = True

CHANNEL = 16 #GPIO pin for input signal
BOUNCETIME = 20#50#500

QUEUE = Queue()
SPENTO = Event()
LOCK_SPENTO = Lock()

QUEUE_IST = Queue()
HTTPD = None  # Server object as global so I can stop it
ORAULTLAMP = datetime(1970,1,1) # ora ultimo lampeggio per la potenza istantanea, senza lock perchè tanto unico thread


class RequestHandler (BaseHTTPRequestHandler):
    port = 8001
    address = ('', port)
    def do_GET(self):
        global QUEUE_IST, ORAULTLAMP, LOCK_SPENTO
        LOCK_SPENTO.acquire()
        spento = SPENTO.isSet()
        LOCK_SPENTO.release()
        potenza = 0
        if (spento):
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
                        t2 = QUEUE_IST.get(timeout=360) # sarebbe 10 watt allora impianto spento
                    else: # non ha gia lampeggiato
                        t1 = QUEUE_IST.get(timeout=360) # sarebbe 10 watt allora impianto spento
                        t2 = QUEUE_IST.get(timeout=360) # molto improbabile
                except Empty:
                    logging.debug('Timeout, empty queue')
                    potenza = -1

        if (potenza != -1):
            timeDifference = t2 - t1
            potenza = 3600/( timeDifference.seconds + timeDifference.microseconds*0.000001 ) # microseconds 10^-6
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
            self.wfile.write(str(parameters['callback'][0]) + '({"potenza":'+str(potenza)+'});')
        except KeyError:
            self.wfile.write('potenza({"potenza":'+str(potenza)+'});')


def instantServer():
    logging.info('Starting server')
    HTTPD.serve_forever()
    logging.info('Server closed')


def insertValues(metaGiornata=False):
    global QUEUE, SPENTO, LOCK_SPENTO
    logging.info('insertValues')
    if (not metaGiornata):
    # inserisci singolo
        logging.info("inserimento singolo perche' e' appena partito")
        inserimento = 'insert into potenza(GIORNO, ORA, WATT, PICCO_WATT, PICCO_ORA) values (curdate(), curtime(), 1, 0, curtime())'
        inserisciDatabase(inserimento)
    # sleep until 5 minuti 'puliti'
        logging.info('First run, extra sleep. insert values: ' + str(datetime.now()))
        sleep(secondsUntilNext5min())

# sleep until 5 minuti 'puliti'
    logging.info('insert values: ' + str(datetime.now()))
    #sleep(5) # per non beccare lo stesso 5 min
    sleep(secondsUntilNext5min())
    oraInserimento = datetime.now()
    logging.info('insert values: ' + str(oraInserimento))
    oraInserimento = oraInserimento + timedelta(seconds=1) # per essere sicuro di avere i 5 minuti e non 4 minuti e 99
    oraInserimento = oraInserimento.replace(second = 0,microsecond = 0) # per avere database pulito

    LOCK_SPENTO.acquire()
    spento = SPENTO.isSet() # variabile locale
    LOCK_SPENTO.release()
    logging.info('Spento: '+str(spento))

    while (not spento):
    #insert values
    #dalla queue leggi (watt, maxPotenza, oraMax, oraUltLamp)
        logging.info("se l'impianto non e' spento")
        oraLampeggi = list()
        while (not QUEUE.empty()):
            oraLampeggi.append(QUEUE.get_nowait())
        watt = len(oraLampeggi)
        if (watt != 0):
            oraUltLamp = oraLampeggi[len(oraLampeggi)-1]
            maxPotenza = 0
            indexMaxPotenza = 0
            for i in range(1,len(oraLampeggi)):
                timeDifference = (oraLampeggi[i] - oraLampeggi[i-1]) # differenza tra i due lampeggi, <type timedelta>
                potenzaIstantanea = 3600/( timeDifference.seconds + timeDifference.microseconds*0.000001 ) # microseconds 10^-6
                if (potenzaIstantanea > maxPotenza):
                    maxPotenza = potenzaIstantanea
                    indexMaxPotenza = i
            oraMax = oraLampeggi[indexMaxPotenza]
            if (watt == 1 or watt == 2):
                inserimento = "insert into potenza(GIORNO, ORA, WATT, PICCO_WATT, PICCO_ORA) values (curdate(),'%s', %d, %d, '%s')" % (oraUltLamp.strftime('%H:%M:%S'), watt, round(maxPotenza), oraMax.strftime('%H:%M:%S')) # per avere l'ora di fine giornata
            else:
                inserimento = "insert into potenza(GIORNO, ORA, WATT, PICCO_WATT, PICCO_ORA) values (curdate(),'%s', %d, %d, '%s')" % (oraInserimento.strftime('%H:%M:%S'), watt, round(maxPotenza), oraMax.strftime('%H:%M:%S'))
            logging.info('inserisco')
            inserisciDatabase(inserimento)
    # sleep until 5 min
        logging.info('aspetto i prossimi 5 minuti')
        #sleep(5) # per non beccare gli stessi 5 min
        sleep(secondsUntilNext5min())
        oraInserimento = datetime.now()
        logging.info('insert values: ' + str(oraInserimento))
        oraInserimento = oraInserimento + timedelta(seconds=1) # per essere sicuro di avere i 5 minuti e non 4 minuti e 99
        oraInserimento = oraInserimento.replace(second = 0,microsecond = 0) # per avere database pulito
        logging.info("vedo se l'impianto e' spento")
        LOCK_SPENTO.acquire()
        spento = SPENTO.isSet() # variabile locale
        LOCK_SPENTO.release()

    logging.info('Uscito dal while, impianto spento, esco dal thread')
    return


def secondsUntilNext5min():
    oraWakeUp = datetime.now() + timedelta(seconds = 5) # aggiungo secondi per evitare di chimare stesso 5 min
    # ESEMPIO:
    # ora = 14:52:00.0 mi darà oraWakeUp = 14:55:00.0 ma poi io farò sleep dei secondi di differenza tra oraWakeUp e adesso, quindi trascuro i microsecondi
    # quindi quando mi risveglierò, avendo trascurato i microsecondi non saranno le 14:55:00.0 ma tipo 14:54:59.45
    # quindi se la funzione (insertValues) dura tipo 200 ms, avrò come 'ora inizio' 14:54:59.65 e quindi avrei come wakeup di nuovo 14:55:00.0
    # per evitare questo, anche se viene di nuovo chiamata alle 14:54:59.65, aggiungo 5 secondi così sono sicuro di cadere nella prossima fascia
    secondsToAdd = (4 - oraWakeUp.minute % 5) * 60 + 60 - oraWakeUp.second
    oraWakeUp = oraWakeUp + timedelta(seconds = secondsToAdd)
    oraWakeUp = oraWakeUp.replace(microsecond = 0) # azzero i microsecondi
    return (oraWakeUp - datetime.now()).seconds


def readLED(channel): # parametro voluto da GPIO
    global QUEUE,QUEUE_IST,LOCK_SPENTO,SPENTO
    oraLampeggio = datetime.now()
    logging.info('ReadLED: accesa la luce '+str(oraLampeggio))
    timeToEnd = oraLampeggio + timedelta(seconds=10)
# while fino a ora lampeggio + 1 secondo (se gira per più di 10 secondi allora la luce è accesa per un secondo di fila e quindi l'impianto è spento
    while (datetime.now() < timeToEnd):
        led = not bool(GPIO.input(CHANNEL)) # NOT perchè il circuito è tale da avere voltaggio basso per luce accesa
    # se LED spento
        if (led == False): # perchè è più semplice da leggere, spegnendosi significa che ha lampeggiato
        # inserisco l'ora nella QUEUE
            logging.info('spento quindi ha lampeggiato')
            QUEUE.put_nowait(oraLampeggio)
            QUEUE_IST.put_nowait(oraLampeggio)
        # se la queue istantanea ha più di due lampeggi elimino il terzo più vecchio
            if (QUEUE_IST.qsize() > 2):
                QUEUE_IST.get() # elimino il terzo più vecchio (FIFO)
            return
# se esco dal ciclo allora vuol dire che per un secondo la luce era fissa accesa
    logging.info('luce rimasta accesa per un secondo, quindi impianto spento')
    LOCK_SPENTO.acquire()
    SPENTO.set()
    LOCK_SPENTO.release()
    logging.info('esco impianto spento')
    return


def manageGPIO(mailSempre=False):
    try:
        global CHANNEL,BOUNCETIME
        logging.info('manage gpio')
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(CHANNEL, GPIO.IN) # ingresso fototransistor
    #Impianto acceso?
        led1 = not bool(GPIO.input(CHANNEL)) #NOT perchè il circuito è tale da avere voltaggio basso per luce accesa: acceso -> false
        logging.info('LED: '+str(led1))
        sleep(1)
        led2 = not bool(GPIO.input(CHANNEL))
        logging.info('LED: '+str(led2))

        if (led1 and led2): #se luce accesa significa impianto SPENTO
            logging.info('Spento')
            LOCK_SPENTO.acquire()
            SPENTO.set() #= TRUE
            LOCK_SPENTO.release()
        else: #luce spenta, quindi impianto ACCESO
            logging.info('Acceso')
            LOCK_SPENTO.acquire()
            SPENTO.clear() #= FALSE
            LOCK_SPENTO.release()
        #setup event detect
            logging.info('add event')
            GPIO.add_event_detect(CHANNEL, GPIO.FALLING, callback=readLED, bouncetime=BOUNCETIME) #falling significa 0 e quindi il led si accende
        #setup insertValues metaGiornata = True
            logging.info('faccio partire thread insert values')
            threadInsertValues = Thread(target=insertValues,args=(True,))
            threadInsertValues.daemon = True #così muore assieme a manageGPIO
            threadInsertValues.start()
        #sleep until spento
            logging.info("aspetto che si spenga l'impianto")
            SPENTO.wait() #sfrutto l'oggetto EVENT
        #SPENTO
            logging.info('SPENTO: sleep(3)')
            sleep(3) # aspetto che esca da ReadLED
            logging.info('tolgo interrupt')
            ## SINCRONIZZARE INSERT VALUES ???
            GPIO.remove_event_detect(CHANNEL)
            logging.info('chiama funzione serale')
            wattProdotti = updateDatabase()
            logging.info('Prodotti: '+str(wattProdotti))
            if mailSempre:
                mail = inviaMail(wattProdotti)
                if (mail != 0):
                    logging.info('Errore: Mail NON inviata')
                else:
                    logging.info('Mail inviata')
            elif (wattProdotti == 0):
                mail = inviaMail(wattProdotti)
                if (mail != 0):
                    logging.info('Errore: Mail NON inviata')
                else:
                    logging.info('Mail inviata')

    #SPENTO
        while (True):
        #wait for edge
            logging.info('Aspetto che si spenga la luce')
            GPIO.wait_for_edge(CHANNEL, GPIO.RISING) #aspetto che ledN sia True quindi si spenga
        # siamo la mattina dopo ed è ripartito
            #logging.info('remove event detect' # testing, teoricamente non dovrebbe servire E INVECE
            GPIO.remove_event_detect(CHANNEL) # testing, teoricamente non dovrebbe servire E INVECE
        # set ACCESO
            logging.info('Luce spenta, impianto acceso')
            LOCK_SPENTO.acquire()
            SPENTO.clear() # = FALSE (quindi acceso)
            LOCK_SPENTO.release()
        # launch insert values
            logging.info('faccio partire thread insert values')
            threadInsertValues = Thread(target=insertValues)
            threadInsertValues.daemon = True #così muore assieme a manageGPIO
            threadInsertValues.start() # è lui che fa il primo inserimento
        #setup event detect
            logging.info('add event')
            GPIO.add_event_detect(CHANNEL, GPIO.FALLING, callback=readLED, bouncetime=BOUNCETIME) #falling significa 0 e quindi il led si accende
        #sleep until spento
            logging.info("aspetto che si spenga l'impianto")
            SPENTO.wait() #sfrutto l'oggetto EVENT
        #SPENTO
            logging.info('SPENTO: tolgo interrupt')
            sleep(3) # aspetto che esca da ReadLED
            ## SINCRONIZZARE INSERT VALUES???
            GPIO.remove_event_detect(CHANNEL)
            logging.info('chiama funzione serale')
            wattProdotti = updateDatabase()
            logging.info('Prodotti: '+str(wattProdotti))
            if mailSempre:
                mail = inviaMail(wattProdotti)
                if (mail != 0):
                    logging.info('Errore: Mail NON inviata')
                else:
                    logging.info('Mail inviata')
            elif (wattProdotti == 0):
                mail = inviaMail(wattProdotti)
                if (mail != 0):
                    logging.info('Errore: Mail NON inviata')
                else:
                    logging.info('Mail inviata')

    except KeyboardInterrupt:
        logging.info('keyboard interrupt')
        GPIO.cleanup()
        return


def inviaMail(wattProdotti):
    #si potrebbe fare un array di indirizzi mail
    if (wattProdotti != 0):
        statusForm = subprocess.call('sed s/NNN/'+str(wattProdotti)+'/ < '+HOME+'/PhotoBerry/mail/form > '+HOME+'/PhotoBerry/mail/final', shell=True)
        statusMail = subprocess.call('ssmtp '+EMAIL+' < '+HOME+'/PhotoBerry/mail/final', shell=True)
    else:
        statusForm = 0 #nessun errore
        statusMail = subprocess.call('ssmtp '+EMAIL+' < '+HOME+'/PhotoBerry/mail/errore', shell=True)
    return 2*statusForm + statusMail


if __name__ == '__main__':
    logging.basicConfig(level=LOGGING_LEVEL, format=LOGGING_FORMAT, datefmt=LOGGING_DATE_FORMAT)
    HTTPD = HTTPServer(RequestHandler.address, RequestHandler)
    try:
        import RPi.GPIO as GPIO
    except:
        logging.error('No root privileges.\nSkipping RPi.GPIO import')
    try:
        threadInstant = Thread(target=instantServer)
        threadInstant.start()
        manageGPIO(mailSempre=MAILSEMPRE)
    except KeyboardInterrupt:
        logging.info('keyboard interrupt')
        GPIO.cleanup()
        HTTPD.shutdown()  # Kills threadInstant

