from typing import Literal
import uvicorn
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from smarthouse.domain import Actuator, ActuatorWithSensor, Device, Floor, Measurement, Room, Sensor, SmartHouse
from smarthouse.persistence import SmartHouseRepository
from pydantic import BaseModel
from pathlib import Path
import os

"""
Importer: fast api brukt for å opprette web server
Staticfiles, brukt for å operere statisk innhold som HTML, CSS og JL filer
pathlib from path og os, brukt for håndtere fil og server manipulering/endringer
"""

#Funksjon for å sette opp database ved å peke på riktig fil
def setup_database():
    #Finner prosjektets rotmappe basert på filens plassering
    project_dir = Path(__file__).parent.parent
    #Definerer stien til database filen
    db_file = project_dir / "data" / "db.sql" # you have to adjust this if you have changed the file name of the database
    #Returnerer en instans av SmartHouseRepository som håndterer interaksjonen med databasen
    return SmartHouseRepository(str(db_file.absolute()))

#Oppretter et nytt FastApi applikasjonsobjekt
app = FastAPI()

#Setter opp referansen og lagrer referansen i "repo"
repo = setup_database()

#Laster inn hele smarthuset fra databasen
smarthouse = repo.load_smarthouse_deep()
#testing av smarthuset http://127.0.0.1:8000/docs#/

#Sjekker om mappen www eksisterer i gjeldende mappe
if not (Path.cwd() / "www").exists():
    os.chdir(Path.cwd().parent) #Bytter til foreldre mappe hvis www ikke finnes

    #Hvis www mappen eksisterer, setter opp en rute for å håndtere statiske filer fra denne mappen
if (Path.cwd() / "www").exists():
    # http://localhost:8000/welcome/index.html
    app.mount("/static", StaticFiles(directory="www"), name="static")


# http://localhost:8000/ -> welcome page

#definerer en pydantic modell for å representere informasjon om smarthuset
class SmartHouseInfo(BaseModel):
    no_rooms: int
    no_floors: int
    total_area: float
    no_devices: int

    #Statisk metode for å lage en ny instans av SmartHouse info fra SmartHouse objektet
    @staticmethod
    def from_obj(house: SmartHouse):
        """
        Metoden konverterer et SmartHouse objekt til en SmartHouse info instans.
        Args:
            house(SmartHouse): Objekt som representerer hele smarthuset, med rom, etasjer, totalt areal og antall enheter
        Returns:
            SmartHouseInfo: En instans av SmartHouseInfo som inneholder informasjon om smarthuset
        """
        return SmartHouseInfo(
            no_rooms=len(house.get_rooms()), #Beregner antall rom  ved å kalle på .get_rooms metoden på smarthus objektet
            no_floors=len(house.get_floors()), #Beregner antall etasjer ved å kalle .get_floors
            total_area=house.get_area(),#Henter totalt areal ved å kalle .get_area fra Domain
            no_devices=len(house.get_devices())) #Beregner antall enheter ved å kalle .get_devices

#Pydantic modell som representerer detaljert informason om en etasje i smarthuset
class FloorInfo(BaseModel):
    fid: int  #Unik ID for etasjenummeret
    rooms: list[int] #Liste med ROM-ID er som finnes på etasjen

    @staticmethod
    def from_obj(floor: Floor):
        """
        Metoden konverterer et Floor objekt fra SmartHuset til en Floor instans.
        Args:
            floor(Floor): Et objekt som representerer en etasje, med rom og etasjenivå
        Returns:
            FloorInfo: En instans av FloorInfo som inneholder informasjon om etasjen, med hvilke rom som er på etasjen
        """
        return FloorInfo(
            fid=floor.level, #Tar etasjenivået fra Floor objektet og setter det som etasje ID
            rooms=[r.db_id for r in floor.rooms if r.db_id] #Lager en liste med ROM-ID'ene som faktisk har en ID i database
        )

#Pydantic modell som representerer detaljert informasjon om et rom i smarthuset
class RoomInfo(BaseModel):
    rid: int | None #Rom ID, kan være None hvis rommet ikke har en Database ID
    room_size: float #Areal av rom
    room_name: str | None #Rom navn, kan være None hvis ikke har et navn i Database
    floor: int #Etasjen som rommet befinner seg på
    devices: list[str] #Liste av devices som er registrert i rommet, str for de vil ligge med sin device-id


