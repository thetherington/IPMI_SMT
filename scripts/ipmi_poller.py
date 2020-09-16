import argparse
import requests
from xml.dom import minidom
import urllib3
import math
import json
import datetime
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()


class poller():

    def sensorType(self, id):

        sensorDef = {

            "01": "temperature",
            "02": "voltage",
            "04": "fanspeed",
            "05": "chassis",
            "08": "psu",
            "c0": "OEM Sensor",
            "0d": "hdd",
            "c1": "wattage",

        }

        try:
            return sensorDef[id]

        except Exception:
            return None

    def unitType(self, unitID):

        unitDef = {

            "01": "degrees C",
            "02": "degrees F",
            "03": "degrees K",
            "04": "Volts",
            "05": "Amps",
            "06": "Watts",
            "07": "Joules",
            "12": "R.P.M",
            "13": "Hz"

        }

        try:
            return unitDef[unitID]

        except Exception:
            return None

    def sensorPSURead(self, reading):

        state_String = ""

        if not((reading / 1) % 2) and not((reading / 2) % 2):

            state_String = 'Not Present. '
            state_color = "bgcolor=white"

        else:

            if int(reading / 1) % 2:
                state_String += 'Presence detected. '
                state_color = "bgcolor=green"
            if int(reading / 2) % 2:
                state_String += 'Power Supply Failure detected. '
                state_color = "bgcolor=red"
            if int(reading / 4) % 2:
                state_String += 'Predictuve Failure. '
                state_color = "bgcolor=red"
            if int(reading / 8) % 2:
                state_String += 'Power Supply input lost (AC/DC). '
                state_color = "bgcolor=red"
            if int(reading / 16) % 2:
                state_String += 'Power Supply input lost or out-of-range. '
                state_color = "bgcolor=red"
            if int(reading / 32) % 2:
                state_String += 'Power Supply input out-of-range, but present. '
                state_color = "bgcolor=red"
            if int(reading / 64) % 2:
                state_String += 'Configuration error. '
                state_color = "bgcolor=red"

        return [state_String, state_color]

    def sensorChassisRead(self, reading):

        state_String = ""
        state_color = "bgcolor=red"

        if reading == 0:
            state_String += 'OK'
            state_color = "bgcolor=green"
        if int(reading / 1) % 2:
            state_String += 'General Chassis Intrusion. '
        if int(reading / 2) % 2:
            state_String += 'Drive Bay instrusion. '
        if int(reading / 4) % 2:
            state_String += 'I/O Card area instrusion. '
        if int(reading / 8) % 2:
            state_String += 'Processor area instrusion. '
        if int(reading / 16) % 2:
            state_String += 'LAN Leash Lost. '
        if int(reading / 32) % 2:
            state_String += 'Unauthorized dock. '
        if int(reading / 64) % 2:
            state_String += 'Fan area intrusion. '

        return [state_String, state_color]

    def sensorHDDRead(self, reading):

        state_String = ""
        state_color = "bgcolor=red"

        if int(reading / 1) % 2:
            state_String += 'Drive Presence'
            state_color = "bgcolor=green"
        if int(reading / 2) % 2:
            state_String += 'Drive Fault'
            state_color = "bgcolor=red"
        if int(reading / 4) % 2:
            state_String += 'Predictuve Failure'
            state_color = "bgcolor=red"
        if int(reading / 8) % 2:
            state_String += 'Hot Spare'
            state_color = "bgcolor=red"
        if int(reading / 16) % 2:
            state_String += 'Consistency / Parity Check'
            state_color = "bgcolor=red"
        if int(reading / 32) % 2:
            state_String += 'In Critical Array'
            state_color = "bgcolor=red"
        if int(reading / 64) % 2:
            state_String += 'In Failed Array'
            state_color = "bgcolor=red"
        if int(reading / 128) % 2:
            state_String += 'Rebuild / Remap in progress'
            state_color = "bgcolor=red"
        if int(reading / 256) % 2:
            state_String += 'Rebuild / Remap Aborted'
            state_color = "bgcolor=red"
        if reading == "00":
            state_String = 'Not Present'
            state_color = "bgcolor=white"

        return [state_String, state_color]

    def toSigned(self, Num, signedbitB):

        if signedbitB > 0:

            if ((Num % (0x01 << signedbitB) / (0x01 << (signedbitB - 1))) < 1):
                return Num % (0x01 << signedbitB - 1)
            else:
                temp = (Num % (0x01 << signedbitB - 1)) ^ ((0x01 << signedbitB - 1) - 1)
                return (-1 - temp)
        else:
            return Num

    def bitwise(self, raw_data, m, b, rb):

        M_raw = ((int(m, 16) * 0xC0) << 2) + (int(m, 16) >> 8)
        B_raw = ((int(b, 16) & 0xC0) << 2) + (int(b, 16) >> 8)

        Km_raw = int(rb, 16) >> 4
        Kb_raw = int(rb, 16) & 0x0F

        M_data = self.toSigned(M_raw, 10)
        B_data = self.toSigned(B_raw, 10)
        Km_data = self.toSigned(Km_raw, 4)
        Kb_data = self.toSigned(Kb_raw, 4)

        return (M_data * int(raw_data, 16) + B_data * math.pow(10, Kb_data)) * math.pow(10, Km_data)

    def webfetch(self):

        POST_LOGIN_URL = "%s://%s/cgi/login.cgi" % (self.PROTO, self.IP)
        REQUEST_URL = "%s://%s/cgi/ipmi.cgi" % (self.PROTO, self.IP)
        LOGOUT_URL = "http://%s/cgi/logout.cgi" % (self.IP)

        payload = {
            "name": self.UNAME,
            "pwd": self.PASSWD
        }

        data = {
            "op": "SENSOR_INFO.XML",
            "SENSOR_INFO.XML": "(1,ff)",
            "r": "(1,ff)",
            "_": ""
        }

        headers = {
            "Referer": "http://%s/cgi/url_redirect.cgi?url_name=servh_sensor" % (self.IP)
        }

        try:

            with requests.Session() as session:

                post = session.post(POST_LOGIN_URL, data=payload, verify=False, timeout=6.0)
                resp = session.post(REQUEST_URL, headers=headers, data=data, verify=False, timeout=6.0)
                logout = session.get(LOGOUT_URL, verify=False, timeout=6.0)

                post.close()
                resp.close()
                logout.close()

        except Exception as e:

            if self.LOG:

                with open("ipmi_poller_err", "a+") as fo:
                    fo.write(str(datetime.datetime.now()) + " " + self.HOSTNAME + " webfetch --> " + str(e) + "\r\n")

            else:

                print(e)

            return None

        return resp.text

    def sensorThreshold(self, sensor):

        _unitId1 = sensor.getAttribute("UNIT1")
        AnalogDataFormat = int(_unitId1, 16) >> 6

        _READING = sensor.getAttribute("READING")

        _UNR = sensor.getAttribute("UNR")
        _UC = sensor.getAttribute("UC")
        _UNC = sensor.getAttribute("UNC")
        _LNC = sensor.getAttribute("LNC")
        _LC = sensor.getAttribute("LC")
        _LNR = sensor.getAttribute("LNR")

        _M = sensor.getAttribute("M")
        _B = sensor.getAttribute("B")
        _RB = sensor.getAttribute("RB")

        RawReading = _READING[0:2]
        ReadingDataFormat = RawReading

        if AnalogDataFormat == 2:

            ReadingDataFormat = str(self.toSigned(int(RawReading, 16), 8))
            _UNR = str(self.toSigned(int(_UNR, 16), 8))
            _UC = str(self.toSigned(int(_UC, 16), 8))
            _UNC = str(self.toSigned(int(_UNC, 16), 8))
            _LNC = str(self.toSigned(int(_LNC, 16), 8))
            _LC = str(self.toSigned(int(_LC, 16), 8))
            _LNR = str(self.toSigned(int(_LNR, 16), 8))

        sensorReading = float(self.bitwise(ReadingDataFormat, _M, _B, _RB))
        sensorUNR = float(self.bitwise(_UNR, _M, _B, _RB))
        sensorUC = float(self.bitwise(_UC, _M, _B, _RB))
        sensorUNC = float(self.bitwise(_UNC, _M, _B, _RB))
        sensorLNC = float(self.bitwise(_LNC, _M, _B, _RB))
        sensorLC = float(self.bitwise(_LC, _M, _B, _RB))
        sensorLNR = float(self.bitwise(_LNR, _M, _B, _RB))

        if self.verbose:
            print(sensorReading, sensorLNR, sensorLC, sensorLNC, sensorUNC, sensorUC, sensorUNR)

        if ((sensorReading <= sensorUNC) and (sensorReading >= sensorLNC)):
            return ['Normal', 'bgcolor=green']

        elif (sensorReading > sensorUNR):
            return ['Upper None-recoverable', 'bgcolor=red']

        elif (sensorReading > sensorUC):
            return ['Upper Critical', 'bgcolor=red']

        elif (sensorReading > sensorUNC):
            return ['Upper Non-critical', 'bgcolor=yellow']

        elif (sensorReading >= sensorLC):
            return ['Lower Non-critical', 'bgcolor=yellow']

        elif (sensorReading >= sensorLNR):
            return ['Lower Non-recoverable', 'bgcolor=red']

        return ['N/A', 'bgcolor=white']

    def sensorValueResolve(self, sensor):

        SensorReadingScale = 1000

        _L = sensor.getAttribute("L")
        _STYPE = sensor.getAttribute("STYPE")
        _M = sensor.getAttribute("M")
        _B = sensor.getAttribute("B")
        _RB = sensor.getAttribute("RB")
        _READING = sensor.getAttribute("READING")
        _eventReadingType = sensor.getAttribute("ERTYPE")

        descr = None
        color = None
        convertValue = None
        state = "Present"

        if _L == "00" and (_STYPE == "01" or _STYPE == "04" or _STYPE == "02" or _STYPE == "c1"):

            valueRaw = _READING[0:2]
            processedValue = self.bitwise(valueRaw, _M, _B, _RB)
            convertValue = (processedValue * SensorReadingScale) / SensorReadingScale

            if _eventReadingType == '01':
                descr, color = self.sensorThreshold(sensor)

            if (valueRaw == '00' and descr == "N/A") or (valueRaw == '00' and _STYPE == '01'):
                state = "Not Present"
                color = "bgcolor=white"

            return [convertValue, descr, color, state]

        elif _L == "08" and (_STYPE == "01" or _STYPE == "04"):

            valueRaw = _READING[0:2]
            processedValue = self.bitwise(valueRaw, _M, _B, _RB)
            convertValue = (math.pow(processedValue, 2) * SensorReadingScale) / SensorReadingScale

            if _eventReadingType == '01':
                descr, color = self.sensorThreshold(sensor)

            if valueRaw == '00' and descr == "N/A" or (valueRaw == '00' and _STYPE == '01'):
                state = "Not Present"
                color = "bgcolor=white"

            return [convertValue, descr, color, state]

        elif _STYPE == "08":

            valueRaw = int(_READING[2:4], 16)
            return self.sensorPSURead(valueRaw)

        elif _STYPE == "05":

            valueRaw = int(_READING[2:4], 16)
            return self.sensorChassisRead(valueRaw)

        elif _STYPE == "0d":

            valueRaw = int(_READING[2:4], 16)
            return self.sensorHDDRead(valueRaw)

        else:
            return _READING

    def sensorProcess(self, _data):

        self.sensorDB = {}

        try:

            doc = minidom.parseString(str(_data))

        except Exception as e:

            if self.LOG:

                with open("ipmi_poller_err", "a+") as fo:

                    fo.write(str(datetime.datetime.now()) + " " + self.HOSTNAME + " minidomparse --> " + str(e) + "\r\n")
                    fo.write(str(datetime.datetime.now()) + " " + self.HOSTNAME + " " + _data + "\r\n")

            else:

                print(e)
                print(_data)

            return None

        self.sensorDB[self.IP] = {
            "hostname": self.HOSTNAME,
            "sensors": []
        }

        Sensors = doc.getElementsByTagName("SENSOR")

        for sensor in Sensors:

            _id = sensor.getAttribute("ID")
            _name = sensor.getAttribute("NAME")
            s_type = self.sensorType(sensor.getAttribute("STYPE"))
            _unitId = sensor.getAttribute("UNIT")

            value = None
            descr = None
            color = None
            state = None
            u_type = None

            if s_type == 'temperature' or s_type == 'fanspeed' or s_type == 'wattage':

                value, descr, color, state = self.sensorValueResolve(sensor)
                value = int(value)
                u_type = self.unitType(_unitId)

            elif s_type == 'voltage':

                value, descr, color, state = self.sensorValueResolve(sensor)
                value = round(value, 3)
                u_type = self.unitType(_unitId)

            elif s_type == 'psu' or s_type == 'chassis' or s_type == "hdd":

                descr, color = self.sensorValueResolve(sensor)

                state = "Not Present" if ("white" in color) else "Present"
                value = 0 if ("green" in color) else 1
                u_type = "boolean"

            elif s_type == 'OEM Sensor':

                value == self.sensorValueResolve(sensor)

                if value is None:
                    state = "Not Present"
                    color = "bgcolor=white"
                    descr = "N/A"
                    value = 0
                    u_type = "N/A"

            if self.verbose:
                print(_name, value, u_type, descr, color, state)

            if any(param for param in [value, descr, color, state, u_type]):

                self.sensorDB[self.IP]['sensors'].append({
                    "id": int(_id, 16),
                    "sensor": _name,
                    "type": s_type,
                    "unit": u_type,
                    "d_value": value,
                    "description": descr,
                    "color": color,
                    "state": state,
                    "hostname": self.HOSTNAME
                })

    def returnServer(self):
        return [server for server in self.sensorDB]

    def returnSensors(self, server):

        if self.state:
            return [sensors for sensors in self.sensorDB[server]['sensors']]

        else:
            return [sensor for sensor in self.sensorDB[server]['sensors'] if sensor['state'] == "Present"]

    def __init__(self, **kwargs):

        self.UNAME = "ADMIN"
        self.PASSWD = "ADMIN"
        self.HOSTNAME = "SMT X9"
        self.state = True
        self.PROTO = "https"
        self.LOG = True
        self.verbose = None

        for key, value in kwargs.items():

            if ("user" in key) and (value):
                self.UNAME = value

            if ("passwd" in key) and (value):
                self.PASSWD = value

            if ("address" in key) and (value):
                self.IP = value

            if ("hostname" in key) and (value):
                self.HOSTNAME = value

            if ("state" in key) and (value):
                self.state = None

            if ("nosecure" in key) and (value):
                self.PROTO = "http"

            if ("nolog" in key) and (value):
                self.LOG = None

            if ("verbose" in key) and (value):
                self.verbose = True


