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

from flask import Flask,request,jsonify
from datetime import datetime,timedelta
import MySQLdb

#from flask.ext.cors import cross_origin

app = Flask(__name__)
#cors = CORS(app)

HOST = ""
USER = ""
PASSWD = ""

PORT = 

def giorniDelMese(mese,anno):
   giorniMese = (31,28,31,30,31,30,31,31,30,31,30,31)
   if ((anno % 400 == 0 or (anno % 100 != 0 and anno % 4 == 0)) and mese == 2):
      return 29
   else:
      return giorniMese[mese - 1]

@app.route("/potenzaGrafico") # CONTROLLARE MANCANZA PARAMETRI GET?
def potenzaGrafico():
   '''
      devo restituire un dizionario
      {
         "potenze":list
      }
      list = [
                  {"ora":"hh-mm-ss","potenza":watt},
                  {"ora":"hh-mm-ss","potenza":watt},
             ]
   '''
   #fetchone: mi da un tuple con la riga del database
   #fetchall: mi da un tuple di tutte le righe (ogni riga e'ha un tuple)
   giorno = str(request.args["giorno"])
   db = MySQLdb.connect(host=HOST, user=USER, passwd=PASSWD, db="fotov")
   c = db.cursor()
   length = c.execute("SELECT ora,watt FROM potenza WHERE giorno = '%s'" % giorno)
   riga = c.fetchone() # riga = [ora,picco_watt]
   # potenza = Energia/tempo = Wh/5 min = Wh / (5/60) = 12 * Wh 
   entries = [{"ora":str(riga[0]),"potenza":int(12 * riga[1])},] #questa e' la lista
   for i in range(1,length):
      riga = c.fetchone()
      entries.append({"ora":str(riga[0]),"potenza":int(12 * riga[1])})
   db.close()
   return jsonify({"potenze":entries}) #creo dizionario con solo una entry pari alla lista precedente

@app.route("/giornalieroGrafico")
def giornalieroGrafico():
   '''
   GET: mese,anno
   RETURN:
   {
      "giornateDelMese":list
   }
   list= [
            {"giorno": "aaaa-mm-gg","produzione": "int","potenza": "int"},
            {"giorno": "aaaa-mm-gg","produzione": "int","potenza": "int"},
         ]
   '''
   
   db = MySQLdb.connect(host=HOST, user=USER, passwd=PASSWD, db="fotov")
   c = db.cursor()
   # Lista giorni
   mese = int(request.args["mese"])
   anno = int(request.args["anno"])
   # se il mese non e' incominciato dal primo giorno
   c.execute("SELECT giorno FROM giornaliero WHERE MONTH(giorno) = %d AND YEAR(giorno) = %d ORDER BY giorno LIMIT 1" % (mese,anno));
   giornoInizio = c.fetchone()[0]
   oggi = datetime.now()
   if (mese == oggi.month): #mese in corso quindi fermati ad oggi
      giorni = range(giornoInizio.day,oggi.day) #perche range esclude l'ultimo elemento ma oggi non ho il giornaliero
   else:
      giorni = range(giornoInizio.day,giorniDelMese(mese,anno) + 1) #perche range esclude l'ultimo elemento
   entries = [] #la lista
   for giorno in giorni:
      presente = bool(c.execute("SELECT giorno,watt,picco_watt FROM giornaliero WHERE DAY(giorno) = %d AND MONTH(giorno) = %d AND YEAR(giorno) = %d" % (giorno,mese,anno)))
      if presente:
         riga = c.fetchone() # riga = [ora,picco_watt]
         entries.append({"giorno":str(riga[0]),"produzione":riga[1],"potenza":riga[2]})
      else:
         entries.append({"giorno":str(datetime(year=anno,month=mese,day=giorno).date()),"produzione":0,"potenza":0})
   db.close()
   return jsonify({"giornateDelMese":entries}) #creo dizionario con solo una entry pari alla lista precedente

@app.route("/giornalieroTabella") #controllare giorno2 > giorno1
def giornalieroTabella():
   '''
      GET:
         "giorno_inizio" aaaa-mm-gg
         "giorno_fine" aaaa-mm-gg
      RETURNS:
      la tabella per tutti i giorni intermedi
      {
         "datiGiornata":
         [
            {
               "giorno": "aaaa-mm-gg",
               "watt": "int",
               "picco_watt": "int",
               "picco_ora": "hh:mm:ss",
               "inizio": "hh:mm:ss", #ora di inizio produzione
               "fine": "hh:mm:ss" #ora di fine produzione
            },
         ]
      }
   '''
   db = MySQLdb.connect(host=HOST, user=USER, passwd=PASSWD, db="fotov")
   c = db.cursor()
   entries = []
   giorno_inizio = datetime.strptime(str(request.args["giorno_inizio"]),"%Y-%m-%d")
   giorno_fine = datetime.strptime(str(request.args["giorno_fine"]),"%Y-%m-%d")
   if (giorno_inizio > giorno_fine):
      return "ERROR: giorno inizio e giorno fine invertiti"
   giorno = giorno_inizio #inizializzo giorno che e' la variabile iterativa
   giorni = [] #inizializzo la lista dei giorni
   while (giorno != giorno_fine):
      giorni.append(giorno)
      giorno = giorno + timedelta(days=1)
   giorni.append(giorno) # cosi mi mette anche giorno_fine
   for giorno in giorni:
      presente = bool(c.execute("SELECT giorno,watt,picco_watt,picco_ora,inizio,fine FROM giornaliero WHERE giorno = '%s'" % giorno))
      if presente:
         riga = c.fetchone() # riga = [giorno,watt,picco_watt,picco_ora,inizio,fine]
         entries.append({"giorno":str(riga[0]),"watt":riga[1],"picco_watt":riga[2],"picco_ora":str(riga[3]),"inizio":str(riga[4]),"fine":str(riga[5])})
      else:
         entries.append({"giorno":str(giorno.date()),"watt":0,"picco_watt":0,"picco_ora":str(timedelta()),"inizio":str(timedelta()),"fine":str(timedelta())})
   db.close()
   return jsonify({"datiGiornata":entries}) #creo dizionario con solo una entry pari alla lista precedente