#Statisk metode for å en ny instans av RoomInfo fra et Room objekt
    @staticmethod
    def from_obj(room: Room):
        """
        Metoden konverterer et Room objekt til en Room info instans.
        Args:
            room(Room): Et objekt som representerer rommet, med de tilhørende egenskapene som er tidligere definert
        """
        return RoomInfo(
            rid=room.db_id, #Henter og setter rom-ID'en fra Room objektet hvis det er tilgjengelig
            room_size=room.room_size, #Henter og setter areal på rom
            floor=room.floor.level, #Henter og setter etasjenivå som rom befinner seg på
            room_name=room.room_name, #Henter romnavn, hvis tilgjengelig
            devices=[d.id for d in room.devices] #Henter og lager en liste med devices med deres ID for enhetene i rommet
        )

#Pydantic modell som definerer en modellklasse for å holde på informasjon om enhetene
class DeviceInfo(BaseModel):
    id: str #Device ID
    model: str #Device Modellnavn
    supplier: str #Supplier navn på device
    device_type: str #Device type, smart lock, temp sensor etc
    device_category: Literal["actuator"] | Literal["sensor"] | Literal["actuator_with_sensor"] | Literal["unknown"]
    #spesifikk kategori for device, om det er aktator eller sensor

    room: int | None #ID for rommet hvor enhet befinner seg, kan være None hvis ikke enheten er tildelt et rom

#Statisk metode for å oprette en DeviceInfo instans basert på Device-Instans fra Domain
    @staticmethod
    def from_obj(device: Device):
        """
        Metoden konverterer et Device objekt til en DeviceInfo instans, med håndtering av enhets kategorisering
        Arg:
        device(Device): Enhet objekt som skal konverteres
        Returns:
        DeviceInfo: Instans som inneholder detaljert info om enheten
        """
        #Bestemmer om enheten er sensor eller aktuator basert på Device-instans
        category: Literal['actuator', 'sensor', 'actuator_with_sensor', 'unknown'] = "unknown"
        if isinstance(device, ActuatorWithSensor):
            category = "actuator_with_sensor"
        elif isinstance(device, Actuator):
            category = "actuator"
        elif isinstance(device, Sensor):
            category = "sensor"

        #Oppretter og returnerer en Device-info instans med detaljer hentet fra Device objektet
        return DeviceInfo(
            id=device.id,
            model=device.model_name,
            supplier=device.supplier,
            device_type=device.device_type,
            device_category=category,
            room=device.room.db_id if device.room else None
        )

#Pydantic modell som representerer tilstands informasjon om en aktuator, på skrudd eller avskrudd
class ActuatorStateInfo(BaseModel):
    state: str | float #Tilstanden til en aktuator kan være str eller flyttall, f.esk 1 på, 0 av

#Statisk metode som oppretter en ny instans av ActuatorStateInfo fra Actuator klassen/instansen
    @staticmethod
    def from_obj(actuator: Actuator):
        """
        Metoden konverterer en Actuator-instans til en ActuatorStateInfo instans, som representerer om den er av eller på
        Args:
        actuator(Actuator): Aktuator objektet som skal konverteres
        Returns:
        ActuatorStateInfo: Instansen som inneholder informasjon om tilstanden til en aktuator.
        """
        #Sjekker om aktuatorens tilstand og om tilstanden har en flyt verdi
        if actuator.state and isinstance(actuator.state, float):
            return ActuatorStateInfo(state=actuator.state) #Returnerer tilstanden som en flyttall
        #Hvis state er en streng, sjekker da om den har en tilstand spesifisert med streng
        elif actuator.state:
            return ActuatorStateInfo(state="running") #Bruker strengen "running" for å indikere at aktuatoren er på
        #Hvis ingen av de overnevnte, antas aktuatoren å være avskrudd
        else:
            return ActuatorStateInfo(state="off") #strengen off for å indikere at den er av

#Rute for å håndtere statiske filer fra mappen "www"
# http://localhost:8000/welcome/index.html
app.mount("/static", StaticFiles(directory="www"), name="static")


# http://localhost:8000/ -> welcome page

