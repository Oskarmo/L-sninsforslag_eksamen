#Importerer nødvendige biblotek for GUI, logging og nettverkforespørsler
import tkinter as tk
from tkinter import ttk
import logging
import requests

#Importerer klasse med Aktuator status og common modul
from messaging import ActuatorState
import common

#Funksjon som håndterer endring av tilstand på lyspære
def lightbulb_cmd(state, did):
    #Henter den valgte tilstanden fra radioknappene i GUI
    new_state = state.get()
    #Logger denne tilstanden
    logging.info(f"Dashboard Lightbulb state: {new_state}")

    # TODO START
    # send HTTP request with new actuator state to cloud service
    #Bestemmer hva tilstanden skal være basert på bruker sitt valg i GUI
    if state.get() == 'On':
        new_state = "running"
    else:
        new_state = "off"

    #Oppretter en instans av ActuatorState med den nye tilstanden
    actuator_state = ActuatorState(new_state)
    #Konverterer aktuatortilstanden til JSON format for å sende over HTTP
    payload = actuator_state.to_json()
    #Setter headere for forespørselen, spesifikt innhold stypen altså JSON
    headers = {'Content-Type': 'application/json'}
    #Bygger URLen for PUT forespørselen ved å hente enhetens ID fra common og legge til basen URL
    url = common.BASE_URL + f"actuator/{did}/"
    #Sender PUT forespørsel til server med den nye tilstanden
    response = requests.request("PUT", url, headers=headers, data=payload)

    # TODO: END

#
def init_lightbulb(container, did):
    #Oppretter en etikkeramme (Labelframe) for lyspæren
    lb_lf = ttk.LabelFrame(container, text=f'LightBulb [{did}]')
    #Plasserer den i i hovedvindu
    lb_lf.grid(column=0, row=0, padx=20, pady=20, sticky=tk.W)

    #Oppretter en StringVar en spesiell Tkinter variabel for å spore tilstand til lyspæren
    lightbulb_state_var = tk.StringVar(None, 'Off')
    #Radio knapp for å skru lyspæren på
    on_radio = ttk.Radiobutton(lb_lf, text='On', value='On',
                               variable=lightbulb_state_var,
                               command=lambda: lightbulb_cmd(lightbulb_state_var, did))
    #Plasserer radioknapp i etikettrammen
    on_radio.grid(column=0, row=0, ipadx=10, ipady=10)
    #Oppretter radioknapp for å skru lyspæren av
    off_radio = ttk.Radiobutton(lb_lf, text='Off', value='Off',
                                variable=lightbulb_state_var,
                                command=lambda: lightbulb_cmd(lightbulb_state_var, did))
    #PLasserer radioknapp for av ved siden av på
    off_radio.grid(column=1, row=0, ipadx=10, ipady=10)