@app.route("/mensileTabella")
def mensileTabella():
   '''
      GET:
         "mese_inizio" int
         "anno_inizio" int
         "mese_fine" int
         "anno_fine" int
      RETURNS:
      ritorna la tabella per tutti i mesi intermedi
      {
         "datiMese":
         [
            {
               "anno": "int",
               "mese": "int",
               "watt": "int",
               "giornata_max_giorno": "aaaa-mm-gg",
               "giornata_max_watt": "int",
               "picco_max_giorno": "aaaa-mm-gg",
               "picco_max_watt": "int"
            },
         ]
      }
   '''
   db = MySQLdb.connect(host=HOST, user=USER, passwd=PASSWD, db="fotov")
   c = db.cursor()
   entries = []
   mese_inizio = int(request.args["mese_inizio"])
   anno_inizio = int(request.args["anno_inizio"])
   mese_fine = int(request.args["mese_fine"])
   anno_fine = int(request.args["anno_fine"])
   if (anno_inizio > anno_fine):
      return "ERROR: anno inizio > anno fine"
   if (anno_inizio == anno_fine and mese_inizio > mese_fine):
      return "ERROR: anni uguali ma mese_inizio > mese_fine"
   giorno_inizio = datetime(year=anno_inizio,month=mese_inizio,day=1) #lavoro il giorno dell'inizio dei mesi
   giorno_fine = datetime(year=anno_fine,month=mese_fine,day=1) #lavoro il giorno dell'inizio dei mesi
   
   giorno = giorno_inizio #inizializzo giorno che e' la variabile iterativa
   giorni = [] #inizializzo la lista dei giorni, che sono il primo giorno dei mesi che mi interessano
   while (giorno != giorno_fine):
      giorni.append(giorno)
      giorno = giorno + timedelta(days=giorniDelMese(giorno.month,giorno.year))
   giorni.append(giorno) # cosi mi mette anche giorno_fine
   for giorno in giorni:
      presente = bool(c.execute("SELECT anno,mese,watt,giornata_max_giorno,giornata_max_watt,picco_max_giorno,picco_max_watt FROM mensile WHERE anno = '%d' AND mese = '%d'" % (giorno.year,giorno.month)))
      if presente:
         riga = c.fetchone() # riga = [giorno,watt,picco_watt,picco_ora,inizio,fine]
         entries.append({"anno":riga[0],"mese":riga[1],"watt":riga[2],"giornata_max_giorno":str(riga[3]),"giornata_max_watt":riga[4],"picco_max_giorno":str(riga[5]),"picco_max_watt":riga[6]})
      else:
         entries.append({"anno":giorno.year,"mese":giorno.month,"watt":0,"giornata_max_giorno":str(giorno.date()),"giornata_max_watt":0,"picco_max_giorno":str(giorno.date()),"picco_max_watt":0})
   db.close()
   return jsonify({"datiMese":entries}) #creo dizionario con solo una entry pari alla lista precedente

@app.route("/dataMinima")
def dataMinima():
   db = MySQLdb.connect(host=HOST, user=USER, passwd=PASSWD, db="fotov")
   c = db.cursor()
   numRighe = c.execute("SELECT giorno FROM giornaliero ORDER BY giorno LIMIT 1")
   if (numRighe == 0):
      db.close()
      return "Errore, non ci sono entries in giornaliero"
   else:
      riga = c.fetchone()
      db.close()
      return jsonify({"dataMinima":str(riga[0])})

#@app.route("/prova")
#def prova():
   #try:
      #return "<b>hello world!</b>"+str(request.args["gigi"])
   #except KeyError as e:
      #return "errore"
 #  return app.send_static_file("gigi.txt")
@app.route("/photoberry")
def photoberry():
   return app.send_static_file("photoberry.html")

#@app.route("/mphotoberry")
#def mphotoberry():
   #return app.send_static_file("mphotoberry.html")

#@app.route("/provaDirective")
#def provaDirective():
   #return app.send_static_file("prova.html")

if __name__ == "__main__":
   app.run(debug=False,port=PORT,host="0.0.0.0")
