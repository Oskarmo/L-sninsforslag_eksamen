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


    def reconnect(self):
        """
        Lukker den nåværende tilkoblingen til databasen og åpner en ny
        Metoden sikrer at tilkoblingen er frisk og uten tidligere potensielle tilstandsfeil
        """
        self.conn.close()
        self.conn = sqlite3.connect(self.file)


    
    def load_smarthouse_deep(self):
        """
        Metoden henter den komplette enkeltinstansen av 'SmartHouse' objektet lagret i databasen
        Hentingen gir en 'dyp' kopi av smarthuset, dvs det vil si at alle refererte objekt innen objektstrukturen
        (som etasjer, rom og enheter) blir også hentet.
        """
        result = SmartHouse() #Oppretter et nytt smarthouse objekt som vil være fylt med data fra databasen
        cursor = self.cursor()

        cursor.execute('SELECT MAX(floor) from rooms;')
        no_floors = cursor.fetchone()[0]
        floors = []

        #Løkke som oppretter etasjeobjekt basert på antall etasjer henter fra databasen
        for i in range(0, no_floors):
            floors.append(result.register_floor(i + 1))
            #Registrerer hver etasje i SmartHus objektet, append lar oss legge til element i listen

        room_dict = {}

        cursor.execute('SELECT id, floor, area, name from rooms;')

        room_tuples = cursor.fetchall()

        #Itererer gjennom hvert rom i tuppelen som er hentet fra databasen for å registrere hvert rom
        for room_tuple in room_tuples:

            #Beregner etasjens indeks ved å trekke 1 fra etasjenummeret fra databasen (ettersom lister i python er 0 basert)
            room = result.register_room(floors[int(room_tuple[1]) - 1], float(room_tuple[2]), room_tuple[3])

            room.db_id = int(room_tuple[0])
            #Legger til det nye romobjektet i 'room_dict' ordboken med rom ID som nøkkel
            room_dict[room_tuple[0]] = room

        cursor.execute('SELECT id, room, kind, category, supplier, product from devices;')
        device_tuples = cursor.fetchall()

        for device_tuple in device_tuples:

            #Bruker room_dict for å finne romobjektet som korresponderer med rom ID som er lagret i device_tuple
            room = room_dict[device_tuple[1]]

            #Lagrer katergorien til enheten, som forteller om det er en sensor eller aktutator
            category = device_tuple[3]

            #Sjekker enhetens kategori og oppretter tilsvarende enhetsobjekt i det tilsvarende rommet
            if category == 'sensor':
                result.register_device(room, Sensor(device_tuple[0], device_tuple[5], device_tuple[4], device_tuple[2]))

                #Hvis det er en aktuator registrerer som aktuator, men om typen er av 'Heat Pump' indikerer dette at enheten
                #er både sensor og aktuator
            elif category == 'actuator':
                if device_tuple[2] == 'Heat Pump':
                    result.register_device(room, ActuatorWithSensor(device_tuple[0], device_tuple[5], device_tuple[4], device_tuple[2]))
                else:
                    result.register_device(room, Actuator(device_tuple[0], device_tuple[5], device_tuple[4], device_tuple[2]))

        #Iterer først gjennom alle enhetene registrert i smarthus objektet
        for dev in result.get_devices():
            if isinstance(dev, Actuator):

                cursor.execute(f"SELECT state FROM states where device = '{dev.id}';")
                state = cursor.fetchone()[0]

                if state is None:
                    dev.turn_off()

                elif float(state) == 1.0:
                    dev.turn_on() #Kaller på 'turn_on' metoden uten parameter

                #Hvis tilstand er noe annet enn '1.0' eller 'None', antar en spesifikk tilstand som enhet skal settes til
                else:
                    dev.turn_on(float(state))

        cursor.close()
        return result


    def get_readings(self, sensor: str, limit_n: int | None) -> list[Measurement]:
        """
        Metoden henter en liste over målinger fra en sensor, listen kan begrenses til et max antall måliner
        Args:
            sensor(str) id til sensoren som vi skal hente måling fra
            limit_n(int) Et valgfritt tall som spesifiserer antall målinger som skal hentes
        returns:
        list[Measurement]: en liste med målingene forespurt, hvor hver måling er en instans av Measurement klassen
        """
        cursor = self.cursor()

        #Utfører spørring i databasen basert på om en limit på antall målinger er satt eller ikke
        if limit_n:
            cursor.execute("""\
SELECT ts, value, unit 
FROM measurements
WHERE device = ?
ORDER BY datetime(ts) DESC 
LIMIT ?
            """, (sensor, limit_n))
        else:
            cursor.execute("""\
SELECT ts, value, unit 
FROM measurements
WHERE device = ?
ORDER BY datetime(ts) DESC 
            """, (sensor,))
        tuples = cursor.fetchall()

        #Konverterer hver tuple til et instans av Measurement
        result = [Measurement(timestamp=t[0], value=t[1], unit=t[2]) for t in tuples]
        cursor.close()
        return resul


    def delete_oldest_reading(self, sensor: str) -> Measurement | None:
        """
        Metode som sletter den eldste målingen for en spesifisert sensor fra databasen
        Args:
            sensor(str): ID til sensor som vi ønsker å slette eldste måling
        Returns:
            Measurement| None: returnerer den slettede målingen som en Measurement-instans, eller None hvis ingen måling funnet
        """

        c = self.cursor()
        query = """\
SELECT ts, value, unit FROM measurements WHERE device = ? ORDER BY datetime(ts) ASC LIMIT 1
        """
        c.execute(query, (sensor,)) #Utfører spørringen med sensor ID som parameter
        tup = c.fetchone()
        #Sjekker om det faktisk ble funnet en måling
        if tup:
            #Definerer ny SQL spørring for å slette målingen fra databasen
            query = f"""
    DELETE FROM measurements
    WHERE device = ?
    AND ts = ?
            """
            c.execute(query, (sensor, tup[0]))
            self.conn.commit()

        c.close()

        #Returnerer den slettede målingen som en Measurement-instans hvis en måling ble funnet og slettet
        if tup:
            return Measurement(timestamp=tup[0], value=tup[1], unit=tup[2])
        else:
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

        query = f"""
INSERT INTO measurements (device, ts, value, unit) VALUES (?, ?, ?, ?)
        """
        c = self.cursor()
        #Utfører INSERT spørringen med de faktiske verdiene som skal legges inn
        c.execute(query, (sensor, measurement.timestamp, measurement.value, measurement.unit))

        self.conn.commit()
        c.close()


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
        #SQL spørring hvor resultatet sortert etter ts, i synkende rekkefølge for å få siste måling som første rad
        query = f"""
SELECT ts, value, unit from measurements m 
WHERE device = '{sensor.id}'
order by ts desc 
limit 1;
        """
        c = self.cursor()

        c.execute(query)
        result = c.fetchall()

        #Hvis resultatet fra spørringen er en tom liste returnerer da None og lukker cursor
        if len(result) == 0:
            return None

        #Så lenge resultatet ikke er en liste med null rader, oppretter da en Measurement-instans
        #fra den første raden i resultatet
        m = Measurement(timestamp=result[0][0],value=float(result[0][1]),unit=result[0][2])
        c.close()
        return m

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
        if isinstance(actuator, Actuator):
            s = 'NULL'

            #Sjekker og konverterer aktuator tilstand til en streng som er egnet for SQL spørringen
            if isinstance(actuator.state, float):
                s = str(actuator.state)
            elif actuator.state is True:
                s = '1.0'

            #Definerer så SQL spørringen for å oppdatere tabellen states (tilstand) til aktuatoren i databasen
            query = f"""
UPDATE states 
SET state = {s}
WHERE device = '{actuator.id}'; 
        """
            c = self.cursor()
            c.execute(query)
            #Utfører commit for å commite endring til database, så tilstand blir lagret i db
            self.conn.commit()

            c.close()


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
            lower_bound_pred = "" #Vil inneholde SQL kode for start dato
            upper_bound_pred = "" #Vil inneholde SQL kode for slutt dato

            #Setter SQL koden for startdato/sluttdato hvis den er oppgitt og ikke None
            if from_date is not None:
                lower_bound_pred = f"AND ts >= '{from_date} 00:00:00'"

            if until_date is not None:
                upper_bound_pred = f"AND ts <= '{until_date} 23:59:59'"

            query = f"""
    SELECT STRFTIME('%Y-%m-%d', DATETIME(ts)), avg(value) 
    FROM devices d 
    INNER join measurements m ON m.device = d.id 
    WHERE d.room = {room.db_id} AND m.unit = '°C' {lower_bound_pred} {upper_bound_pred}
    GROUP BY STRFTIME('%Y-%m-%d', DATETIME(ts)) ;
            """

            cursor = self.cursor()
            cursor.execute(query)
            query_result = cursor.fetchall()

            #Iterer over resultatet og legger til hver dato og dens gj.snitt temperatur i resultat ordboken
            for row in query_result:
                result[row[0]] = float(row[1])

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

        result = []
        #Sjekker at input objekt 'room' faktisk er en instans av 'Room' klassen og at det har en gyldig database ID
        if isinstance(room, Room) and room.db_id is not None:

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

            cursor = self.cursor()
            cursor.execute(query)
            #Iterer over resultatet og legger timene til resultatlisten
            for h in cursor.fetchall():
                result.append(int(h[0])) #Konverterer timen fra streng til heltall og legger den til i listen
        return result





#steg i sql spørring 1. Henter timen fra ts og omdøper kollone til 'hours, 2.Filtrerer målingene til det spesifikke rommet
#3.Sørger for at kun målinger med fuktighet som enehet behandles
#4.Beregner gj.snitt av fuktighetsmålingene for dagen
#5.Grupperer resultatet etter timer
#6.Velger kun målinger hvor det er mer enn 3 målinger over gjennomsnittet
#Begrenser data til den spesifikke datoen
 #Filtrerer målingene til de som er over gjennomsnittet for dagen



