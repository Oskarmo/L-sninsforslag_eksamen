from datetime import datetime
from random import random
from typing import List, Optional, Union 
from abc import abstractmethod

from pydantic import BaseModel
#Measurement klassen arver fra Basemodel,som er en del av pydantic bibloteket
#Dette sikrer at data som håndteres er korrekte og i riktig format
class Measurement(BaseModel): 
    """
    Klassen representerer en måling tatt fra en sensor ,
    ts, value og unit er attributter
    """
    timestamp: str
    value: float 
    unit: str | None #Målenhet


#Device er en baseklasse som representerer en generell enhet i smarthuset
#Bruker objektorienterte prinsipper som arv og abstraksjon for å gi et felles grunnlag for alle enheter i smarthuset
class Device:
    """En baseklasse for alle enheter i huset, definerer felles attributer
    som navn, id, type osv..."""
    def __init__(self, id: str, model_name: str, supplier: str, device_type: str):
        self.id = id #unik id for enhet
        self.model_name = model_name 
        self.supplier = supplier
        self.device_type = device_type
        self.room : Optional[Room] = None

    def get_device_type(self) -> str:
        #Returnerer hvilken type device det er snakk om, om det er en aktuator eller sensor
        return self.device_type

#Abstrakt metoder som krever at alle subklasser implementerer disse metodene
    #Dette demonstrerer polymorfisme og abstraksjon i OOP
    @abstractmethod
    def is_actuator(self) -> bool: #returnerer True hvis enhet er aktuator
        pass

    @abstractmethod
    def is_sensor(self) -> bool: #returnerer True hvis enhet er sensor
        pass

#Sensor er en subklasse av Device og representerer en sensor
#Arver funksjonalitet fra Deivce og tilfører spesifikke egenskaper for en sensor
class Sensor(Device):
    def __init__(self, id: str, model_name: str, supplier: str, device_type: str, unit: str = ""):
        super().__init__(id, model_name, supplier, device_type)
        self.unit = unit

    def is_sensor(self) -> bool: #
        return True #Bekrefter at enhet er en sensor
    def is_actuator(self) -> bool:
        return False #Bekrefter at enhet ikke er en aktuator
    
    def last_measurement(self) -> Measurement:
        #Oppretter og returnerer en måling tilhørende sensoren henter fra Measurement klasse
        #Målingen returnerer med tidsstempel,random verdi og måleenhet
        return Measurement(timestamp= datetime.now().isoformat(), value=random() * 10, unit=self.unit)

        

#Egen klasse for aktuatorer som arver fra Device
#klassen definerer funksjonalitet som er spesfikk for aktuatorer
class Actuator(Device):
#Klassen er egen for aktuatorer som kan skrus av og på, påvirker miljøet i huset ved å endre tilstand
    def __init__(self, id: str, model_name: str, supplier: str, device_type: str):
        super().__init__(id, model_name, supplier, device_type)
        self.state : Union[float, bool] = False #Nåværende tilstand på aktuator, False når av, True når på

    def is_actuator(self) -> bool:
        return True #Bekrefter at enhet er en aktuator

    def is_sensor(self) -> bool:
        return False #Bekrefter at enhet ikke er en sensor

    def turn_on(self, target_value: Optional[float] = None):
        """Slår på aktuatoren, og setter den til en spesifikk verdi hvis gitt.
        Hvis ingen verdi er gitt, settes tilstanden bare til True."""""
        if target_value:
            self.state = target_value
        else:
            self.state = True

    def turn_off(self): #skrur av aktuatoren ved å sette tilstand False
        self.state = False 

    def is_active(self) -> bool:
        #Returnerer True hvis aktutator er aktiv (påskrudd)
        return self.state is not False



class ActuatorWithSensor(Actuator, Sensor):
    """Klassen arver både fra actuator klassen og sensor klassen,
    demonstrerer prinsippet om flerav. Klassen representerer enheter som kan
    fungere både som sensor og aktuator, vil da ha en måling og en av/på funksjon"""
    def __init__(self, id: str, model_name: str, supplier: str, device_type: str):
        #Et "superkall" som initialiserer både Actuator og sensor konstruktører
        super().__init__(id, model_name, supplier, device_type)

    def is_actuator(self) -> bool:
        return True

    def is_sensor(self) -> bool:
        return True


class Floor:
    """En klasse for etasje i huset, hver etasje inneholder flere rom"""
    def __init__(self, level: int):
        self.level = level #Etasjenivå
        self.rooms : list[Room] = [] #Lager en liste med rom tilhørende etasje


class Room:
    """Representerer et rom i en etasje, hvor romdata spesifiseres"""

    def __init__(self, floor: Floor, room_size: float, room_name: Optional[str]):
        self.floor = floor  #Setter hvilken etasje rommet er i
        self.room_size = room_size #Størrelse på rommet
        self.room_name = room_name #Valgfritt navn på rommet
        self.devices : list[Device]= [] #Enheter i rommet
        self.db_id :int | None = None #Database identifikator, brukes når systemet integreres med en DB