#Definerer rotruten for applikasjonen
@app.get("/")
def root():
    return RedirectResponse("/static/index.html")


# Health Check / Hello World
#Definerer en enkel health check
@app.get("/hello")
def hello(name: str = "Oskar"):
    """
    En enkel endpoint for å si 'Hello' til brukeren, med navn som kan tilpasses
    Args:
    name(str):Navnet til bruker
    Returns:
    dict: en orbok med hilsen
    """
    return {"hello": name}

#Definerer en rute for å hente generell info om smarthuset
@app.get("/smarthouse")
def get_smarthouse_info() -> SmartHouseInfo:
    """
    Endpoint som returnerer et objekt med informasjon om den generelle strukturen av smarthuset
    Returns:
    SmartHouseInfo: Pydantic modell som inneholder informasjon om antall rom, etasjer, enheter og totalt areal av hus
    """
    #Bruker den statiske metoden fra SmartHouseInfo for å lage et info objekt fra det globale 'smarthouse' objektet
    return SmartHouseInfo.from_obj(smarthouse)

#Henter en liste over alle etasejer i smarthuset og returnerer det som en liste av FloorInfo objekter.
@app.get("/smarthouse/floor")
def get_floors() -> list[FloorInfo]:
    """
    Endpoint som returnerer en liste med informasjon om de ulike etasjene, konverterer hver etasje til FloorInfo objekter
    """
    #Konverterer hver etasje til et FloorInfo objekt og returnerer listen
    return [FloorInfo.from_obj(x) for x in smarthouse.get_floors()]

#Henter informasjon om en spesifikk etasje, basert på etasjens id
@app.get("/smarthouse/floor/{fid}")
def get_floor(fid: int) -> Response:
    """
    Endpoint som returnerer detaljert informasjon om spesifikk etasje spesifisert ved 'fid'.
    Args:
    fid(int):Etasjen sin ID
    Returns:
    JSONResponse: En JSON-respons som inneholder informasjonen om etasjen, eller 404 response hvis ikke funnet.
    """
    #Går gjennom listen av etasjer og sjekker om den angitte ID'en matcher med noen av etasjene i smarthuset
    for f in smarthouse.get_floors():
        if f.level == fid:
            #Hvis funnet, returnerer da en JSON-respons med info om etasjen.
            return JSONResponse(content=jsonable_encoder(FloorInfo.from_obj(f)))
    #Hvis etasjen ikke finnes returneres en 404 error message
    return Response(status_code=404)

#Henter en liste over rom i en spesifikk etasje, spesifisert med 'fid'.
@app.get("/smarthouse/floor/{fid}/room")
def get_rooms(fid: int) -> list[RoomInfo]:
    """
    Endpoint som returnerer en liste av RoomInfo objekter for hvert rom i den spesifikke etasjen
    Args:
    fid(int): Etasjens ID som rommene skal hentes fra
    Returns:
    list[RoomInfo]: En liste med informasjon fra alle rommene i etasjen
    """
    #Filtrerer og returnerer rom som tilhører den spesifikke etasjen, konvertert til RoomInfo objekter
    return [RoomInfo.from_obj(r) for r in smarthouse.get_rooms() if r.floor.level == fid]

#Henter delaljert informasjon om et rom i smarthuset, spesifisert av etasje id og rom id
@app.get("/smarthouse/floor/{fid}/room/{rid}")
def get_room(fid: int, rid: int) -> Response:
    """
    Endpoint som søker gjennom alle rom i smarthuset og returnerer detaljert informasjon om spesififsert rom, hvis det finnes
    Args:
    fid(int): Etasje som rom befinner seg i
    rid(int): Rom som vi skal hente informasjon om
    Returns:
    JSONResponse: En respons med detaljer om rommet i dict format, hvis ikke funnet 404 error message
    """
    #Iterer gjennom alle rom i huset
    for r in smarthouse.get_rooms():
        #Sjekker om rom-ID og etasje ID matcher med oppgitte ID'er
        if r.db_id == rid and r.floor.level == fid:
            #Returnerer en JSONRespone med rom info hvis funnet
            return JSONResponse(content=jsonable_encoder(RoomInfo.from_obj(r)))
    #Hvis rom ikke funnet returnerer en 404 error message
    return Response(status_code=404)

