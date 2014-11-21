#!/usr/bin/env python

########################################################################
#  Software for collecting data from PV energy meters
#  Copyright (C) 2014 Axel Bernardinis <abernardinis@hotmail.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
########################################################################

"""
I'm sorry but since this version is based on the ENEL energy meter (which is the 
default for Italy) pretty much every comment is in Italian.
 
   Legge la lucetta del contatore dei fotovoltaici e crea un database
   VERSION : 2.1 (RPi.GPIO v0.5.3 required)
      -usare interrupt (RPi.GPIO v0.5.3) al posto del polling
      -eliminare da "fotovoltaico.db" la tabella cumulativo parziale
      -creare "fotovoltaico_parziale.db" per il cumulativo con ultima entry quella parziale
      -corretto errore import multiplo di time
      -inserito cleanup, anche nel caso in cui si abbia interruzione via tastiera
      -updateDatabase, cambia a seconda che venga eseguito da apache
"""

import sqlite3,os 
import random, time
from math import floor
from shutil import copyfile  #for copying files

try:
   import RPi.GPIO as GPIO
except:
   print "No root privileges.\nSkipping RPi.GPIO import"

HOME = "/home/pi"


def readValues():
   """ Legge la luce del contatore
       Chiama insertValues per inserire i dati nel database
   """
   GPIO.setmode(GPIO.BOARD)
   GPIO.setup(16, GPIO.IN) # ingresso fototransistor
   #print time.strftime("%d")
   giorno = time.strftime("%d")
   pulse = False
   try:      
      while (True):
         GPIO.wait_for_edge(16,GPIO.FALLING)      
         while (True):
            ledN = GPIO.input(16) # lo chiamo ledN perche  negato del led: acceso ->false...
            if ledN == True:
               pulse = True
               print "spento"
               break
            if giorno != time.strftime("%d"):
               print giorno
               giorno = time.strftime("%d")
               print "chiama funzione serale"
               updateDatabase("fotovoltaico.db",False)# chiama funzione serale
               #break
         if pulse == True:
            pulse = False
            print "chiamare insertValues"
            insertValues() # chiamo funzione che inserisce i valori
         
         #if giorno != time.strftime("%d"):
            #print giorno
            #giorno = time.strftime("%d")
            #print "chiama funzione serale"
            #updateDatabase("fotovoltaico.db",False)# chiama funzione serale
   except KeyboardInterrupt:  
      GPIO.cleanup()
   GPIO.cleanup()
   return

def setup(filename = "fotovoltaico.db", createDB = True):
   os.chdir(HOME)
   exists = os.path.isdir('Photoberry') ## decidere dove salvare il database
   if (exists):
      print "~/Photoberry directory already exists"
   else:
      os.mkdir('Photoberry')
   os.chdir('Photoberry')
   exists = os.path.isdir('databases')
   if (exists):
      print "~/Photoberry/databases directory already exists"
   else:
      os.mkdir('databases')
   os.chdir('databases')
   if createDB:
      createDatabase(filename)

def createDatabase(filename = "fotovoltaico.db"):
   """ 
       Controlla che non esista gia' il database
       Crea il database con due tabelle:
       lampeggi:
       DATA                ORA               
       (data lampeggio)    (ora lampeggio)   
       cumulativo:   
       DATA    WATT       INIZIO PRODUZIONE  FINE PRODUZIONE  ORA PICCO  WATT PICCO
               (prodotti) (ora inizio)       (ora fine)                  (potenza istantanea di picco [W])      
   """
   os.chdir(HOME)
   if (os.path.isdir('Photoberry/databases')):
      # create database
      os.chdir('Photoberry/databases')      
   else:
      # run setup
      print "~/Photoberry/databases does not exist\nPlease run setup.py (run it as user for best results)"
      while True:
         answer = raw_input("Should I run setup.py which will create the directories (WARNING: if the script has been called a s root it is suggested you quit and run setup.py as user)? (y/N)")
         if (answer.lower() == "y" or answer.lower() == "yes"):
            setup(filename,False)
            break
         elif (answer.lower() == "n" or answer.lower() == "no"):
            print "no database"            
            return         
         else:
            answer = raw_input("Please answer with 'y' or 'n'")   

   databaseConn = sqlite3.connect(filename)
   c = databaseConn.cursor()
   # Create table
   try:
      c.execute('''CREATE TABLE lampeggi (DATA date, ORA time)''')
   except sqlite3.OperationalError, exception:
      print "Database esiste gia':", exception   
   try:
        c.execute('''CREATE TABLE cumulativo (DATA date, WATT real, INIZIO_PRODUZIONE time, FINE_PRODUZIONE time, ORA_PICCO time, WATT_PICCO real)''')  
   except sqlite3.OperationalError, exception:
      print "Database esiste gia':", exception   
   #####
   #c.execute("INSERT INTO cumulativo VALUES('2010-05-13',5.64,'15:12:04','16:34:12','15:35:00',2512.45)")
   #####
   databaseConn.commit()
   databaseConn.close()