def main():

    parser = argparse.ArgumentParser(description='IPMI Web Scrubber for SMT X9 motherboards')
    parser.add_argument('-H', '--host', metavar="", required=True, help='IP to query against')
    parser.add_argument('-U', '--user', metavar="", required=False, help='Username')
    parser.add_argument('-P', '--password', metavar="", required=False, help='Password')
    parser.add_argument('-N', '--hostname', metavar="", required=False, help='Custom Hostname')
    parser.add_argument('-S', '--state', action='store_true', required=False, help='Omit non active sensors')
    parser.add_argument('-SSL', '--nosecure', action='store_true', required=False, help='Use http instead of https')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-p', '--pretty', action='store_true', help='Print something pretty')
    group.add_argument('-d', '--dump', action='store_true', help='Dumps some xml and json')
    group.add_argument('-v', '--verbose', action='store_true', help='Pretty verbose')
    args = parser.parse_args()

    ipmi = poller(address=args.host, hostname=args.hostname, nolog=True, verbose=args.verbose,
                  state=args.state, user=args.user, passwd=args.password, nosecure=args.nosecure)

    #ipmi = poller(address="192.168.10.32", nolog=True)
    #ipmi = poller(address="192.168.10.181", nolog=True)
    #ipmi = poller(address="172.16.205.212", nolog=True)
    #ipmi = poller(address="172.16.112.147", nolog=True)

    _xml = ipmi.webfetch()

    if _xml:

        if args.verbose:
            print(_xml)

        ipmi.sensorProcess(_xml)

        documents = []

        for host in ipmi.returnServer():
            for sensor in ipmi.returnSensors(host):

                if args.pretty or args.verbose:
                    print(sensor)

                document = {
                    "fields": sensor,
                    "host": host
                }

                documents.append(document)

        if args.dump or args.verbose:
            print(json.dumps(documents, indent=4, sort_keys=False))


if __name__ == '__main__':
    main()