#Henter en liste over alle enheter i huset
@app.get("/smarthouse/device")
def get_devices() -> list[DeviceInfo]:
    """
    Endpoint som returnerer en liste over alle enheter i smarthuset, hver representert som DeviceInfo objekter.
    Returns:
    list[DeviceInfo]: En liste med enhetsinformasjon for alle enheter i huset.
    """
    #Konverterer hvert enhet til et DeviceInfo objekt og returnerer listen
    return [DeviceInfo.from_obj(d) for d in smarthouse.get_devices()]

#Henter informasjon en spesifikk enhet, angitt med enhetens Device-id
@app.get("/smarthouse/device/{uuid}")
def get_device(uuid: str) -> Response:
    """
    Endpoint som søker etter og returnerer detaljer om en spesifikk smart enhet, baser på dens Device-ID
    Args:
    uuid(str): Device-id som vi vil hente info om
    Returns:
    JSONResponse: Respons med detaljer om enheten hvis den finnes, hvis ikke 404 error message.
    """
    #Iterer gjennom devices i smarthuset
    for d in smarthouse.get_devices():
        #Sjekker om angitt id er registrert i huset
        if d.id == uuid:
            #Hvis funnet returnerer JSON-respons med enhetsinformasjonen
            return JSONResponse(content=jsonable_encoder(DeviceInfo.from_obj(d)))
    #Hvis ikke funnet returnerer en 404 error message
    return Response(status_code=404)

#Henter den nyligste målingen fra en sensor
@app.get("/smarthouse/sensor/{uuid}/current")
def get_most_recent_measurement(uuid: str) -> Response:
    """
    Endpoint som returnerer den nyligste målingen fra en gitt sensor
    Args:
    uuid(str): Den unike ID-en til sensoren vi vil hente siste måling fra
    Returns:
    JSONResponse: Respons med den nyeste måling fra sensor, eller feilmelding hvis ingen måling tilgjengelig
    """
    #Finner enheten baser på uuid og sjekker at det er en sensor
    device = smarthouse.get_device_by_id(uuid)
    if device and device.is_sensor():
        #hvis funnet og er sensor, henter da den siste målingen
        reading = repo.get_latest_reading(device)
        if reading:
        #Hvis måling tilgjengelig, returnerer da måingen som en JSONResponse
            return JSONResponse(content=jsonable_encoder(reading))
        else:
            #Returnerer feilmelding hvis ingen måling er tilgjengelig
            return JSONResponse(content=jsonable_encoder({'reason': 'no timeseries available'}), status_code=404)
    else:
        #Returnerer feilmelding hvis enhet ikke funnet, eller enhet ikke er en sensor
        return JSONResponse(content=jsonable_encoder({'reason': 'sensor with id not found'}), status_code=404)

#Legger til en ny måling for en spesifikk sensor
@app.post("/smarthouse/sensor/{uuid}/current")
def add_sensor_measurement(uuid: str, measurement: Measurement) -> Response:
    """
    Endpoint som tar imot og lagrer en ny måling for en sensor.
    Args:
    uuid(str): Den unike ID-en til sensoren
    measurement(Measurement): Målingsobjektet som vi vil legge til
    Returns:
    JSONResponse: Bekreftelse på at måling er lagt til eller en feilmelding hvis sensor ikke finnes
    """
    #Sjekker om enheten finnes og er en sensor
    device = smarthouse.get_device_by_id(uuid)
    if device and device.is_sensor():
        #Hvis det er en sensor lagres måling i db
        repo.insert_measurement(uuid, measurement)
        #Returnerer den lagrede målingen som en JSONRespons med statuskode 201(Created)
        return JSONResponse(content=jsonable_encoder(measurement), status_code=201)
    else:
        #Returnerer en feilmelding hvis sensor ikke finnes
        return JSONResponse(content=jsonable_encoder({'reason': 'sensor with uuid not found'}), status_code=404)

