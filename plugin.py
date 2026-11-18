# Zerdure Python Plugin
#
# Author: HTB
#
"""
<plugin key="Zendure" name="Zendure Plugin" author="HTB" version="1.1.0">
    <description>
        <h2>Zendure</h2><br/>
        Plugin for zendure solarFlow2400AC+.<br/>
        Might work on other zendure products. Not tested.<br/>
        I used https://github.com/Zendure/zenSDK.git to get device names and values.<br/><br/>
        On linux you can use 'avahi-browse --all -r' to get ip address/hostname.<br/>
        Use Zendure-&lt;Model&gt;-&lt;ID&gt;.local as hostname or use the ip address.<br/>
        For solarFlow2400AC+ you have to change the hostname '\043' into a '+'.<br/>
        Use search engine to find how this is done on Windows.<br/><br/>
        When changing device parameters make sure you do not exceed max allowed values.
    </description>
    <params>
        <param field="Address" label="Zendure battery IP Address/Hostname" width="400px" required="true"/>
        <param field="Mode1" label="Polling Interval" width="200px">
            <options>
                <option label="30 seconds" value="30"/>
                <option label="1 minute" value="60"/>
                <option label="2 minutes" value="120"/>
                <option label="3 minutes" value="180"/>
                <option label="4 minutes" value="240"/>
                <option label="5 minutes" value="300" default="true"/>
                <option label="6 minutes" value="360"/>
                <option label="7 minutes" value="420"/>
                <option label="8 minutes" value="480"/>
                <option label="9 minutes" value="540"/>
                <option label="10 minutes" value="600"/>
            </options>
        </param>
        <param field="Mode2" label="Device name prefix" width="200px"/>
        <param field="Mode3" label="Zendure meter IP Address/Hostname" width="400px">
            <description><br/>Parameters below are only needed for price information.<br/>
                              Works only if enever plugin is used.<br/>
                              Leave empty if not used.</description>
        </param>
        <param field="Mode4" label="Domoticz IP Address:Port number" width="400px" required="true" default="127.0.0.1:8080"/>
    </params>
</plugin>
"""
import DomoticzEx as Domoticz
import json
import requests
import time
import math
import datetime
import threading

# 80, 5 = Temperature
# 113, 0 = Counter
# 242, 1 = Setpoint
# 243, 6 = Percentage
# 243, 8 = Voltage
# 243, 19 = Text
# 243, 23 = Current
# 243, 29 = Kwh
# 243, 31 = Custom Sensor
# 244, 62, 18 = Selector Switch
# 244, 73, 0 = Switch, On/Off
# 248, 1 = Usage

# item, [ Unit, Type, Subtype, Switchtype, OptionsList{}, Multiplier, Name ]
# A lot of items are disable because domoticz database increased a lot.

OWN_DEVICES={
    "max_kwh"          :[1,   113,  0,  0, {}, 1, "Maximum Kwh"],
    "cur_kwh"          :[2,   113,  0,  0, {}, 1, "Current Kwh"],
    "in_kwh"           :[3,   243, 29,  0, {'EnergyMeterMode': '1'}, 1, "Input Kwh"],
    "out_kwh"          :[4,   243, 29,  4, {'EnergyMeterMode': '1'}, 1, "Output Kwh"],
    "soc"              :[5,   243,  6,  0, {}, 1, "soc"],
    "charge"           :[6,   248,  1,  0, {}, 1, "charge / discharge"],
    "saving"           :[7,   243, 31,  0, {"Custom": "1;€"}, 0.01, "saving"],
    "total_saving"     :[8,   243, 31,  0, {"Custom": "1;€"}, 0.01, "total saving"],
}

RESPONSE_HEADER={
# Header
#    "timestamp"        :[10,  243, 19,  0, {}, 1, "timestamp"],
#    "messageId"        :[11,  243, 19,  0, {}, 1, "messageId"],
    "sn"               :[12,  243, 19,  0, {}, 1, "Serial Number"],
    "version"          :[13,  243, 19,  0, {}, 1, "Version"],
    "product"          :[14,  243, 19,  0, {}, 1, "Product"],
}