def insertValues(filename = "fotovoltaico.db"):
   """
       DATA                ORA
       (data lampeggio)    (ora lampeggio)
   """
   date = getDate()
   time = getTime()
   values = [date,time]

   os.chdir(HOME)
   if (os.path.isdir('Photoberry/databases')):
      # create database
      os.chdir('Photoberry/databases')      
   else:
      # run setup
      print "~/Photoberry/databases does not exist\nPlease run setup.py (for best results run it as user)"
      while True:
         answer = raw_input("Should I run setup.py which will create the directories (WARNING: if the script has been called a s root it is suggested you quit and run setup.py as user)? (y/N))")
         if (answer.lower() == "y" or answer.lower() == "yes"):
            setup(filename)
            break
         elif (answer.lower() == "n" or answer.lower() == "no"):
            print "no database"            
            return         
         else:
            answer = raw_input("Please answer with 'y' or 'n'")

   databaseConn = sqlite3.connect(filename)   
   c = databaseConn.cursor()
   # Inserisci in table lampeggi
   while True:
      try:
         c.execute("INSERT INTO lampeggi VALUES(?,?)", values)
         break
      except sqlite3.OperationalError, exception:
         print "Tabella non esiste:", exception
         while True:
            answer = raw_input("Should I run createDatabase which will create the database (WARNING: if the script has been called a s root it is suggested you quit and run setup.py which will automatically call createDatabase as user)? (y/N)")
            if (answer.lower() == "y" or answer.lower() == "yes"):
               createDatabase(filename)
               break
            elif (answer.lower() == "n" or answer.lower() == "no"):
               break
            else:
               answer = raw_input("Please answer with 'y' or 'n'")
      if (answer.lower() == "n" or answer.lower() == "no"):
         break

   databaseConn.commit()
   databaseConn.close()