class SmartHouse:
    """
    Hovedklasse for styring av enheter i smarthuset, inkluderer registrering og
    admin av etasjer, rom og enheter

    """


    def __init__(self) -> None:
        self.floors : List[Floor]= [] #En liste som holder alle etasjer i huset

    def register_floor(self, level: int) -> Floor:
        """
        Metode som registrerer et nytt rom på en spesifisert etasje og valgfritt navn
        """
        floor = Floor(level)
        self.floors.append(floor) #Append for å legge til element på slutten av liste, her legges den nye etasjen
        return floor

    def register_room(self, floor: Floor, room_size: float, room_name: Optional[str] = None) -> Room:
        """
        Metode som registrerer et nytt rom basert på spesifisert etasje med girr størrelse,
        og valgfritt navn.
        """
        room = Room(floor, room_size, room_name) #Bruker spesifiserer etasje, str på rom, og romnavn
        floor.rooms.append(room) #Append for å legge rom som et nytt element i slutten av liste
        return room


    def get_floors(self) -> List[Floor]: #funksjon som forteller at
        # get_floors skal returnere en liste hvor hvert element er en instans av Floor-klassen, kalt type hinting
        """
        Metode som returnerer en liste av alle registrerte etasjer i huset.
        sortert etter etasjenivå.
        """
        return self.floors


    def get_rooms(self) -> List[Room]:
        """
        Metode som returnerer en list med alle rom i huset
        """
        result = [] #Oppretter en tom liste
        for f in self.floors: #Itererer over hver etasje i huset
            result.extend(f.rooms) #Extend for å legge til alle rom i etasje til den resulterende listen
        return result #returnerer listen


    def get_area(self) -> float:
        """
        Metode som returnerer det totale arealet av huset,
        altså summen av areal fra hvert rom i huset.
        """
        result = 0.0 #setter en start variabel result som skal holde på det totale arealet av huset
        for r in self.get_rooms(): #en løkke som går gjennom alle rom i huset. 'get_rooms' gir listen over alle rom
            result += r.room_size #Legger til arealet av hvert rom til 'result'. 'room_size' er arealet av hvert enkelt rom
        return result #returnerer det totale arealet av huset


    def register_device(self, room: Room, device: Device):
        """
        Metode som registrerer en gitt enhet i et bestemt rom,
        Dette inkluderer og å fjerne enheten fra det gamle rommet hvis den allerede er registrert,
        for å så legge den til i dets nye rom.
        """
        old_room = device.room
        #Henter og lagrer referansen til enhetens nåværende rom
        #'device.room' er enten None hvis enheten ikke er registrert i et rom,
        #eller en referanse til rommet hvor enheten allerede er registrert
        if old_room: #sjekker om enheten er registrert i et rom allerede
            old_room.devices.remove(device) #Fjerner enheten fra listen over enheter i det gamle rommet
            #Nødvendig for å oppdatere plassering i systemet, og sikre at gammelt rom ikke lenger har referanse til enhet
        room.devices.append(device) #append for å legge til enhet til liste over enheter i det nye rommet
        device.room = room # setter enhetens 'room' -attributt til det nye rommet


    def get_devices(self) -> List[Device]:
        """Metode som henter en liste over alle enheter registrert i huset
        Den går gjennom alle rom i huset og legger alle enhetene i en samlet liste
        This method retrieves a list of all devices in the house"""
        result = [] #Oppretter en tom liste som skal inneholde alle enhetene
        for r in self.get_rooms(): #itererer gjennom alle rom i huset ved å kallse '.get_rooms'
            #'get_rooms' returnerer en liste av alle rom
            result.extend(r.devices) #Bruker 'extend' for å legge til alle enhetene fra rommet 'r'
            #til listen result,Dette er fordi hvert 'Room' inneholder en liste 'Devices'
            #som holder på enhetene i det rommet
        return result #Returnerer den samlede listen over alle enheter i huset

    
    def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """
        Metode som henter en enhet baser på id nummer (serienummer)
        Den gjennomgår alle enheter i huset og returnerer enheten som matcher gitt ID nummer
        Hvis ingen enhet finnes med gitt ID, vil den returnere None
        """
        for d in self.get_devices(): #Kaller på metoden '.get_devices()' for å få liste over alle enheter i huset
            if d.id == device_id: #Itererer gjennom liste
                # for å sjekke om ID til den gjeldende enheten i løkken matcher gitt ID
                return d #returnerer enheten umiddelbart hvis en match er funnet
        return None #Returnerer None hvis løkken gjennomføres uten å finne en matchende ID

        