RESPONSE_PROPERTIES={
# Device Data Properties — Read Only
#    "heatState"        :[20,  243, 19,  0, {}, 1, "Heating state"],
    "packInputPower"   :[21,  248,  1,  0, {}, 1, "Battery discharge power"],
    "outputPackPower"  :[22,  248,  1,  0, {}, 1, "Battery charge power"],
#    "outputHomePower"  :[23,  248,  1,  0, {}, 1, "Output to home "],
#    "remainOutTime"    :[24,  243, 19,  0, {}, 1, "Remaining discharge time"],
#    "packState"        :[25,  243, 19,  0, {}, 1, "Pack state"],
#    "packNum"          :[26,  243, 19,  0, {}, 1, "Number of packs"],
#    "electricLevel"    :[27,  243,  6,  0, {}, 1, "Average SOC"],
#    "gridInputPower"   :[28,  248,  1,  0, {}, 1, "Grid input power"],
#    "solarInputPower"  :[29,  248,  1,  0, {}, 1, "Total PV input"],
#    "solarPower1"      :[30,  248,  1,  0, {}, 1, "PV channel power 1"],
#    "solarPower2"      :[31,  248,  1,  0, {}, 1, "PV channel power 2"],
#    "solarPower3"      :[32,  248,  1,  0, {}, 1, "PV channel power 3"],
#    "solarPower4"      :[33,  248,  1,  0, {}, 1, "PV channel power 4"],
#    "solarPower5"      :[34,  248,  1,  0, {}, 1, "PV channel power 5"],
#    "solarPower6"      :[35,  248,  1,  0, {}, 1, "PV channel power 6"],
#    "pass"             :[36,  243, 19,  0, {}, 1, "Pass-through state"],
#    "reverseState"     :[37,  243, 19,  0, {}, 1, "Reverse flow state"],
#    "socStatus"        :[38,  243, 19,  0, {}, 1, "SOC calibration"],
    "hyperTmp"         :[39,   80,  5,  0, {}, 1, "Enclosure temperature"],
#    "dcStatus"         :[40,  243, 19,  0, {}, 1, "DC state"],
#    "pvStatus"         :[41,  243, 19,  0, {}, 1, "PV state"],
#    "acStatus"         :[42,  243, 19,  0, {}, 1, "AC state"],
#    "dataReady"        :[43,  243, 19,  0, {}, 1, "Data ready flag"],
#    "gridState"        :[44,  243, 19,  0, {}, 1, "Grid connection state"],
    "BatVolt"          :[45,  243,  8,  0, {}, 0.01, "Battery voltage"],
#    "FMVolt"           :[46,  243, 19,  0, {}, 1, "Voltage activation value"],
#    "socLimit"         :[47,  243, 19,  0, {}, 1, "SOC limit state"],
#    "rssi"             :[48,  243, 19,  0, {}, 1, "Signal strength"],
#    "gridOffPower"     :[49,  248,  1,  0, {}, 1, "Off-grid power"],
#    "lampSwitch"       :[50,  243, 19,  0, {}, 1, "Lamp state"],
#    "IOTState"         :[51,  243, 19,  0, {}, 1, "IoT connection"],
#    "fanSwitch"        :[52,  243, 19,  0, {}, 1, "Fan state"],
#    "fanSpeed"         :[53,  243, 19,  0, {}, 1, "Fan level"],
#    "faultLevel"       :[54,  243, 19,  0, {}, 1, "Fault severity"],
#    "bindstate"        :[55,  243, 19,  0, {}, 1, "Bind state"],
#    "VoltWakeup"       :[56,  243,  8,  0, {}, 1, "Voltage wake-up"],
#    "OldMode"          :[57,  243, 19,  0, {}, 1, "Legacy mode"],
#    "OTAState"         :[58,  243, 19,  0, {}, 1, "OTA state"],
#    "LCNState"         :[59,  243, 19,  0, {}, 1, "LCN state"],
#    "factoryModeState" :[60,  243, 19,  0, {}, 1, "Factory mode"],
#    "timestamp"        :[61,  243, 19,  0, {}, 1, "System timestamp"],
#    "ts"               :[62,  243, 19,  0, {}, 1, "Unix timestamp"],
#    "timeZone"         :[63,  243, 19,  0, {}, 1, "Timezone"],
#    "tsZone"           :[64,  243, 19,  0, {}, 1, "Timezone offset"],
    "chargeMaxLimit"   :[65,  248,  1,  0, {}, 1, "Max charge power"],
#    "phaseSwitch"      :[66,  243, 19,  0, {}, 1, "Phase switch"],
#    "is_error"         :[67,  243, 19,  0, {}, 1, "Error flag"],
#| Bit | Meaning |
#|-----|--------|
#| Bit0 | AC-coupled input present, auto-cleared by DSP |
#| Bit1 | AC input present flag |
#| Bit2 | AC-coupled overload |
#| Bit3 | Excess AC input power |
#    "acCouplingState"  :[68, 243, 19,  0, {}, 1, "AC Coupling State"],
#    "dryNodeState"     :[69, 243, 19,  0, {}, 1, "Dry contact status"],

# Device Data Properties — Read / Write
#    "writeRsp"         :[70,  243, 19,  0, {}, 1, "Write response"],
    "acMode"           :[71,  244, 62, 18, {"LevelActions":"|", "LevelNames":"input|output", "LevelOffHidden":"false", "SelectorStyle":"0"}, 1, "Charge or discharge mode"],
    "inputLimit"       :[72,  242,  1,  0, {'ValueStep':'1', 'ValueMin':'0',  'ValueMax':'2400', 'ValueUnit':'W'}, 1, "AC charge limit"],
    "outputLimit"      :[73,  242,  1,  0, {'ValueStep':'1', 'ValueMin':'0',  'ValueMax':'3200', 'ValueUnit':'W'}, 1, "Output limit"],
    "socSet"           :[74,  242,  1,  0, {'ValueStep':'1', 'ValueMin':'70', 'ValueMax':'100', 'ValueUnit':'%'}, 0.1, "Target SOC"],
    "minSoc"           :[75,  242,  1,  0, {'ValueStep':'1', 'ValueMin':'10',  'ValueMax':'50',   'ValueUnit':'%'}, 0.1, "Minimum SOC"],
    "gridReverse"      :[76,  244, 62, 18, {"LevelActions":"||", "LevelNames":"disabled|allow|forbidden", "LevelOffHidden":"false", "SelectorStyle":"0"}, 1, "Reverse flow control"],
    "inverseMaxPower"  :[77,  242,  1,  0, {'ValueStep':'1', 'ValueMin':'0',  'ValueMax':'2400', 'ValueUnit':'W'}, 1, "Max inverter output"],
#    "gridStandard"     :[78,  244, 62, 18, {"LevelActions":"|||||||||", "LevelNames":"Germany|France|Austria|Switzerland|Netherlands|Spain|Belgium|Greece|Denmark|Italy", "LevelOffHidden":"false", "SelectorStyle":"1"}, 1, "Country"],
# 1: Parameters are not written to flash
# Device restores previous flash values after reboot
# Recommended for frequent configuration changes
#    "smartMode"        :[79,  244, 73,  0, {}, 1, "Flash write behavior"],
#    "batCalTime"       :[80,  243, 19,  0, {}, 1, "BatCalTime(minutes). Unauthorized modifications are not recommended"],
#    "Fanmode"          :[81,  243, 19,  0, {}, 1, "Fanmode. Unauthorized modification is not recommended"],
#    "Fanspeed"         :[82,  243, 19,  0, {}, 1, "Fanspeed. Unauthorized modification is not recommended"],
#    "gridOffMode"      :[83,  244, 62, 18, {"LevelActions":"||", "LevelNames":"normal|eco|off", "LevelOffHidden":"false", "SelectorStyle":"0"}, 1, "Grid Off Mode"],
}