#Henter en liste over målinger fra en sensor, med mulighet for å begrense antall målinger
@app.get("/smarthouse/sensor/{uuid}/values")
def get_measurements(uuid: str, n: int | None = None) -> Response:
    """
    Endpoint som returnerer en liste med målinger for en spesifikk sensor
    Args:
    uuid(str): Device id for enhet vi vil hente fra
    n(int | None): Maks antall målinger som vi vil hente, hvis ikke spesifisert returneres alle målinger
    Returns:
    JSONResponse: En liste med alle målingene eller en feilmelding hvis sensor ikke finnes
    """
    #Sjekker om enheten finnes og er en sensor
    device = smarthouse.get_device_by_id(uuid)
    if device and device.is_sensor():
        #hvis den finnes og er sensor henter målingene
        result = repo.get_readings(uuid, n)
        #Returnerer målingene som en JSONResponse
        return JSONResponse(content=jsonable_encoder(result), status_code=200)
    else:
    #Hvis sensor ikke finnes returnerer en feilmelding
        return JSONResponse(content=jsonable_encoder({'reason': 'sensor with uuid not found'}), status_code=404)

#Sletter siste måling for en spesifikk sensor
@app.delete("/smarthouse/sensor/{uuid}/oldest")
def delete_old_measurement(uuid: str) -> Response:
    """
    Endpoint som sletter den eldste målingen for en spesifikk sensor
    Args:
    uuid(str): Device-id til sensor som vi vil slette siste måling fra
    Returns:
    JSONResponse: En respons som bekrefter sletting av siste måling eller feilmelding hvis sensor ikke finnes
    """
    #Henter device og sjekker at device er en sensor
    device = smarthouse.get_device_by_id(uuid)
    if device and device.is_sensor():
        result = repo.delete_oldest_reading(uuid)
        return JSONResponse(content=jsonable_encoder(result), status_code=200)
    else:
        return JSONResponse(content=jsonable_encoder({'reason': 'sensor with uuid not found'}), status_code=404)

#Henter tilstanden til en spesifikk aktuator
@app.get("/smarthouse/actuator/{uuid}/current")
def get_sensor_state(uuid: str) -> Response:
    """
    Endpoint som returnerer tilstanden til en spesifikk aktuator
    Args:
    uuid(str): Device-id til Aktuator som vi vil hente tilstand på
    Returns:
    JSONResponse: En respons med tilstands data eller en feilmelding hvis aktuator ikke funnet
    """
    device = smarthouse.get_device_by_id(uuid)
    if device and isinstance(device, Actuator):
        return JSONResponse(jsonable_encoder(ActuatorStateInfo.from_obj(device)))
    else:
        return JSONResponse(content=jsonable_encoder({'reason': 'actuator with uuid not found'}), status_code=404)

#Oppdaterer tilstanden til en aktuator
@app.put("/smarthouse/actuator/{uuid}/")
def update_sensor_state(uuid: str, target_state: ActuatorStateInfo) -> Response:
    """
    Endpoint som oppdaterer tilstanden til en aktuator basert på input tilstand som vi vil skal settes
    Args:
    uuid(str): Device-id til aktuator som vi vil endre tilstand på
    target_state(ActuatorStateInfo): Tilstand som vi vil sette for aktuatoren
    Response:
    JSONResponse: Respons som bekrefter oppdateringen eller feilmelding hvis aktuator ikke funnet
    """
    device = smarthouse.get_device_by_id(uuid)
    if device and isinstance(device, Actuator):
        if isinstance(target_state.state, float):
            device.turn_on(target_state.state)
        elif target_state.state == "running":
            device.turn_on()
        elif target_state.state == "off":
            device.turn_off()
        # else leave unchanged
        repo.update_actuator_state(device)
        return JSONResponse(jsonable_encoder(ActuatorStateInfo.from_obj(device)))
    else:
        return JSONResponse(content=jsonable_encoder({'reason': 'actuator with uuid not found'}), status_code=404)

#Kjører serveren hvis filen blir eksekvert som hovedprogram
#if__name__ = '__main__' standard python teknikk som avgjør om scriptet kjøres direkte (og ikke importeres)
#uvicorn.run(app, host="127.0.0.1", port = 8000), uvicorn funksjon som starter serveren
#app, FastApi applikasjon som skal kjøres av Uvicorn serveren
#Host Angir ip adressen som serveren skal kjøre på, angitt adresse her er en local adresse, serveren bare tilgjengelig fra min pc
#port, dette er portnummeret som serveren lytter på

if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)