def updateDatabase(filename = "fotovoltaico_parziale.db", parziale = True, apache=False):
   """
       Aggiunge una entry nel database cumulativo usando i dati del database di base 
       parziale e' un flag che e' vero se la funzione e' chiamata esternamente e quindi i valori potrebbero non essere completi per la giornata, mentre e' falso se la funzione viene chiamata internamente a readValues.py e quindi i dati della giornata sono completi
       Nel caso in cui sia parziale, si copia "fotovoltaico.db" in "fotovoltaico_parziale.db" e si inserisce la nuova entry in quest'ultimo
       Apache, serve per sapere chi la esegue. Se apache, metto cumulativo in apache, se no dentro database
   """
   # aprire database
   os.chdir(HOME)
   if (os.path.isdir('Photoberry/databases')):
      # create database
      os.chdir('Photoberry/databases')      
   else:
      # run setup
      print "Something went wrong, ~/Photoberry/databases does not exist\nPlease run setup.py (for best results run it as user)"
      return 1
   if (parziale):
      if (apache):
         #table cumulativi
         copyfile(HOME+"/Photoberry/databases/fotovoltaico.db",HOME+"/Photoberry/databases/apache/fotovoltaico_parziale.db")
         os.chdir("apache")
         if (filename == "fotovoltaico.db"):
            print "Non si puo' inserire valori parziali nel database 'fotovoltaico.db'\nExiting"
            return 1
      else:
         #table cumulativi
         copyfile(HOME+"/Photoberry/databases/fotovoltaico.db",HOME+"/Photoberry/databases/fotovoltaico_parziale.db")
         if (filename == "fotovoltaico.db"):
            print "Non si puo' inserire valori parziali nel database 'fotovoltaico.db'\nExiting"
            return 1   
   databaseConn = sqlite3.connect(filename)
   c = databaseConn.cursor()
   # creare ed assegnare: data, watt, inzio, fine, picco_ora, picco_watt
   data = "2013-08-05" #data
   watt = 19.82 # float [Wh]
   inizio = "07:04:02:333" # ora
   fine = "20:02:45:977" # ora
   picco_ora = "13:52:30:232" # ora
   picco_watt = 2763.3 # float [W]
   # calcolo variabili
      # DATA: prendo la data dell'ultimo lampeggio

   c.execute("SELECT data FROM lampeggi ORDER BY ROWID DESC LIMIT 1") #seleziona la data ultima entry
   try:
      dataUltimoLampeggio = (c.fetchone())[0]
   except TypeError, e:
      print "Empty database, no update done"
      return 1

   print dataUltimoLampeggio
   data = dataUltimoLampeggio
      #WATT
      #conto il numero di entries con la dataUltimoLampeggio
      #watt = conto
   c.execute("SELECT ora FROM lampeggi WHERE data = '%s'" % data)
   lampeggiList = c.fetchall()
   lampeggi = []
   for i in range(len(lampeggiList)):
      lampeggi.append((lampeggiList[i])[0])
   watt = len(lampeggi) / 1000.0
   print watt
      #INIZIO
      #inizio = ora primo lampeggio con data=dataUltimoLampeggio
   inizio = lampeggi[0]
      #FINE
      #fine = ora dell'ultimo lampeggio
   fine = lampeggi[len(lampeggi)-1]
   print inizio,fine
      #PICCO
      #picco_ora = ora primo lampeggio
   picco_ora = lampeggi[0]
      #picco_watt = 3600 / toSeconds((ora secondo lampeggio) - (ora primo lampeggio))
           ## POTENZA = ENERGIA / TEMPO quindi ma tempo e' il tempo per produrre 1Wh cioe' 3600Ws 
           ## quindi POTENZA [W] = 3600 Ws / TEMPO produzione 3600Ws [s]
   try:
      picco_watt = 3600.0 / timeDifference(lampeggi[1],lampeggi[0])
   except ZeroDivisionError, e:
      print "Skipping because time difference = 0:", e
      # for all entries - 1  perche' nel calcolo si usa il lampeggio successivo
   for i in range(len(lampeggi)-1):
       try:
         wattTemp = 3600 / timeDifference(lampeggi[i+1],lampeggi[i])
       except ZeroDivisionError, e:
         print "Skipping because time difference = 0:", e
       if (wattTemp > picco_watt):
         picco_watt = wattTemp
         picco_ora = lampeggi[i]
   values = [data,watt,inizio,fine,picco_ora,picco_watt]
   print values
   try:
      c.execute("INSERT INTO cumulativo VALUES(?,?,?,?,?,?)", values)
   except sqlite3.OperationalError, exception:
      print "Something went wrong, table does not exist:", exception

   databaseConn.commit()
   databaseConn.close()

def istantaneo():
   # aprire database
   os.chdir(HOME)
   if (os.path.isdir('Photoberry/databases')):
      # create database
      os.chdir('Photoberry/databases')      
   else:
      # run setup
      print "Something went wrong, ~/Photoberry/databases does not exist\nPlease run setup.py (for best results run it as user)"
   databaseConn = sqlite3.connect("fotovoltaico.db")
   c = databaseConn.cursor()
   # ora ultimo e penultimo lampeggio
   c.execute("SELECT ora FROM lampeggi ORDER BY ROWID DESC LIMIT 2") #seleziona ora ultime due lampeggi
   oraUltimo = (c.fetchone())[0]
   oraPenUltimo = (c.fetchone())[0]
   #print oraPenUltimo, oraUltimo
   #controllo che non sia spento
   currentTime = getTime()   
   if (timeDifference(currentTime,oraUltimo) < 360):   
      potenza = 3600.0 / timeDifference(oraUltimo,oraPenUltimo)
      #print oraPenUltimo, oraUltimo, potenza
   else:
      potenza = 0
      #print "Impianto spento"
   databaseConn.commit()
   databaseConn.close()
   return potenza