RESPONSE_SIZE = 20

RESPONSE_PACK_DATA={
# Battery Pack Data Properties
    "sn"               :[100, 243, 19,  0, {}, 1, "Serial Number"],
#    "packType"         :[101, 243, 19,  0, {}, 1, "pack Type"],
#    "socLevel"         :[102, 243,  6,  0, {}, 1, "State of charge"],
#    "state"            :[103, 243, 19,  0, {}, 1, "State"],
#    "power"            :[104, 248,  1,  0, {}, 1, "Battery pack power"],
# float maxTemp_C = (maxTemp - 2731) / 10.0;
#    "maxTemp"          :[105,  80,  5,  0, {}, 1, "Stored temperature value"],
#    "totalVol"         :[106, 243,  8,  0, {}, 0.01, "Total voltage"],
# Raw format: 16-bit two’s complement
# Source container: uint8_t[3]
# Convert to signed int16
# current_A = value / 10.0;
#    "batcur"           :[107, 243, 23,  0, {}, 1, "Battery current"],
#    "maxVol"           :[108, 243,  8,  0, {}, 0.01, "Max cell voltage"],
#    "minVol"           :[109, 243,  8,  0, {}, 0.01, "Min cell voltage "],
    "softVersion"      :[110, 243, 19,  0, {}, 1, "Firmware version"],
}

