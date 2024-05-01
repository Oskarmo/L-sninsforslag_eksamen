import logging
import threading
import time
import requests

from messaging import ActuatorState
import common


class Actuator:

    def __init__(self, did):
        self.did = did #device id for aktuatoren
        self.state = ActuatorState('False') #Setter False tilstand som standard

    def simulator(self):
        #Logger at simulator for aktuatoren starter
        logging.info(f"Actuator {self.did} starting")
        #En uendelig løkke som kontinuerlig simluerer aktuatoren sin tilstand
        while True:
            #Logger den nåværende tilstanden for aktuatoren
            logging.info(f"Actuator {self.did}: {self.state.state}")
            #Venter på forhåndsdefinert tidsintervall før neste simuleringsrunde
            time.sleep(common.LIGHTBULB_SIMULATOR_SLEEP_TIME)

    def client(self):
       #Logger at klienten for aktuatoren starter
        logging.info(f"Actuator Client {self.did} starting")

        # TODO START
        # send request to cloud service with regular intervals to obtain actuator state
        #Bygger URLen for å sende forespørsel til skytjeneste og hente den nyeste tilstanden til akutatoren
        url = common.BASE_URL + f"actuator/{self.did}/current"
        #Initialiserer Payload og headers for HTTP forespørselen
        payload = {}
        headers = {}
        #En undelig løkke som kontinuerlig oppdaterer tilstanden til aktuatoren basert på data fra skytjenesten
        while True:
            #Sender en GET forespørsel til skytjenesten og henter responsen
            response = requests.request("GET", url, headers=headers, data=payload)
            #Oppdaterer tilstanden til aktatoren basert på responsen
            self.state = ActuatorState.from_json(response.text)
            #Logger den oppdaterte tilstanden til aktuatoren
            logging.info(f"Actuator Client {self.did} {self.state.state}")
            #Venter på et forhåndsdefinert tidsintervall før neste oppdatering
            time.sleep(common.LIGHTBULB_CLIENT_SLEEP_TIME)
        #logger at klient avsluttes, selv om den ikke nåes pga uendelig løkke
        logging.info(f"Client {self.did} finishing")

        # TODO END

    #Multithreading brukt for å kunne simulere en aktuator samtidig som å kunne motta oppdateringer fra skyen
    def run(self):

        # TODO START

        # Starter en tråd som simulerer en fysisk lyspære (eller en annen aktuator)
        sensor_thread = threading.Thread(target=self.simulator)
        sensor_thread.start()

        #Starter en tråd som mottar tilstand fra skytjenesten
        client_thread = threading.Thread(target=self.client)
        client_thread.start()

        # TODO END