def cleanUpDatabase():
   """
   questa funziona deve ripulire la tabella dei lampeggi ed inserire nella tabella Giornaliero il numero di conteggi per ogni singola ora
   """
   return

def timeDifference(tmax,tmin):
   timediff = 0
   hour1 = int(tmin[0:2])
   minutes1 = int(tmin[3:5])
   seconds1 = int(tmin[6:8])
   milli1 = int(tmin[9:12])
   hour2 = int(tmax[0:2])
   minutes2 = int(tmax[3:5])
   seconds2 = int(tmax[6:8])
   milli2 = int(tmax[9:12])

   timediff = (milli2 - milli1) / 1000.0
   if (timediff < 0):
      timediff += 1
      seconds2 -= 1
   timediff += seconds2 - seconds1
   if (timediff < 0):
      timediff += 60
      minutes2 -= 1
   a = minutes2 - minutes1
   if (a < 0):
      a += 60
      hour2 -= 1
   timediff += a * 60
   a = hour2 - hour1
   timediff += a * 3600
   return timediff

def getDate():
   """
       prende la data del lampeggio dal raspberry
   """
   fileOutputComando = os.popen("date +%F") # yyyy-mm-dd
   date = fileOutputComando.readline()
   i = len(date)
   date = date[0:i-1]
   return date

def getTime():
   """
       prende l'ora del lampeggio
       Versione senza PIC: legge l'ora del sistema linux del raspberry
       Versione con PIC: legge l'ora del lampeggio salvata sul PIC
   """
   # versione senza PIC
   fileOutputComando = os.popen("date +%T:%N") # hh-mm-ss-mmm   
   # elimino \n   
   time = fileOutputComando.readline()
   time = time[0:12]
   return time

###### CHECKING FUNCTIONS
"""
def randomDatabase(num):
   createDatabase("fotovoltaico_random.db")
   sleepTime = []
   sleepTime = randomSleepTimes(num)
   i = 0
   length = len(sleepTime)
   date = getDate()
   time = getTime()
   values = [date,time]

   os.chdir(HOME) #######################
   os.chdir('Photoberry/databases')
   databaseConn = sqlite3.connect("fotovoltaico_random.db")
   c = databaseConn.cursor()
   # Inserisci in table lampeggi
   for i in range(num):
      try:
         c.execute("INSERT INTO lampeggi VALUES(?,?)", values)
      except sqlite3.OperationalError, exception:
        print "Tabella non esiste:", exception
      hour = int(time[0:2])
      minutes = int(time[3:5])
      seconds = int(time[6:8])
         seconds += 1 ### ERRORE
      milli = int(time[9:12])
      milli += int((sleepTime[i] - floor(sleepTime[i])) * 1000)
      while (milli >= 1000):
         milli -= 1000
      while (seconds >= 60):
         seconds -= 60
         minutes += 1
      while (minutes > 59):
         minutes -= 60
         hour += 1
      if (minutes < 10):
         if (seconds < 10):
            time = str(hour)+":0"+str(minutes)+":0"+str(seconds)+":"+str(milli)  
         else:
            time = str(hour)+":0"+str(minutes)+":"+str(seconds)+":"+str(milli)   
      else:
         if (seconds < 10):
            time = str(hour)+":"+str(minutes)+":0"+str(seconds)+":"+str(milli)   
         else:
            time = str(hour)+":"+str(minutes)+":"+str(seconds)+":"+str(milli)   
            
      print hour, minutes, seconds, milli, "||", 
      values[1] = time   
   databaseConn.commit()
   databaseConn.close()
 
def randomSleepTimes(num):
   numbers1 = []
   numbers2 = []
   numbers3 = []
   i = 0
   for i in range(num/2):
      numbers1.append(round(random.random()*120,3))
      numbers2.append(round(random.random()*120,3))
   numbers1 = sorted(numbers1)
   numbers2 = sorted(numbers2)
   numbers3.extend(numbers2)
   i = 0
   length = len(numbers3)
   for i in range(num/2):
      numbers3[i] = numbers2[length-1-i]
   sleepTime = numbers3 + numbers1
   print sleepTime
   return sleepTime
"""
############

if __name__ == '__main__':
   readValues()
   
#### MAYBE
# Creare classe DATE e TIME e costruttori a partire da stringa
# metodi somma sotrazione etc.
####