class ZendurePlugin:
    enabled = False
    def __init__(self):
        return

    def onStart(self):
        # Domoticz.Log("onStart called")
        self.address = Parameters["Address"]
        self.pollingInterval = int(Parameters["Mode1"])
        self.heartbeatWaits = int(self.pollingInterval / 30)
        self.heartbeatCount = 0
        self.busy = False
        Domoticz.Heartbeat(self.pollingInterval if self.pollingInterval <= 30 else 30)
        self.prefix = str(Parameters["Mode2"])
        self.meter = Parameters["Mode3"]
        self.domoticz = Parameters["Mode4"]
        self.max_kwh = 0
        self.cur_kwh = 0
        self.ac_mode = 0
        self.max_input = 0
        self.max_output = 0
        self.max_soc = 0
        self.min_soc = 0
        self.charge_power = 0
        self.discharge_power = 0
        self.input_limit = 0
        self.output_limit = 0
        self.last_kwh = -1
        self.last_time = -1
        self.in_kwh = 0
        self.out_kwh = 0
        self.soc = 0
        self.charge = 0
        self.saving = 0
        self.total_saving = 0
        self.sn = "???"
        self.product = "???"
        self.version = "???"
        self.pack_sn = []
        self.pack_firmware = []
        self.pack_name = []
        self.pack_model = []
        self.pack_kwh = []
        self.Hwid = Parameters['HardwareID']
        self.maxPack = 0
        self.zendure_start = 0
        # enever
        self.enever = -1
        self.provider = ""
        self.price = []
        # zendure meter:
        self.power = 0
        self.last_a_aprt_power = 1e30
        self.last_b_aprt_power = 1e30
        self.last_c_aprt_power = 1e30

        # Skip values that are not present in response message.
        # This allows maybe other devices then solarFlow2400AC+ to work.
        for i in range(3):
            ok, response = self.zendure_get_battery(1)
            if ok:
                break
        if ok:
            try:
                self.maxPack = len(response["packData"])
                unit_max = 0
                for Dev in RESPONSE_PACK_DATA:
                    if RESPONSE_PACK_DATA[Dev][0] > unit_max:
                        unit_max = RESPONSE_PACK_DATA[Dev][0]
                unit_max += (self.maxPack - 1) * RESPONSE_SIZE
                present=[0]
                for i in range(unit_max):
                    present.append(0)
                for header in response:
                    if RESPONSE_HEADER.get(header) != None:
                        present[RESPONSE_HEADER[header][0]] = 1
                for properties in response["properties"]:
                    if RESPONSE_PROPERTIES.get(properties) != None:
                        present[RESPONSE_PROPERTIES[properties][0]] = 1
                for pack in range(self.maxPack):
                    for packData in response["packData"][pack]:
                        if RESPONSE_PACK_DATA.get(packData) != None:
                            present[RESPONSE_PACK_DATA[packData][0] + pack * RESPONSE_SIZE] = 1
            except:
                ok = False
        if ok == False:
            Domoticz.Error("Battery not found. No devices are created")
            return

        for own in OWN_DEVICES:
            dev = OWN_DEVICES[own]
            DeviceID = "{:04x}{:04x}".format(self.Hwid, dev[0])
            if DeviceID not in Devices:
                Domoticz.Unit(DeviceID=DeviceID, Unit=dev[0], Name=self.prefix + dev[6], Type=dev[1], Subtype=dev[2], Switchtype=dev[3], Options=dev[4], Used=1).Create()
        for header in RESPONSE_HEADER:
            dev = RESPONSE_HEADER[header]
            DeviceID = "{:04x}{:04x}".format(self.Hwid, dev[0])
            if DeviceID not in Devices and present[dev[0]] == 1:
                Domoticz.Unit(DeviceID=DeviceID, Unit=dev[0], Name=self.prefix + dev[6], Type=dev[1], Subtype=dev[2], Switchtype=dev[3], Options=dev[4], Used=1).Create()
        for properties in RESPONSE_PROPERTIES:
            dev = RESPONSE_PROPERTIES[properties]
            DeviceID = "{:04x}{:04x}".format(self.Hwid, dev[0])
            if DeviceID not in Devices and present[dev[0]] == 1:
                Domoticz.Unit(DeviceID=DeviceID, Unit=dev[0], Name=self.prefix + dev[6], Type=dev[1], Subtype=dev[2], Switchtype=dev[3], Options=dev[4], Used=1).Create()
        for pack in range(self.maxPack):
            for packData in RESPONSE_PACK_DATA:
                dev = RESPONSE_PACK_DATA[packData]
                unit = dev[0] + pack * RESPONSE_SIZE
                DeviceID = "{:04x}{:04x}".format(self.Hwid, unit)
                if DeviceID not in Devices and present[unit] == 1:
                    Domoticz.Unit(DeviceID=DeviceID, Unit=unit, Name=self.prefix + dev[6] + "[" + str(pack) + "]", Type=dev[1], Subtype=dev[2], Switchtype=dev[3], Options=dev[4], Used=1).Create()

        try:
            self.saving = float(self.zendure_get_value("saving")) * 100
            self.total_saving = float(self.zendure_get_value("total_saving")) * 100
            # Domoticz.Log("saving: " + str(self.saving / 100) + " " + str(self.total_saving / 100))
        except:
            self.saving = 0
            self.total_saving = 0

        if ok:
            self.zendure_process(response)
            self.zendure_update_all(response)

        Domoticz.Log("Product: " + self.product + ", Serial Number: " + self.sn + ", Version: " + self.version)
        for i in range(len(self.pack_sn)):
            Domoticz.Log("Package: " + self.pack_name[i] + " " + self.pack_model[i] + ", Kwh: " + str(self.pack_kwh[i]) + ", Serial Number: " + self.pack_sn[i] + ", firmware Version: " + self.pack_firmware[i])

        if self.meter.strip() != '':
            for i in range(3):
                ok, meter = self.zendure_get_meter(1)
                if ok:
                    break
            if ok == False:
                Domoticz.Error("Meter not found.")
                self.meter = ''

        if self.meter.strip() != '':
            # Check for enever price feed
            ok, hardware = self.domoticz_get("type=command&param=gethardware")
            if ok:
                hardware = hardware["result"]
                for hw in range(len(hardware)):
                    # main/RFXNames.h: HTYPE_EneverPriceFeeds, //105
                    if hardware[hw]["Type"] == 105:
                        self.enever = hardware[hw]["idx"]
                        self.provider = hardware[hw]["Extra"].split(";")[0]
            if self.enever == -1:
                self.meter = ''
            Domoticz.Log("Enever price feed " + ("not found." if self.enever == -1 else "found."))

        if self.meter.strip() != '':
            self.zendure_start = 1
            self.zendure_sem = threading.Semaphore(value = 0)
            self.zendure_thread = threading.Thread(name="ZendureThread", target=self.zendure_thread)
            self.zendure_thread.start()

    def onStop(self):
        Domoticz.Log("onStop called")
        if self.zendure_start != 0:
            self.zendure_sem.release()
            self.zendure_thread.join()

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called")

    def onCommand(self, DeviceID, Unit, Command, Level, Color):
        # Domoticz.Log("onCommand called for Device " + str(DeviceID) + " Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        for dev in RESPONSE_PROPERTIES:
            if RESPONSE_PROPERTIES[dev][0] == Unit:
                result = False
                if (Command == "Off" or Command == "On") and dev == "smartMode":
                    Level = 1 if Command == "On" else 0
                    result = self.zendure_post(dev, Level)
                elif (Command == "Off" or Command == "Set Level") and dev == "acMode":
                    result = self.zendure_post(dev, 1 if Level == 0 else 2)
                elif (Command == "Off" or Command == "Set Level") and (dev == "gridReverse" or dev == "gridStandard" or dev == "gridOffMode"):
                    result = self.zendure_post(dev, Level / 10)
                elif Command == "Set Level" and (dev == "inputLimit" or dev == "outputLimit" or dev == "inverseMaxPower"):
                    result = self.zendure_post(dev, Level)
                elif Command == "Set Level" and (dev == "socSet" or dev == "minSoc"):
                    result = self.zendure_post(dev, Level * 10)
                if result and (Devices[DeviceID].Units[Unit].nValue != int(Level) or Devices[DeviceID].Units[Unit].sValue != str(Level)):
                    Devices[DeviceID].Units[Unit].nValue = int(Level)
                    Devices[DeviceID].Units[Unit].sValue = str(Level)
                    Devices[DeviceID].Units[Unit].Update()

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        # Domoticz.Log("onHeartbeat called")
        if self.meter.strip() == '':
            self.heartbeatCount += 1
            if self.busy and self.heartbeatCount < 5: # Wait some more if busy. Max 5 times
                return
            else:
                if self.heartbeatCount >= self.heartbeatWaits:
                    self.heartbeatCount = 0
                    self.busy = True
                    ok, response = self.zendure_get_battery(0)
                    if ok:
                        self.zendure_process(response)
                        self.zendure_update_all(response)
                    self.busy = False

    def zendure_thread(self):
        try:
            first = True;
            enable = True;
            alpha = 0.001
            background = 0
            last_time = time.time()
            while True:
                start_time = time.time()
                now = time.localtime(start_time)
                hour = now.tm_hour
                minute = now.tm_min
                # Domoticz.Log("zendure thread: " + str(datetime.datetime.now()))
                if self.zendure_sem.acquire(blocking = False):
                    Domoticz.Log("Exiting zendure thread")
                    break

                # enever updates parameter at 00:00
                if enable and (first or (hour == 0 and minute == 1)):
                    ok, parameters = self.domoticz_get("type=command&param=getuservariables")
                    if ok:
                        today = []
                        parameters = parameters["result"]
                        for param in range(len(parameters)):
                            if parameters[param]["Name"] == "Enever_Electricity_" + self.enever:
                                today = json.loads(parameters[param]["Value"])["data"]
                        self.price = []
                        size = len(today)
                        resolution = size / 24 if size >= 24 else 1
                        for i in range(size):
                            for j in range(int(4 / resolution)):
                                self.price.append(float(today[i]["prijs" + self.provider]))
                        
                        self.heartbeatCount = self.pollingInterval

                        if first == False:
                            self.total_saving += self.saving
                            self.saving = 0
                        enable = False
                        first = False

                elif hour != 0:
                    enable = True

                ok, response = self.zendure_get_battery(0)
                if ok:
                    self.heartbeatCount += 1
                    self.zendure_process(response)
                    if self.heartbeatCount >= self.pollingInterval:
                        self.heartbeatCount = 0
                        self.zendure_update_all(response)

                if ok and len(self.price) >= 96 and self.zendure_get_power():
                    if self.charge == 0:
                        background = background * (1 - alpha) + self.power * alpha

                    current_price = self.price[int(hour * 4) + int(minute / 15)]
                    delta = current_price * (start_time - last_time) / 3600 / 1000 * 100 # in cents
                    last_time = start_time;
                    if self.charge >= 0:
                        # charge
                        actual_power = self.power - background
                        if actual_power >= 0 and actual_power < self.charge:
                            self.saving -= actual_power * delta
                        elif actual_power >= self.charge:
                            self.saving -= self.charge * delta
                    else:
                        # discharge
                        self.saving -= self.charge * delta
                    # Domoticz.Log("zendure thread: saving " + str(self.saving / 100) + ", backgound " + str(background))

                delta = 1 - (time.time() - start_time)
                time.sleep(delta if delta > 0 else 1)
        except Exception as err:
            Domoticz.Error("Zendure_thread exception: " + str(err))

    def zendure_process(self, response):
        self.sn = str(response.get("sn"))
        self.product = str(response.get("product"))
        self.version = str(response.get("version"))

        if response.get("properties") != None:
            self.ac_mode = 0
            self.max_input = 0
            self.max_output = 0
            self.max_soc = 0
            self.min_soc = 0
            self.charge_power = 0
            self.discharge_power = 0
            self.input_limit = 0
            self.output_limit = 0
            self.charge = 0
            if (response["properties"].get("acMode") != None and
                response["properties"].get("chargeMaxLimit") != None and
                response["properties"].get("inverseMaxPower") != None and
                response["properties"].get("socSet") != None and
                response["properties"].get("minSoc") != None and
                response["properties"].get("outputPackPower") != None and
                response["properties"].get("packInputPower") != None and
                response["properties"].get("inputLimit") != None and
                response["properties"].get("outputLimit") != None):
                self.ac_mode = response["properties"]["acMode"]
                self.max_input = float(response["properties"]["chargeMaxLimit"])
                self.max_output = float(response["properties"]["inverseMaxPower"])
                self.max_soc = float(response["properties"]["socSet"]) / 10.0
                self.min_soc = float(response["properties"]["minSoc"]) / 10.0
                self.charge_power  = float(response["properties"]["outputPackPower"])
                self.discharge_power = float(response["properties"]["packInputPower"])
                self.input_limit  = float(response["properties"]["inputLimit"])
                self.output_limit = float(response["properties"]["outputLimit"])

            if response["properties"].get("heatState") != None:
               response["properties"].update({"heatState": "on" if response["properties"].get("heatState") else "off"})
            if response["properties"].get("pass") != None:
               response["properties"].update({"pass": "off" if response["properties"].get("pass") == 0 else
                                              "Grid direct supply" if response["properties"].get("pass") == 3 else "on"})
            if response["properties"].get("reverseState") != None:
               response["properties"].update({"reverseState": "on" if response["properties"].get("reverseState") else "off"})
            if response["properties"].get("socStatus") != None:
               response["properties"].update({"socStatus": "on" if response["properties"].get("socStatus") else "off"})
            if response["properties"].get("hyperTmp") != None:
               response["properties"].update({"hyperTmp": (response["properties"].get("hyperTmp") - 2731) / 10.0})
            if response["properties"].get("lampSwitch") != None:
               response["properties"].update({"lampSwitch": "on" if response["properties"].get("lampSwitch") else "off"})
            if response["properties"].get("fanSwitch") != None:
               response["properties"].update({"fanSwitch": "on" if response["properties"].get("fanSwitch") else "off"})
            if response["properties"].get("fanSpeed") != None:
               response["properties"].update({"fanSpeed": "normal" if response["properties"].get("fanSpeed") == 1 else
                                                          "fast" if response["properties"].get("fanSpeed") else "auto"})
            if response["properties"].get("is_error") != None:
               response["properties"].update({"is_error": "on" if response["properties"].get("is_error") else "off"})
            if response["properties"].get("Fanmode") != None:
               response["properties"].update({"Fanmode": "on" if response["properties"].get("Fanmode") else "off"})
            if response["properties"].get("Fanspeed") != None:
               response["properties"].update({"Fanspeed": "normal" if response["properties"].get("Fanspeed") == 1 else
                                                          "fast" if response["properties"].get("Fanspeed") else "auto"})
            if response["properties"].get("outputPackPower") != None and response["properties"].get("packInputPower") != None:
                self.charge = float(response["properties"]["outputPackPower"]) - float(response["properties"]["packInputPower"])

        if response.get("packData") != None:
            self.max_kwh = 0
            self.cur_kwh = 0
            self.soc = 0
            self.pack_sn = []
            self.pack_firmware = []
            self.pack_name = []
            self.pack_model = []
            self.pack_kwh = []
            for pack in range(len(response["packData"])):
                if response["packData"][pack].get("state") != None:
                   response["packData"][pack].update({"state": "Charging" if response["packData"][pack].get("state") == 1 else
                                                               "Discharging" if response["packData"][pack].get("state") else "Standby"})
                if response["packData"][pack].get("maxTemp") != None:
                   response["packData"][pack].update({"maxTemp": (response["packData"][pack].get("maxTemp") - 2731) / 10.0})
                if response["packData"][pack].get("batcur") != None:
                   response["packData"][pack].update({"batcur": (((response["packData"][pack].get("batcur") & 65535) ^ 32768) - 32768) / 10.0})
                name, model, kwh = self.get_battery_type(response["packData"][pack].get("sn"))
                self.pack_sn.append(str(response["packData"][pack].get("sn")))
                self.pack_firmware.append(str(response["packData"][pack].get("softVersion")))
                self.pack_name.append(name)
                self.pack_model.append(model)
                self.pack_kwh.append(kwh)
                self.max_kwh += kwh
                if response["packData"][pack].get("socLevel") != None:
                    self.cur_kwh += kwh * float(response["packData"][pack]["socLevel"]) / 100
            if self.max_kwh != 0:
                self.soc = self.cur_kwh / self.max_kwh * 100
            if self.last_kwh != -1:
                delta = self.cur_kwh - self.last_kwh
                if delta >= 0:
                    self.in_kwh += delta
                else:
                    self.out_kwh += -delta
            self.last_kwh = self.cur_kwh

    def zendure_update_all(self, response):
        cur_time = time.time()
        if self.last_time != -1 and cur_time != self.last_time:
            self.in_kwh *= 3600 / (cur_time - self.last_time)
            self.out_kwh *= 3600 / (cur_time - self.last_time)
        self.last_time = cur_time
        for own in OWN_DEVICES:
            dev = OWN_DEVICES[own]
            match own:
                case "max_kwh":
                    value = self.max_kwh * 1000
                case "cur_kwh":
                    value = self.cur_kwh * 1000
                case "in_kwh":
                    value = str(self.in_kwh * 1000) + ";0"
                case "out_kwh":
                    value = str(self.out_kwh * 1000) + ";0"
                case "soc":
                    value = self.soc
                case "charge":
                    value = self.charge
                case "saving":
                    value = self.saving
                case "total_saving":
                    value = self.total_saving
            self.zendure_update(own, dev[0], dev[1], dev[2], dev[5], value)
        self.in_kwh = 0
        self.out_kwh = 0
        for header in response:
            if RESPONSE_HEADER.get(header) != None:
                dev = RESPONSE_HEADER[header]
                self.zendure_update(header, dev[0], dev[1], dev[2], dev[5], response[header])
        if response.get("properties") != None:
            for properties in response["properties"]:
                if RESPONSE_PROPERTIES.get(properties) != None:
                    dev = RESPONSE_PROPERTIES[properties]
                    self.zendure_update(properties, dev[0], dev[1], dev[2], dev[5], response["properties"][properties])
        if response.get("packData") != None:
            for pack in range(len(response["packData"])):
                for packData in response["packData"][pack]:
                    if RESPONSE_PACK_DATA.get(packData) != None:
                        dev = RESPONSE_PACK_DATA[packData]
                        self.zendure_update(packData, dev[0] + pack * RESPONSE_SIZE, dev[1], dev[2], dev[5], response["packData"][pack][packData])

    def roundValue(self, val, digits):
        scale = 10**-digits
        return round(math.floor((val + (scale / 2)) / scale) * scale, digits)

    def zendure_update(self, name, Unit, Type, Subtype,  multiplier, value):
        DeviceID = "{:04x}{:04x}".format(self.Hwid, Unit)

        update = True
        if ((Type == 243 and Subtype == 19) or     # Text
            (Type == 243 and Subtype == 29)):      # Kwh
            nValue = 0
            sValue = str(value)
        elif (Type == 80 or                       # Temperature
              Type == 113 or                      # Counter
              Type == 242 or                      # Setpoint
              Type == 248 or                      # Usage
              (Type == 243 and Subtype == 6) or   # Percentage
              (Type == 243 and Subtype == 8) or   # Voltage
              (Type == 243 and Subtype == 23)):   # Current
            value = self.roundValue(float(multiplier * value), 0 if multiplier == 1 else 2)
            nValue = int(value)
            sValue = str(value)
        elif (Type == 243 and Subtype == 31):     # Custom Sensor
            value = self.roundValue(float(multiplier * value), 0 if multiplier == 1 else 2)
            nValue = 0
            sValue = str(value)
        elif Type == 244:                         # Selector Switch, Switch, On/Off
            if name != "smartMode":
                if name == "acMode":
                    value -= 1
                value *= 10
            nValue = int(value)
            sValue = str(value)
        else:
            update = False
        if update and (Devices[DeviceID].Units[Unit].nValue != nValue or Devices[DeviceID].Units[Unit].sValue != sValue):
            Devices[DeviceID].Units[Unit].nValue = nValue
            Devices[DeviceID].Units[Unit].sValue = sValue
            Devices[DeviceID].Units[Unit].Update()

    def zendure_get_value(self, name):
        dev = OWN_DEVICES[name]
        DeviceID = "{:04x}{:04x}".format(self.Hwid, dev[0])
        return Devices[DeviceID].Units[dev[0]].sValue

    def zendure_get_power(self):
        self.power = 0
        ok, meter = self.zendure_get_meter(0)
        if ok:
            # check if 1 second(new meter) or 10 second(old meter) update interval
            ret = meter["a_aprt_power"] != self.last_a_aprt_power or meter["b_aprt_power"] != self.last_b_aprt_power or meter["c_aprt_power"] != self.last_c_aprt_power
            self.last_a_aprt_power = meter["a_aprt_power"]
            self.last_b_aprt_power = meter["b_aprt_power"]
            self.last_c_aprt_power = meter["c_aprt_power"]
            self.power = self.last_a_aprt_power + self.last_b_aprt_power + self.last_c_aprt_power
            return ret
        return False

    def domoticz_get(self, request):
        try:
            get_response = requests.get("http://" + self.domoticz + "/json.htm?" + request, timeout=2)
            response = json.loads(get_response.text)
            return True, response
        except:
            Domoticz.Error("Errors in getting domoticz data. Check results.\n")
            return False, ""

    def zendure_get_meter(self, ignore):
        if self.meter.strip() == '':
            return False, ""
        try:
            get_response = requests.get("http://" + self.meter + "/properties/report", timeout=2)
            response = json.loads(get_response.text)
            return True, response
        except:
            if ignore == 0:
                Domoticz.Error("Errors in getting Zendure data. Check results.")
            return False, ""

    def zendure_get_battery(self, ignore):
        try:
            get_response = requests.get("http://" + self.address + "/properties/report", timeout=2)
            response = json.loads(get_response.text)
            return True, response
        except:
            if ignore == 0:
                Domoticz.Error("Errors in getting Zendure data. Check results.")
            return False, ""

    def zendure_post(self, item, value):
        try:
            value = round(value, 0)
            post_response = requests.post("http://" + self.address + "/properties/write", json={"sn": self.sn, "properties": {str(item): value}}, timeout=2)
            response = json.loads(post_response.text)
            return response["success"]
        except:
            Domoticz.Error("Errors in setting Zendure data. Check results.")
            return False

    # imported from https://github.com/Zendure/Zendure-HA.git
    def get_battery_type(self, sn):
        kWh = 0
        model = "???"
        match sn[0]:
            case "A":
                if sn[3] == "3":
                    model = "AIO2400"
                    kWh = 2.4
                else:
                    model = "AB1000"
                    kWh = 0.96
            case "B":
                # packType 70 is the SF4000 Mix AC+'s internal 8 kWh pack, which shares
                # its serial prefix with the unrelated 0.96 kWh AB1000S.
                if pack_type == 70:
                    model = "I8000"
                    kWh = 8.0
                else:
                    model = "AB1000S"
                    kWh = 0.96
            case "C":
                # External AB2000X and internal AB2000X of SF800+/SF800Pro/SF1600AC+ starting with CO4A. They are also described as additional battery in the Zendure App, even when they are integrated into the device.
                model = "AB2000" + ("S" if sn[3] == "F" else "X" if sn[3] == "E" else "")
                kWh = 1.92
            case "F":
                model = "AB3000"
                kWh = 2.88
            case "G":
                model = "AB3000L"
                kWh = 2.88
            case "J":
                # JO2A => internal battery of SF2400AC pro
                # JO4A => internal battery of SF2400AC+
                model = "I2400"
                kWh = 2.4
            case _:
                model = "Unknown"
                kWh = 0.0

        name = f"{model} {sn[-5:]}".strip()
        return name, model, kWh

global _plugin
_plugin = ZendurePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(DeviceID, Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(DeviceID, Unit, Command, Level, Color)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for DeviceName in Devices:
        Device = Devices[DeviceName]
        Domoticz.Debug("Device ID:       '" + str(Device.DeviceID) + "'")
        Domoticz.Debug("--->Unit Count:      '" + str(len(Device.Units)) + "'")
        for UnitNo in Device.Units:
            Unit = Device.Units[UnitNo]
            Domoticz.Debug("--->Unit:           " + str(UnitNo))
            Domoticz.Debug("--->Unit Name:     '" + Unit.Name + "'")
            Domoticz.Debug("--->Unit nValue:    " + str(Unit.nValue))
            Domoticz.Debug("--->Unit sValue:   '" + Unit.sValue + "'")
            Domoticz.Debug("--->Unit LastLevel: " + str(Unit.LastLevel))
    return
