import logging
import threading
import time
import math
import requests

from messaging import SensorMeasurement
import common


class Sensor:

    def __init__(self, did):
        #Konstruktør som initialiserer sensoren med en enehts ID setter målingen til 0.0
        self.did = did
        self.measurement = SensorMeasurement('0.0')

    def simulator(self):
        #Logger at simulering for sensor starter
        logging.info(f"Sensor {self.did} starting")
        #En uendelig løkke som kontinuerlig generer og logger temperaturmålinger
        while True:
            #Beregner en verdi for temperatur basert på sinusfunksjon
            temp = round(math.sin(time.time() / 10) * common.TEMP_RANGE, 1)
            #Logger den nåværende simulerte temperaturen
            logging.info(f"Sensor {self.did}: {temp}")
            #Oppdaterer sensoren med den nye temperaturen
            self.measurement.set_temperature(str(temp))
            #Pauser simulatoren i en definert tidsperiode fra common modulen, før den generer neste måling
            time.sleep(common.TEMPERATURE_SENSOR_SIMULATOR_SLEEP_TIME)


    def client(self):
        """
        Metode som definerer hvordan en sensor kan kommunisere med skytjenesten,
        ved å sende målinger regelmessig, metoden sender kontinuerlig den nyeste
        sensor målingen til skytjenesten.
        """

        #Logger at klienten starter
        logging.info(f"Sensor Client {self.did} starting")

        # TODO START
        # send temperature to the cloud service with regular intervals
        #Uendelig løkke som kontinuerlig sender den nyeste temperaturmålingen til skytjenesten
        while True:
            #Logger den nåværende målingen før den sendes
            logging.info(f"Sensor Client {self.did} {self.measurement.get_temperature()}")
            #Bygger URLen for å sende målinger til skytjenesten basert på enhetens device id
            url = common.BASE_URL + f"sensor/{self.did}/current"
            #Serialiserer målingene til JSON for sending, dette inkluderer temperaturverdien.
            payload = self.measurement.to_json();

            headers = {
                'Content-Type': 'application/json'
            }
            #Sender en POST forespørsel med målingen til skytjenesten
            response = requests.request("POST", url, headers=headers, data=payload)
            #Venter et forhåndsdefinert tidsintervall (definert i common) før neste måling sendes
            time.sleep(common.TEMPERATURE_SENSOR_CLIENT_SLEEP_TIME)
        #Logger at klienten avsluttes
        logging.info(f"Client {self.did} finishing")

        # TODO END

    def run(self):
        """
        Multithreading for å kunne simulere for sensor samtidig som å kunne sende oppdatering til skyen
        Multithreading brukes for å kunne håndtere parallell utførelse i programmet hvor begge prossesene
        må kunne kjøre samtidig uten å blokkere hverandre.
        """

        # TODO START

        #Oppretter en ny tråd som vil kjøre simulator metoden
        #Simulator metoden er ansvarlig for å simulere endringer i temperaturen
        sensor_thread = threading.Thread(target=self.simulator)
        #Starter tråden som vil utføre simulator metoden parallelt med hovedprogrammet
        sensor_thread.start()

        #Oppretter en annen tråd som vil kjøre client metoden
        #Client metoden sender kontinuerlig den simulerte temperaturen til skytjenesten
        client_thread = threading.Thread(target=self.client)
        #Starter tråden som vil utføre client metoden parallelt med hovedprogrammet
        client_thread.start()

        # TODO END

