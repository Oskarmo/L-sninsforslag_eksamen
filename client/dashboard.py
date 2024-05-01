#Importerer tkinter for GUI funksjonalitet og logging for å logge applikasjonen sin aktivitet
import tkinter as tk # https://www.pythontutorial.net/tkinter/

import logging
#importerer funksj9on for lyspære og temp sensor som vi har definert i dashboard_
from dashboard_lightbulb import init_lightbulb
from dashboard_temperaturesensor import init_temperature_sensor

#Importerer common modul
import common
#Definerer format på logg meldinger
log_format = "%(asctime)s: %(message)s"
#Setter opp loggkonfig til å bruke det definerte formatet og spesifiserer nivået av loggmeldinger som skal fanges opp
logging.basicConfig(format=log_format, level=logging.INFO, datefmt="%H:%M:%S")

#Oppretter hovedvinduet for GUI
root = tk.Tk()
#Setter størrelse på hovedvinduet
root.geometry('450x300')
#Setter tittelen på hovedvinduet
root.title('ING301 SmartHouse Dashboard')

#Kaller funksjonen for å initialisere lyspæren i GUI, med referanse til hovedvinduet og enhetens ID fra common modul
init_lightbulb(root, common.LIGHTBULB_DID)
#Samme for temp sensor
init_temperature_sensor(root, common.TEMPERATURE_SENSOR_DID)

#Starter tkinter sin hovedløkke som holder GUI vinduet åpent og lytter etter bruker interaksjon.
root.mainloop()
