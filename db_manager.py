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

"""
    Crea il database con tre tabelle:
    potenza:
        GIORNO                     ORA                     WATT          PICCO_WATT      PICCO_ORA
        (data inserimento)  (ora inserimento)  (prodotti)  (picco [W])     (ora watt picco)
    giornaliero:
        GIORNO          WATT     PICCO_WATT     PICCO_ORA  INIZIO (produzione)  FINE (produzione)
        (prodotti)
"""
import logging
import MySQLdb

from config import USER, PASSWD, DATABASE


def insertDatabase(inserimento):
    db = MySQLdb.connect(host='localhost', user=USER, passwd=PASSWD, db=DATABASE)
    cursore = db.cursor()
    cursore.execute(inserimento)
    db.commit()
    db.close()
    return


def updateDatabase():
    """
        Aggiunge una entry nel database giornaliero usando i dati del database di base
        Pulisce istantaneo
        potenza:
            GIORNO                     ORA                     WATT          PICCO_WATT      PICCO_ORA
            (data inserimento)  (ora inserimento)  (prodotti)  (picco [W])     (ora watt picco)
        giornaliero:
            GIORNO          WATT     PICCO_WATT     PICCO_ORA  INIZIO (produzione)  FINE (produzione)
            (prodotti)

    """
    logging.info('Connect to database')
    db = MySQLdb.connect(host='localhost', user=USER, passwd=PASSWD, db=DATABASE)
    c = db.cursor()
    logging.info('Connected')

    #### nel caso in cui si spegne a mezza giornata e poi riparte, eliminare quelle vecchie
    c.execute('DELETE FROM giornaliero WHERE giorno=curdate()') # numero entries con il giorno di oggi
    ####

    # creare ed assegnare: data, WATT, inzio, fine, picco_ora, picco_WATT
    data = '2013-08-05' #data
    watt = 0 # float [Wh]
    inizio = '07:04:02:333' # ora
    fine = '20:02:45:977' # ora
    picco_ora = '13:52:30:232' # ora
    picco_watt = 2763.3 # float [W]
    # calcolo variabili
        # DATA: prendo la data dell'ultimo lampeggio

    c.execute('SELECT giorno FROM potenza ORDER BY giorno DESC LIMIT 1') #seleziona la data ultima entry
    try:
        dataUltimoLampeggio = (c.fetchone())[0]
    except TypeError as e:
        logging.info('Empty database, no update done')
        return 0

    logging.info(dataUltimoLampeggio)
    data = dataUltimoLampeggio
        #INIZIO
        #inizio = ora primo lampeggio con data=dataUltimoLampeggio
    c.execute("SELECT ora FROM potenza WHERE giorno = '%s'" % data)
    entriesList = c.fetchall()
    # (
    #    (ora,)
    #    (ora,)
    #    (ora,)
    #  )
    inizio = (entriesList[0])[0]
        #FINE
        #fine = ora dell'ultimo lampeggio
    fine = (entriesList[len(entriesList)-1])[0]
    logging.info('%s %s', inizio, fine)

        #WATT
        #sommo WATT di ogni entry con data = dataUltimoLampeggio
    c.execute("SELECT watt FROM potenza WHERE giorno = '%s'" % data)
    watt = 0
    while (True):
        try:
            wattEntry = (c.fetchone())[0]
            watt += int(wattEntry)
        except TypeError as e:
            break
    logging.info('watt: %s', watt)
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
    except MySQLdb.Error as exception:
        logging.info('Something went wrong: %s', exception)

    db.commit()
    db.close()
    return watt


def setup():
    """
        da vedere con MySQL
    """
    return


def createDatabase():
    """
        Crea il database con tre tabelle:
        potenza:
            GIORNO                     ORA                     WATT          PICCO_WATT      PICCO_ORA
            (data inserimento)  (ora inserimento)  (prodotti)  (picco [W])     (ora watt picco)
        giornaliero:
            GIORNO          WATT     PICCO_WATT     PICCO_ORA  INIZIO (produzione)  FINE (produzione)
            (prodotti)
        istantaneo:
            GIORNO  ORA    WATT
    """
    return