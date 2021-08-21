
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
import logging


def inserisciDatabase(inserimento):
    logging.info(inserimento)


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
    logging.info('updateDatabase')
    logging.info('connected')
    logging.info('DELETE FROM giornaliero WHERE giorno=curdate()')
    logging.info('SELECT giorno FROM potenza ORDER BY giorno DESC LIMIT 1') #seleziona la data ultima entry
    logging.info("SELECT ora FROM potenza WHERE giorno = 'data'")
    logging.info("SELECT watt FROM potenza WHERE giorno = 'data'")
    watt = 2
    logging.info('watt: %s', watt)
    logging.info("SELECT picco_watt,picco_ora FROM potenza WHERE giorno = 'data'")
    logging.info("INSERT INTO giornaliero VALUES('data','watt','picco_watt','picco_ora','inizio','fine')")
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