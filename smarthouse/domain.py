from datetime import datetime
from random import random
from typing import List, Optional, Union 
from abc import abstractmethod

from pydantic import BaseModel

class Measurement(BaseModel): 
    """
    Klassen representerer en måling tatt fra en sensor ,
    ts, value og unit er attributter
    """
    timestamp: str
    value: float 
    unit: str | None


class Device:
    """En baseklasse for alle enheter i huset, definerer felles attributer
    som navn, id, type osv..."""
    def __init__(self, id: str, model_name: str, supplier: str, device_type: str):
        self.id = id
        self.model_name = model_name 
        self.supplier = supplier
        self.device_type = device_type
        self.room : Optional[Room] = None

    def get_device_type(self) -> str:
        return self.device_type

#Abstrakt metoder som krever at alle subklasser implementerer disse metodene
    @abstractmethod
    def is_actuator(self) -> bool:
        pass

    @abstractmethod
    def is_sensor(self) -> bool:
        pass

class Sensor(Device):
    def __init__(self, id: str, model_name: str, supplier: str, device_type: str, unit: str = ""):
        super().__init__(id, model_name, supplier, device_type)
        self.unit = unit

    def is_sensor(self) -> bool:
        return True
    def is_actuator(self) -> bool:
        return False
    
    def last_measurement(self) -> Measurement:
        return Measurement(timestamp= datetime.now().isoformat(), value=random() * 10, unit=self.unit)

        

class Actuator(Device):
    def __init__(self, id: str, model_name: str, supplier: str, device_type: str):
        super().__init__(id, model_name, supplier, device_type)
        self.state : Union[float, bool] = False

    def is_actuator(self) -> bool:
        return True

    def is_sensor(self) -> bool:
        return False

    def turn_on(self, target_value: Optional[float] = None):
        """Slår på aktuatoren, og setter den til en spesifikk verdi hvis gitt.
        Hvis ingen verdi er gitt, settes tilstanden bare til True."""""
        if target_value:
            self.state = target_value
        else:
            self.state = True

    def turn_off(self):
        self.state = False 

    def is_active(self) -> bool:
        return self.state is not False



class ActuatorWithSensor(Actuator, Sensor):
    """Klassen arver både fra actuator klassen og sensor klassen,
    demonstrerer prinsippet om flerav. Klassen representerer enheter som kan
    fungere både som sensor og aktuator, vil da ha en måling og en av/på funksjon"""
    def __init__(self, id: str, model_name: str, supplier: str, device_type: str):
        super().__init__(id, model_name, supplier, device_type)

    def is_actuator(self) -> bool:
        return True

    def is_sensor(self) -> bool:
        return True


class Floor:
    """En klasse for etasje i huset, hver etasje inneholder flere rom"""
    def __init__(self, level: int):
        self.level = level
        self.rooms : list[Room] = []


class Room:
    """Representerer et rom i en etasje, hvor romdata spesifiseres"""

    def __init__(self, floor: Floor, room_size: float, room_name: Optional[str]):
        self.floor = floor
        self.room_size = room_size
        self.room_name = room_name
        self.devices : list[Device]= []
        self.db_id :int | None = None #Database identifikator, brukes når systemet integreres med en DB



class SmartHouse:
    """
    Hovedklasse for styring av enheter i smarthuset, inkluderer registrering og
    admin av etasjer, rom og enheter

    """
    def __init__(self) -> None:
        self.floors : List[Floor]= []

    def register_floor(self, level: int) -> Floor:
        """
        Metode som registrerer et nytt rom på en spesifisert etasje og valgfritt navn
        """
        floor = Floor(level)
        self.floors.append(floor) #Append for å legge til element på slutten av liste, her legges den nye etasjen
        return floor

    def register_room(self, floor: Floor, room_size: float, room_name: Optional[str] = None) -> Room:
        """
        Metode som registrerer et nytt rom basert på spesifisert etasje med gitt størrelse,
        og valgfritt navn.
        """
        room = Room(floor, room_size, room_name)
        floor.rooms.append(room) #Append for å legge rom som et nytt element i slutten av liste
        return room


    def get_floors(self) -> List[Floor]:
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
        result = []
        for f in self.floors:
            result.extend(f.rooms) #Extend for å legge til alle rom i etasje til den resulterende listen
        return result


    def get_area(self) -> float:
        """
        Metode som returnerer det totale arealet av huset,
        altså summen av areal fra hvert rom i huset.
        """
        result = 0.0
        for r in self.get_rooms():
            result += r.room_size #Legger til arealet av hvert rom til 'result'.
        return result


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
        if old_room:
            old_room.devices.remove(device)
        room.devices.append(device) #append for å legge til enhet til liste over enheter i det nye rommet
        device.room = room


    def get_devices(self) -> List[Device]:
        """Metode som henter en liste over alle enheter registrert i huset
        Den går gjennom alle rom i huset og legger alle enhetene i en samlet liste
        """
        result = []
        for r in self.get_rooms():
            result.extend(r.devices) #Bruker 'extend' for å legge til alle enhetene fra rommet 'r'
            #til listen result,Dette er fordi hvert 'Room' inneholder en liste 'Devices'
            #som holder på enhetene i det rommet
        return result

    
    def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """
        Metode som henter en enhet baser på id nummer (serienummer)
        Den gjennomgår alle enheter i huset og returnerer enheten som matcher gitt ID nummer
        Hvis ingen enhet finnes med gitt ID, vil den returnere None
        """
        for d in self.get_devices():
            if d.id == device_id: #sjekker om ID til den gjeldende enheten i løkken matcher gitt ID
                return d
        return None

        

