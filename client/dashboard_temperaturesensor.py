import tkinter as tk
from tkinter import ttk

import logging
import requests

#Importerer klassen SensorMeasurement
from messaging import SensorMeasurement
import common

#Definerer funksjon som kalles når bruker klikker på 'refresh' i GUI
def refresh_btn_cmd(temp_widget, did):
    #Logger at temperaturendring er initiert
    logging.info("Temperature refresh")

    # TODO START
    # send request to cloud service to obtain current temperature
    #Bygger URL for API forespørsel basert på sensor ID og URL fra common modul
    url = common.BASE_URL + f"sensor/{did}/current"
    #Forbereder payload og headers for GET forespørsel
    payload = {}
    headers = {}
    #Utfører GET forespørselen for å hente nåværende temp
    response = requests.request("GET", url, headers=headers, data=payload)
    #Parser svaret fra server og oppretter en SensorMeasurement fra JSON-dataen
    sensor_measurement = SensorMeasurement.from_json(response.text)

    # replace statement below with measurement from response
    # sensor_measurement = SensorMeasurement(init_value="-273.15")

    # TODO END

    #Oppdaterer tekstfeltet i brukergrensesnittet for å vise den mottate temperaturen
    temp_widget['state'] = 'normal' # setter tekstfeltet til normal for å tillate endringer
    temp_widget.delete(1.0, 'end') #Sletter den eksiterende teksen i tekstfeltet
    temp_widget.insert(1.0, sensor_measurement.value) #Setter inn den nye temperaturen i tekstfeltet
    temp_widget['state'] = 'disabled' #Setter tekstfeltet tilbake til deaktivert modus for å forhindre brukerendringer


def init_temperature_sensor(container, did):

    ts_lf = ttk.LabelFrame(container, text=f'Temperature sensor [{did}]')

    ts_lf.grid(column=0, row=1, padx=20, pady=20, sticky=tk.W)

    temp = tk.Text(ts_lf, height=1, width=10)
    temp.insert(1.0, 'None')
    temp['state'] = 'disabled'

    temp.grid(column=0, row=0, padx=20, pady=20)

    refresh_button = ttk.Button(ts_lf, text='Refresh',
                                command=lambda: refresh_btn_cmd(temp, did))

    refresh_button.grid(column=1, row=0, padx=20, pady=20)
