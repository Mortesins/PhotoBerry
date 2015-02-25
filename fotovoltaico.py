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
   VERSION : 4.2 (RPi.GPIO v0.5.8 required)
      -4 thread:
         -main: manageGPIO
            -insertValues (daemon of manageGPIO)
            -readLED (run on event detect)
         -instantPower: HTTPD
      -channel 16
"""
import MySQLdb
from threading import Thread,Event,Lock
from Queue import Queue
from datetime import datetime,timedelta
from time import sleep 
import subprocess

##### INSTANT
from urlparse import urlparse, parse_qs
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
#####

""" 
   Crea il database con tre tabelle:
   potenza:
      GIORNO                ORA                WATT        PICCO_WATT     PICCO_ORA 
      (data inserimento)  (ora inserimento)  (prodotti)  (picco [W])    (ora watt picco)
   giornaliero:   
      GIORNO        WATT    PICCO_WATT    PICCO_ORA  INIZIO (produzione)  FINE (produzione)  
      (prodotti)     
"""

class RequestHandler (BaseHTTPRequestHandler):
   port = 8001
   address = ('',port)
   def do_GET(self):
      pass

HOME = ""
USER = ""
PASSWD = ""
DATABASE = "fotov"
EMAIL = ""

CHANNEL = 16 #GPIO pin for input signal
BOUNCETIME = 20#50#500

QUEUE = Queue()
SPENTO = Event()
LOCK_SPENTO = Lock()

QUEUE_IST = Queue()
HTTPD = HTTPServer(RequestHandler.address,RequestHandler) # globale così lo posso fermare
ORAULTLAMP = datetime(1970,1,1) # ora ultimo lampeggio per la potenza istantanea, senza lock perchè tanto unico thread

#### INSTANT
def RequestHandler_do_GET(self):
   global QUEUE_IST, ORAULTLAMP
   LOCK_SPENTO.acquire()
   spento = SPENTO.isSet()
   LOCK_SPENTO.release()
   potenza = 0
   if (spento):
      potenza = -1
   else:
      if (QUEUE_IST.qsize() == 2):
         print "Queue size == 2"
         t1 = QUEUE_IST.get() # sono sicuro ci sono quindi niente timeout
         t2 = QUEUE_IST.get() # sono sicuro ci sono quindi niente timeout
      else:
         print "Queue size != 2"
         try:
            giaLampeggiato = (ORAULTLAMP.date() == datetime.now().date()) # controlla la data
         except NameError: # cioe' ORAULTLAMP not defined
            print "NameError"
            giaLampeggiato = False
         print "Gia lampeggiato: " + str(giaLampeggiato)
         try:
            if (giaLampeggiato):
               t1 = ORAULTLAMP
               t2 = QUEUE_IST.get(timeout=360) # sarebbe 10 watt allora impianto spento
            else: # non ha gia lampeggiato
               t1 = QUEUE_IST.get(timeout=360) # sarebbe 10 watt allora impianto spento
               t2 = QUEUE_IST.get(timeout=360) # molto improbabile
         except Empty:
            print "Timeout, empty queue"
            potenza = -1

   if (potenza != -1):
      timeDifference = t2 - t1 
      potenza = 3600/( timeDifference.seconds + timeDifference.microseconds*0.000001 ) # microseconds 10^-6
      ORAULTLAMP = t2
      print "Potenza: "+str(potenza)+" OraUltimoLampeggio: " + str(ORAULTLAMP)
   potenza = int(round(potenza))
   #potenza = QUEUE_IST.get()
   parameters = parse_qs(urlparse(self.path).query)
   # mi restituisce i parametri GET come dizionario
      # {'callback':['nomefunzione']}
   self.send_response(200)
   self.send_header('Content-type','application/json')
   self.end_headers()
   # Send the html message
   #Per far funzionare JSONP devo restituire una roba tipo
      # nomefunzione({JSONOBJECT});
      # nomefunzione deve essere il parametro callback="stringanomefuzione"
   try:
      self.wfile.write( str(parameters['callback'][0]) + '({"potenza":'+str(potenza)+'});' )
   except KeyError:
      #self.wfile.write("errore({'errore':'errore'});")
      self.wfile.write( 'potenza({"potenza":'+str(potenza)+'});' )
   return 
RequestHandler.do_GET = RequestHandler_do_GET #lo asseggno alla classe
####

def insertValues(metaGiornata=False):
   global QUEUE, SPENTO, LOCK_SPENTO
   print "insertValues"
   if (not metaGiornata):
   # inserisci singolo
      print "inserimento singolo perche' e' appena partito"
      inserimento = "insert into potenza(GIORNO, ORA, WATT, PICCO_WATT, PICCO_ORA) values (curdate(), curtime(), 1, 0, curtime())"
      inserisciDatabase(inserimento)
   # sleep until 5 minuti "puliti"
      print "First run, extra sleep. insert values: " + str(datetime.now())
      sleep(secondsUntilNext5min())

# sleep until 5 minuti "puliti"   
   print "insert values: " + str(datetime.now())
   #sleep(5) # per non beccare lo stesso 5 min
   sleep(secondsUntilNext5min())
   oraInserimento = datetime.now()   
   print "insert values: " + str(oraInserimento)
   oraInserimento = oraInserimento + timedelta(seconds=1) # per essere sicuro di avere i 5 minuti e non 4 minuti e 99
   oraInserimento = oraInserimento.replace(second = 0,microsecond = 0) # per avere database pulito
   
   LOCK_SPENTO.acquire()
   spento = SPENTO.isSet() # variabile locale
   LOCK_SPENTO.release()
   print "Spento: "+str(spento)
   
   while (not spento):
   #insert values
   #dalla queue leggi (watt, maxPotenza, oraMax, oraUltLamp)
      print "se l'impianto non e' spento"
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
            inserimento = "insert into potenza(GIORNO, ORA, WATT, PICCO_WATT, PICCO_ORA) values (curdate(),'%s', %d, %d, '%s')" % (oraUltLamp.strftime("%H:%M:%S"), watt, round(maxPotenza), oraMax.strftime("%H:%M:%S")) # per avere l'ora di fine giornata
         else:
            inserimento = "insert into potenza(GIORNO, ORA, WATT, PICCO_WATT, PICCO_ORA) values (curdate(),'%s', %d, %d, '%s')" % (oraInserimento.strftime("%H:%M:%S"), watt, round(maxPotenza), oraMax.strftime("%H:%M:%S")) 
         print "inserisco"
         inserisciDatabase(inserimento)
   # sleep until 5 min
      print "aspetto i prossimi 5 minuti"
      #sleep(5) # per non beccare gli stessi 5 min
      sleep(secondsUntilNext5min())
      oraInserimento = datetime.now()   
      print "insert values: " + str(oraInserimento)
      oraInserimento = oraInserimento + timedelta(seconds=1) # per essere sicuro di avere i 5 minuti e non 4 minuti e 99
      oraInserimento = oraInserimento.replace(second = 0,microsecond = 0) # per avere database pulito
      print "vedo se l'impianto e' spento"
      LOCK_SPENTO.acquire()
      spento = SPENTO.isSet() # variabile locale
      LOCK_SPENTO.release()
   
   print "Uscito dal while, impianto spento, esco dal thread"
   return

def secondsUntilNext5min():
   oraWakeUp = datetime.now() + timedelta(seconds = 5) # aggiungo secondi per evitare di chimare stesso 5 min
   # ESEMPIO:
   # ora = 14:52:00.0 mi darà oraWakeUp = 14:55:00.0 ma poi io farò sleep dei secondi di differenza tra oraWakeUp e adesso, quindi trascuro i microsecondi
   # quindi quando mi risveglierò, avendo trascurato i microsecondi non saranno le 14:55:00.0 ma tipo 14:54:59.45
   # quindi se la funzione (insertValues) dura tipo 200 ms, avrò come "ora inizio" 14:54:59.65 e quindi avrei come wakeup di nuovo 14:55:00.0
   # per evitare questo, anche se viene di nuovo chiamata alle 14:54:59.65, aggiungo 5 secondi così sono sicuro di cadere nella prossima fascia
   secondsToAdd = (4 - oraWakeUp.minute % 5) * 60 + 60 - oraWakeUp.second
   oraWakeUp = oraWakeUp + timedelta(seconds = secondsToAdd)
   oraWakeUp = oraWakeUp.replace(microsecond = 0) # azzero i microsecondi
   return (oraWakeUp - datetime.now()).seconds
   
def readLED(channel): # parametro voluto da GPIO
   global QUEUE,QUEUE_IST,LOCK_SPENTO,SPENTO
   oraLampeggio = datetime.now()
   print "ReadLED: accesa la luce "+str(oraLampeggio)
   timeToEnd = oraLampeggio + timedelta(seconds=1)
# while fino a ora lampeggio + 1 secondo (se gira per più di un secondo allora la luce è accesa per un secondo di fila e quindi l'impianto è spento
   while (datetime.now() < timeToEnd):
      led = not bool(GPIO.input(CHANNEL)) # NOT perchè il circuito è tale da avere voltaggio basso per luce accesa
   # se LED spento
      if (led == False): # perchè è più semplice da leggere, spegnendosi significa che ha lampeggiato
      # inserisco l'ora nella QUEUE
         print "spento quindi ha lampeggiato"
         QUEUE.put_nowait(oraLampeggio)
         QUEUE_IST.put_nowait(oraLampeggio)
      # se la queue istantanea ha più di due lampeggi elimino il terzo più vecchio
         if (QUEUE_IST.qsize() > 2): 
            QUEUE_IST.get() # elimino il terzo più vecchio (FIFO)
         return
# se esco dal ciclo allora vuol dire che per un secondo la luce era fissa accesa
   print "luce rimasta accesa per un secondo, quindi impianto spento"
   LOCK_SPENTO.acquire()
   SPENTO.set()
   LOCK_SPENTO.release()
   print "esco impianto spento"
   return

def manageGPIO(mailSempre = False):
   try:
      global CHANNEL,BOUNCETIME
      print "manage gpio"
      GPIO.setmode(GPIO.BOARD)
      GPIO.setup(CHANNEL, GPIO.IN) # ingresso fototransistor
   #Impianto acceso?
      led1 = not bool(GPIO.input(CHANNEL)) #NOT perchè il circuito è tale da avere voltaggio basso per luce accesa: acceso -> false
      print "LED: "+str(led1)
      sleep(1)
      led2 = not bool(GPIO.input(CHANNEL))
      print "LED: "+str(led2)
      
      if (led1 and led2): #se luce accesa significa impianto SPENTO
         print "Spento"
         LOCK_SPENTO.acquire()
         SPENTO.set() #= TRUE
         LOCK_SPENTO.release()
      else: #luce spenta, quindi impianto ACCESO
         print "Acceso"
         LOCK_SPENTO.acquire()
         SPENTO.clear() #= FALSE
         LOCK_SPENTO.release()
      #setup event detect
         print "add event"
         GPIO.add_event_detect(CHANNEL, GPIO.FALLING, callback=readLED, bouncetime=BOUNCETIME) #falling significa 0 e quindi il led si accende
      #setup insertValues metaGiornata = True
         print "faccio partire thread insert values"
         threadInsertValues = Thread(target=insertValues,args=(True,)) 
         threadInsertValues.daemon = True #così muore assieme a manageGPIO
         threadInsertValues.start()         
      #sleep until spento
         print "aspetto che si spenga l'impianto"
         SPENTO.wait() #sfrutto l'oggetto EVENT
      #SPENTO
         print "SPENTO: sleep(3)"
         sleep(3) # aspetto che esca da ReadLED
         print "tolgo interrupt"
         ## SINCRONIZZARE INSERT VALUES ???
         GPIO.remove_event_detect(CHANNEL)
         print "chiama funzione serale"
         wattProdotti = updateDatabase()
         print "Prodotti: "+str(wattProdotti)
         if mailSempre:
            mail = inviaMail(wattProdotti)
            if (mail != 0):
               print "Errore: Mail NON inviata"
            else:
               print "Mail inviata"
         elif (wattProdotti == 0):
            mail = inviaMail(wattProdotti)
            if (mail != 0):
               print "Errore: Mail NON inviata"
            else:
               print "Mail inviata"

   #SPENTO
      while (True):
      #wait for edge
         print "Aspetto che si spenga la luce"
         GPIO.wait_for_edge(CHANNEL, GPIO.RISING) #aspetto che ledN sia True quindi si spenga
      # siamo la mattina dopo ed è ripartito
         #print "remove event detect" # testing, teoricamente non dovrebbe servire E INVECE
         GPIO.remove_event_detect(CHANNEL) # testing, teoricamente non dovrebbe servire E INVECE
      # set ACCESO
         print "Luce spenta, impianto acceso"
         LOCK_SPENTO.acquire()
         SPENTO.clear() # = FALSE (quindi acceso)
         LOCK_SPENTO.release()
      # launch insert values
         print "faccio partire thread insert values"
         threadInsertValues = Thread(target=insertValues)
         threadInsertValues.daemon = True #così muore assieme a manageGPIO
         threadInsertValues.start() # è lui che fa il primo inserimento
      #setup event detect
         print "add event"
         GPIO.add_event_detect(CHANNEL, GPIO.FALLING, callback=readLED, bouncetime=BOUNCETIME) #falling significa 0 e quindi il led si accende
      #sleep until spento
         print "aspetto che si spenga l'impianto"
         SPENTO.wait() #sfrutto l'oggetto EVENT
      #SPENTO
         print "SPENTO: tolgo interrupt"
         sleep(3) # aspetto che esca da ReadLED
         ## SINCRONIZZARE INSERT VALUES???
         GPIO.remove_event_detect(CHANNEL)
         print "chiama funzione serale"
         wattProdotti = updateDatabase()
         print "Prodotti: "+str(wattProdotti)
         if mailSempre:
            mail = inviaMail(wattProdotti)
            if (mail != 0):
               print "Errore: Mail NON inviata"
            else:
               print "Mail inviata"
         elif (wattProdotti == 0):
            mail = inviaMail(wattProdotti)
            if (mail != 0):
               print "Errore: Mail NON inviata"
            else:
               print "Mail inviata"
      
   except KeyboardInterrupt: 
      print "keyboard interrupt"
      GPIO.cleanup()
      return 

def instantPower():
   global HTTPD
   print "Starting server"
   HTTPD.serve_forever()
   print "Server closed"
   return

def updateDatabase():
   """
      Aggiunge una entry nel database giornaliero usando i dati del database di base 
      Pulisce istantaneo
      potenza:
         GIORNO                ORA                WATT        PICCO_WATT     PICCO_ORA 
         (data inserimento)  (ora inserimento)  (prodotti)  (picco [W])    (ora watt picco)
      giornaliero:   
         GIORNO        WATT    PICCO_WATT    PICCO_ORA  INIZIO (produzione)  FINE (produzione)  
         (prodotti)  

   """
   print "updateDatabase"
   db = MySQLdb.connect(host="localhost", user=USER, passwd=PASSWD, db=DATABASE)
   c = db.cursor()
   print "connected"
   
   #### nel caso in cui si spegne a mezza giornata e poi riparte, eliminare quelle vecchie
   c.execute("DELETE FROM giornaliero WHERE giorno=curdate()") # numero entries con il giorno di oggi
   ####  
   
   # creare ed assegnare: data, WATT, inzio, fine, picco_ora, picco_WATT
   data = "2013-08-05" #data
   watt = 0 # float [Wh]
   inizio = "07:04:02:333" # ora
   fine = "20:02:45:977" # ora
   picco_ora = "13:52:30:232" # ora
   picco_watt = 2763.3 # float [W]
   # calcolo variabili
      # DATA: prendo la data dell'ultimo lampeggio

   c.execute("SELECT giorno FROM potenza ORDER BY giorno DESC LIMIT 1") #seleziona la data ultima entry
   try:
      dataUltimoLampeggio = (c.fetchone())[0]
   except TypeError, e:
      print "Empty database, no update done"
      return 1

   print dataUltimoLampeggio
   data = dataUltimoLampeggio
      #INIZIO
      #inizio = ora primo lampeggio con data=dataUltimoLampeggio
   c.execute("SELECT ora FROM potenza WHERE giorno = '%s'" % data)
   entriesList = c.fetchall() 
   # (
   #   (ora,)
   #   (ora,)
   #   (ora,)
   #  )
   inizio = (entriesList[0])[0]
      #FINE
      #fine = ora dell'ultimo lampeggio
   fine = (entriesList[len(entriesList)-1])[0]
   print inizio,fine
 
      #WATT
      #sommo WATT di ogni entry con data = dataUltimoLampeggio
   c.execute("SELECT watt FROM potenza WHERE giorno = '%s'" % data)
   watt = 0
   while (True):
      try:
         wattEntry = (c.fetchone())[0]
         watt += int(wattEntry)
      except TypeError, e:
         break
   print "watt: ",watt
      #PICCO
      #picco_ora = ora primo lampeggio
   c.execute("SELECT picco_watt,picco_ora FROM potenza WHERE giorno = '%s'" % data)
   entriesList = c.fetchall()
   piccoIndex = 0
   i = 1
   while (i < len(entriesList)):
      if (entriesList[i][0] > entriesList[piccoIndex][0]):
         piccoIndex = i
      i+=1
   picco_ora = entriesList[piccoIndex][1]
   picco_watt = entriesList[piccoIndex][0]
   ###
   try:
      c.execute("INSERT INTO giornaliero VALUES('%s','%d','%d','%s','%s','%s')" % (data,watt,picco_watt,picco_ora,inizio,fine))
   except MySQLdb.Error, exception:
      print "Something went wrong:", exception

   db.commit()
   db.close()
   return watt

def maxArray(array):
   maxIndex = 0
   for i in range(1,len(array)):
      if (array[i] > array[maxIndex]):
         maxIndex = i
   return maxIndex
   
def minArray(array):
   minIndex = 0
   for i in range(1,len(array)):
      if (array[i] < array[minIndex]):
         minIndex = i
   return minIndex

def inviaMail(wattProdotti):
   #si potrebbe fare un array di indirizzi mail
   if (wattProdotti != 0):
      statusForm = subprocess.call("sed s/NNN/"+str(wattProdotti)+"/ < "+HOME+"/PhotoBerry/mail/form > "+HOME+"/PhotoBerry/mail/final", shell=True)
      statusMail = subprocess.call("ssmtp "+EMAIL+" < "+HOME+"/PhotoBerry/mail/final", shell=True)
   else:
      statusForm = 0 #nessun errore
      statusMail = subprocess.call("ssmtp "+EMAIL+" < "+HOME+"/PhotoBerry/mail/errore", shell=True)
   return 2*statusForm + statusMail
   
def inserisciDatabase(inserimento):
   db = MySQLdb.connect(host="localhost", user=USER, passwd=PASSWD, db=DATABASE)
   cursore = db.cursor()
   cursore.execute(inserimento)
   db.commit()
   db.close()
   return
   
if __name__ == '__main__':
   try:
      import RPi.GPIO as GPIO
   except:
      print "No root privileges.\nSkipping RPi.GPIO import"
   try:
      threadInstant = Thread(target=instantPower)
      threadInstant.start()
      manageGPIO(mailSempre = True)
   except KeyboardInterrupt:
      print "keyboard interrupt"
      GPIO.cleanup()
      HTTPD.shutdown() #cosi muore thread Instant
      
