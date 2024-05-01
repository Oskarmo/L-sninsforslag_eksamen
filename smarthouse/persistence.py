import sqlite3
from typing import Optional
from smarthouse.domain import Actuator, ActuatorWithSensor, Measurement, Room, Sensor, SmartHouse

class SmartHouseRepository:
    """
    Klasse som gir mulighet for å lagre og laste 'SmartHouse objektet
    fra en SQLite database
    """

    def __init__(self, file: str) -> None:
        """
        Konstruktør for 'SmartHouse' klassen som initialiserer en ny instans av klassen
        Metoden tar imot et filnavn som parameter og oppretter en tilkobling til SQLite databasen
        som ligger i den angitte filen. Dette setter opp grunnlaget for videre Database manipulasjoner
        """
        self.file = file #Lagrer filstien som en attributt i klassen
                        #Dette gjør filstien tilgjengelig for andre metoder i klassen, som f.eks reconnect()
                        #som kan trenge å gjenopprette tilkboling til databasen

        #Siste linjen oppretter en database forbindelse til SQLite databasen spesifisert av filstien
        #Parameteret 'check_same_Thread=False' er viktig for å tillate at flere tråder kan dele tilkoblingen
        #Det er nyttig i flertrådede applikasjoner hvor flere deler av systemet trenger å gjøre
        #database manipulasjoner samtidig
        #Uten denne innstillingen, vil SQLite nekte å la flere tråder å bruke samme tilkobling samtidig
        #for å hindre data korrupsjon
        self.conn = sqlite3.connect(file, check_same_thread=False)

    def __del__(self):
        self.conn.close()

    def cursor(self) -> sqlite3.Cursor:
        """
        Gir en 'rå SQLite cursor' for å intagere med databasen
        Når metoden kalles for å skaffe en cursor, er det viktig å huske
        å kalle 'commit/rollback' og 'close' selv etter ferdig med å utføre SQL spørringer
        """
        return self.conn.cursor()
    #Returnerer en cursor fra den etablerte database tilkoblingen

    def reconnect(self):
        """
        Lukker den nåværende tilkoblingen til databasen og åpner en ny
        Metoden sikrer at tilkoblingen er frisk og uten tidligere potensielle tilstandsfeil
        """
        self.conn.close() #Lukker den nåværende tilkoblingen til databasen
                         #Viktig for å frigjøre ressurser som database tilkoblingen holder på
                        #og for å unngå låsing eller andre problemer forbundet med en åpen tilkobling
        self.conn = sqlite3.connect(self.file)
        #Oppretter en ny tilkobling til databasen som er spesifisert ved filstien

    
    def load_smarthouse_deep(self):
        """
        Metoden henter den komplette enkeltinstansen av 'SmartHouse' objektet lagret i databasen
        Hentingen gir en 'dyp' kopi av smarthuset, dvs det vil si at alle refererte objekt innen objektstrukturen
        (som etasjer, rom og enheter) blir også hentet.
        """
        result = SmartHouse() #Oppretter et nytt smarthouse objekt som vil være fylt med data fra database
        cursor = self.cursor() #Henter en database cursor for å utføre SQL spørringer

        # Creating floors
        #Cursor som utfører SQL spørringen, spørringen henter det høyeste etasjenummeret fra 'rooms' tabellen
        #for å finne ut hvor mange etasjer som finnes
        cursor.execute('SELECT MAX(floor) from rooms;')
        no_floors = cursor.fetchone()[0] #fetchcone henter dataen, altså etasje taller
        floors = [] #Oppretter en tom liste for å holde på etasjene

        #Løkke som oppretter etasjeobjekt basert på antall etasjer henter fra databasen
        for i in range(0, no_floors):
            floors.append(result.register_floor(i + 1))
            #Registrerer hver etasje i SmartHus objektet, append lar oss legge til element i listen

        # Creating roooms
        #Oppretter en tom ordbok for å holde på rom objektene med databse ID som nøkkel
        room_dict = {}

        #Henter alle rom fra databasen med SQL spørring, cursor utfører spørringen
        cursor.execute('SELECT id, floor, area, name from rooms;')

        #fetchall henter all data fra spørring og lagrer all romdataen i liste med tupler
        #Hver tuple inneholder informasjon om rom id, etasje, areal og navn
        room_tuples = cursor.fetchall()

        #Itererer gjennom hvert rom i tuppelen som er hentet fra databasen for å registrere hvert rom
        for room_tuple in room_tuples:

            #Beregner etasjens indeks ved å trekke 1 fra etasjenummeret fra databasen (ettersom lister i python er 0 basert)
            #Konverterer deretter arealet fra streng til flyttall
            #Registrerer så rommet i SmartHouse objektet og mottar en referanse til det nylig opprettede objektet
            room = result.register_room(floors[int(room_tuple[1]) - 1], float(room_tuple[2]), room_tuple[3])

            #setter 'db_id' som er attributtet til et nylig opprettede rommet med ID hentet fra database
            #Dette gjør det mulig å relatere objektet med sin unike ID i databasen for fremtidige operasjoner
            room.db_id = int(room_tuple[0])

            #Legger til det nye romobjektet i 'room_dict' ordboken med rom ID som nøkkel
            #Dette tillater rask oppslag av romobjektet basert på deres ID i database,
            #Dette er nyttig enheter til deres tilhørende rom fra databasen
            room_dict[room_tuple[0]] = room

         #Utfører en SQL spørring for å hente alle smart enhetene fra databasen
        cursor.execute('SELECT id, room, kind, category, supplier, product from devices;')
        device_tuples = cursor.fetchall() #Henter resultatet fra spørringen og lagrer det i en liste av tupler

        #Iterer gjennom hver enhetstuple som ble hentet fra databasen
        for device_tuple in device_tuples:

            #Bruker her room_dict for å finne romobjektet som korresponderer med rom ID som er lagret i device_tuple
            room = room_dict[device_tuple[1]]

            #Lagrer her katergorien til enheten, som forteller om det er en sensor eller aktutator
            category = device_tuple[3]

            #Sjekker enhetens kategori og oppretter tilsvarende enhetsobjekt i det tilsvarende rommet
            if category == 'sensor':
                #Hvis det er en sensor, registerer sensor i rommet med ID, navn, produktnavn, leverandør og type
                result.register_device(room, Sensor(device_tuple[0], device_tuple[5], device_tuple[4], device_tuple[2]))

                #Hvis det er en aktuator registrerer som aktuator, men om typen er av 'Heat Pump' indikerer dette at enheten
                #er både sensor og aktuator
            elif category == 'actuator':
                if device_tuple[2] == 'Heat Pump':
                    #Hvis det er 'Heat Pump' registreres enheten som actuator med sensor
                    result.register_device(room, ActuatorWithSensor(device_tuple[0], device_tuple[5], device_tuple[4], device_tuple[2]))
                else:
                    #Hvis ikke Heat Pump registreres som vanlig Actuator
                    result.register_device(room, Actuator(device_tuple[0], device_tuple[5], device_tuple[4], device_tuple[2]))

        #Iterer først gjennom alle enhetene registrert i smarthus objektet
        for dev in result.get_devices():

            #Sjekker om enheten er av instans av klassen Actuator
            #Dette er viktig siden vi vil utføre tilstand sjekk av disse
            if isinstance(dev, Actuator):

                #Utfører så SQL spørring for å finne tilstand til actuator'en registrert i database
                #'dev.id' brukes for å identifisere riktig enhet i databasen basert på dens unike ID
                cursor.execute(f"SELECT state FROM states where device = '{dev.id}';")

                #Henter så resultatet fra spørringen '.fetchcone()[0]' gir oss den første kolonnen i resultatet
                #som  er tilstanden til enheten. Hvis det ikke er registrert tilstand, vil den returnere None
                state = cursor.fetchone()[0]

                #Derfor hvis state er None, kaller vi på turn_off metoden så tilstand på actutator blir satt til off
                #i databasen
                if state is None:
                    dev.turn_off()

                #Hvis ikke sjekker om 'state == 1.0' som vil si den er påskrudd
                elif float(state) == 1.0:
                    dev.turn_on() #Kaller på 'turn_on' metoden uten parameter

                #Hvis tilstand er noe annet enn '1.0' eller 'None', antar en spesifikk tilstand
                #som enheten skal settes til
                else:
                    dev.turn_on(float(state))
                    #Kaller turn_on metoden med det hentede tilstanden som parameter


        cursor.close() #lukker cursor tilkobling på database
        return result #returnerer resultatet av spørringen


    def get_readings(self, sensor: str, limit_n: int | None) -> list[Measurement]:

        """
        Metoden henter en liste over målinger fra en sensor, listen kan begrenses til et max antall måliner
        Args:
            sensor(str) id til sensoren som vi skal hente måling fra
            limit_n(int) Et valgfritt tall som spesifiserer antall målinger som skal hentes

        returns:
        list[Measurement]: en liste med målingene forespurt, hvor hver måling er en instans av Measurement klassen
        """
        cursor = self.cursor() #Oppretter en cursor for å gjøre utspørringer i databasen

        #Utfører spørring i databasen basert på om en limit på antall målinger er satt eller ikke
        if limit_n:

            #Hvis et max antall målinger er spesifisert inkluderer vi dette i spørringen med LIMIT og antallet spesifisert ?
            cursor.execute("""\
SELECT ts, value, unit 
FROM measurements
WHERE device = ?
ORDER BY datetime(ts) DESC 
LIMIT ?
            """, (sensor, limit_n))
        else:
            #Hvis ikke max antall målinge spesifisert, inkluderer ikke LIMIT i spørring, henter da alle målinger fra sensor
            cursor.execute("""\
SELECT ts, value, unit 
FROM measurements
WHERE device = ?
ORDER BY datetime(ts) DESC 
            """, (sensor,))
        tuples = cursor.fetchall() #Henter alle resultatene fra spørringen som en liste av tupler

        #Konverterer så hver tuple til et instans av Measurement
        result = [Measurement(timestamp=t[0], value=t[1], unit=t[2]) for t in tuples]
        cursor.close() #Lukker cursor for å frigjøre database ressurser
        return result #Returnerer listen av Measurement instanser


    def delete_oldest_reading(self, sensor: str) -> Measurement | None:
        """
        Metode som sletter den eldste målingen for en spesifisert sensor fra databasen
        Args:
            sensor(str): ID til sensor som vi ønsker å slette eldste måling

        Returns:
            Measurement| None: returnerer den slettede målingen som en Measurement-instans, eller None hvis ingen måling funnet
        """

        c = self.cursor() #Oppretter en database cursor for å utføre SQL spørringer

        #Definerer så SQL spørringen og utfører for å finne den eldste målingen for den angitte sensoren
        query = """\
SELECT ts, value, unit FROM measurements WHERE device = ? ORDER BY datetime(ts) ASC LIMIT 1
        """
        c.execute(query, (sensor,)) #Utfører spørringen med sensor ID som parameter
        tup = c.fetchone() #Henter resultatet av spørringen, som er den eldste målingen

        #Sjekker om det faktisk ble funnet en måling
        if tup:
            #Definerer ny SQL spørring for å slette målingen fra databasen
            query = f"""
    DELETE FROM measurements
    WHERE device = ?
    AND ts = ?
            """
            #Slettespørringen blir utført med sensor ID og tidsstempel som parametre.
            c.execute(query, (sensor, tup[0]))
            self.conn.commit() #Utfører en commit for å bekrefte endring i databasen
        c.close() #Lukker cursor for å firgjøre database ressurser

        #Returnerer den slettede målingen som en Measurement-instans hvis en måling ble funnet og slettet
        if tup:
            return Measurement(timestamp=tup[0], value=tup[1], unit=tup[2])
        else:
            #Returnerer None hvis ingen måling ble funnet og slettet
            return None

            

    def insert_measurement(self, sensor: str, measurement: Measurement) -> None:

        """
        Metoden legger til en ny måling for en gitt sensor
        Args:
            sensor(str): ID til sensor som målingen tilhører
            measurement(Measurement): En instans av Measurement klassen som inneholder dataene som skal legges inn

        Result:
              Utfører en INSERT operasjon i databasen for å legge til målingen
        """

        #Definererer SQL spørringen som skal brukes for å legge til ny måling i measurements tabellen
        #Bruker place holders '?' for å unngå SQL-injeksjon og sikre at data som legges inn er sikre
        query = f"""
INSERT INTO measurements (device, ts, value, unit) VALUES (?, ?, ?, ?)
        """
        c = self.cursor() #Oppretter en cursor tilkobling til databasen

        #Utfører INSERT spørringen med de faktiske verdiene som skal legges inn
        #Disse inkluderer sensor ID, ts for måling, verdi av måling, og måleenhet
        c.execute(query, (sensor, measurement.timestamp, measurement.value, measurement.unit))
        #commiter endring til database, dette bekrefter at endring legges inn så det lagres i db
        self.conn.commit()
        c.close() #Lukker cursor for å frigjøre database ressurser og unngå lekkasjer


    def get_latest_reading(self, sensor) -> Optional[Measurement]:
        """
        Metoden henter den siste målignen fra en spesifisert sensor hvis tilgjengelig
        Returnerer None hvis det ikke finnes målinger for den spesifiserte sensoren.
        Args:
            sensor: sensorobjekt, spesifiserer med ID hvilken sensor som måling skal hentes fra
        Returns:
            Optional[Measurement] Returnerer en Measurement-instans som representerer den siste målingen
                                 eller None hvis ingen målinger er tilgjengelig
        """
        #Definerer SQL spørringen for å hente den siste målingen fra sensor
        #Sorterer resultatet etter ts, i synkende rekkefølge for å få siste måling som første rad
        query = f"""
SELECT ts, value, unit from measurements m 
WHERE device = '{sensor.id}'
order by ts desc 
limit 1;
        """
        #Oppretter en cursor for å utføre database operasjoner
        c = self.cursor()

        #Utfører spørringen og lagrer resultatet
        c.execute(query)
        result = c.fetchall() #Henter alle rader fra spørre resultatet

        #Hvis resultatet fra spørringen er en tom liste returnerer da None og lukker cursor
        if len(result) == 0:
            return None

        #Så lenge resultatet ikke er en liste med null rader, oppretter da en Measurement-instans
        #fra den første raden i resultatet
        #Konverterer så verdiene til riktig datatype og pakker dem inn i Measurement - klassen
        m = Measurement(timestamp=result[0][0],value=float(result[0][1]),unit=result[0][2])
        c.close()
        return m #Returnerer den nyeste målingen som en Measurement-klasse


    def update_actuator_state(self, actuator):
        """
        Metoden lagrer tilstanden til den gitte aktuatoren i databasen
        Args:
            actuator: Bruker spesifiserer hvilken Aktuator ID som skal oppdateres,
            bruker her en instans Actuator-klassen
        Result:
              Tilstanden til den gitte aktuatoren oppdateres i database
        """
        #Sjekker at den gitte aktuatoren faktisk er en instans av Aktuator klassen
        #Viktig så vi vet at metoden kun håndterer Aktuator objekt
        if isinstance(actuator, Actuator):
            #Initialiserer så standardverdi for tilstanden som skal lagres i databasen
            s = 'NULL'

            #Sjekker og konverterer aktuator tilstand til en streng som er egnet for SQL spørringen
            if isinstance(actuator.state, float): #Konverterer her flyttilstand til streng
                s = str(actuator.state)
            elif actuator.state is True:
                s = '1.0' #Bruker '1.0' som er streng i database for å sette tilstand registrert som True altså påskrudd

            #Definerer så SQL spørringen for å oppdatere tabellen states (tilstand) til aktuatoren i databasen
            query = f"""
UPDATE states 
SET state = {s}
WHERE device = '{actuator.id}'; 
        """
            #Oppretter en database cursor for å utføre spørringen
            c = self.cursor()
            #Utfører den formulerte spørringen med den akutelle tilstandsverdien og aktuatorens ID
            c.execute(query)
            #Utfører commit for å commite endring til database, så tilstand blir lagret i db
            self.conn.commit()
            #Lukker cursor for å frigjøre database ressurser
            c.close()



    # statistics

    def calc_avg_temperatures_in_room(self, room, from_date: Optional[str] = None, until_date: Optional[str] = None) -> dict:
        """
        Metoden beregner gjennomsnitts temperaturen i et gitt rom for en angitt tidsperiode
        Args:
            room(Room):Rommet hvor gj.snitt temp skal beregnes
            from_date(Optional[str]):Start dato for tidsperiode, inkluderer ikke tidspunktet hvis None
            until_date(Optional[str]): Slutt dato for tidsperiode, inkluderer ikke tidspunktet hvis None
        Returns:
            dict: En ordbok hvor nøklene er i ISO-format og verdiene er gj.snitt temp for disse datoene
        """
        #Oppretter en tom ordbok som vil inneholde datoer og deres tilsvarende gj.snitt temperaturer
        result = {}
        #Sjekker at 'room' faktisk er en instans av Room og at den har en gyldig database ID
        if isinstance(room, Room) and room.db_id is not None:
            #Forbereder SQL spørre begrensninger basert på input datoene
            lower_bound_pred = "" #Vil inneholde SQL kode for start dato
            upper_bound_pred = "" #Vil inneholde SQL kode for slutt dato

            #Setter SQL koden for startdato hvis den er oppgitt og ikke None
            if from_date is not None:
                lower_bound_pred = f"AND ts >= '{from_date} 00:00:00'" #Startdato i SQL spørring
            #Setter SQL koden for sluttdato hvis den er oppgitt og ikke None
            if until_date is not None:
                upper_bound_pred = f"AND ts <= '{until_date} 23:59:59'" #Sluttdato i SQL spørring

            #Definerer her SQL spørringen som beregner gj.snitt temperaturen per dag
            query = f"""
    SELECT STRFTIME('%Y-%m-%d', DATETIME(ts)), avg(value) 
    FROM devices d 
    INNER join measurements m ON m.device = d.id 
    WHERE d.room = {room.db_id} AND m.unit = '°C' {lower_bound_pred} {upper_bound_pred}
    GROUP BY STRFTIME('%Y-%m-%d', DATETIME(ts)) ;
            """
            #Utfører spørringen med en database cursor
            cursor = self.cursor()
            cursor.execute(query)
            query_result = cursor.fetchall()
            #Iterer over resultatet og legger til hver dato og dens gj.snitt temperatur i resultat ordboken
            for row in query_result:
                result[row[0]] = float(row[1])
        #Returnerer så ordboken som inneholder resultatet med gj.snitt temp or angitte datoer
        return result

    
    def calc_hours_with_humidity_above(self, room, date: str) -> list:
        """
        Metoden beregner hvilke timer iløpet av en gitt dag det var mer enn tre målinger hvor fuktigheten
        var over gjennomsnittet for den dagen i det gitte rommet.
        Args:
            room(Room): rommet der målingene skal analyseres
            date(str): Datoen som vi skal analysere for i ISO format
        Returns:
            list: med timer (0-23) hvor fuktigheten var høyere enn gjennomsnittet mer enn tre ganger.
        """
        #Oppretter en tom liste som skal holde på resultatet
        result = []
        #Sjekker at input objekt 'room' faktisk er en instans av 'Room' klassen og at det har en gyldig database ID
        if isinstance(room, Room) and room.db_id is not None:
            #Definerer SQL spørring som bruker en sub-query for å beregne gj.snitt fuktigheten
            query = f"""
SELECT  STRFTIME('%H', DATETIME(m.ts)) AS hours
FROM measurements m 
INNER JOIN devices d ON m.device = d.id 
INNER JOIN rooms r ON r.id = d.room 
WHERE 
r.id = {room.db_id} 
AND m.unit = '%' 
AND DATE(m.ts) = DATE('{date}')
AND m.value > (
	SELECT AVG(value) 
	FROM measurements m 
	INNER JOIN devices d on d.id = m.device
	WHERE d.room = 4 AND DATE(ts) = DATE('{date}'))
GROUP BY hours 
HAVING COUNT(m.value) > 3; 
            """
            #Utfører spørringen
            cursor = self.cursor()
            cursor.execute(query)
            #Iterer over resultatet og legger timene til resultatlisten
            for h in cursor.fetchall():
                result.append(int(h[0])) #Konverterer timen fra streng til heltall og legger den til i listen
        return result
        # Returnerer listen over timer hvor fuktigheten var over gjennomsnittet mer enn tre ganger.

#steg i sql spørring 1. Henter timen fra ts og omdøper kollone til 'hours, 2.Filtrerer målingene til det spesifikke rommet
#3.Sørger for at kun målinger med fuktighet som enehet behandles
#4.Beregner gj.snitt av fuktighetsmålingene for dagen
#5.Grupperer resultatet etter timer
#6.Velger kun målinger hvor det er mer enn 3 målinger over gjennomsnittet
#Begrenser data til den spesifikke datoen
 #Filtrerer målingene til de som er over gjennomsnittet for dagen



