# Zerdure Python Plugin
#
# Author: HTB
#
"""
<plugin key="Zendure" name="Zendure Plugin" author="HTB" version="1.0.0">
    <description>
        <h2>Zendure</h2><br/>
        Plugin for zendure solarFlow2400AC+.<br/>
        Might work on other zendure products. Not tested.<br/>
        I used https://github.com/Zendure/zenSDK.git to get device names and values.<br/><br/>
        On linux you can use 'avahi-browse --all -r' to get ip address/hostname.<br/>
        Use Zendure-&lt;Model&gt;-&lt;ID&gt;.local as hostname or use the ip address.<br/>
        For solarFlow2400AC+ you have to change the hostname '\043' into a '+'.<br/>
        Do not use Zendure-MeterReader-&lt;ID&gt;.local<br/>
        Use search engine to find how this is done on Windows.<br/><br/>
        When changing device parameters make sure you do not exceed max allowed values.
    </description>
    <params>
        <param field="Address" label="Zendure IP Address/Hostname" width="400px" required="true"/>
        <param field="Mode1" label="Polling Interval" width="200px">
            <options>
                <option label="30 seconds" value="30"/>
                <option label="1 minute" value="60"/>
                <option label="2 minutes" value="120" default="true"/>
                <option label="3 minutes" value="180"/>
                <option label="4 minutes" value="240"/>
                <option label="5 minutes" value="300"/>
            </options>
        </param>
        <param field="Mode2" label="Device name prefix" width="200px"/>
    </params>
</plugin>
"""
import DomoticzEx as Domoticz
import json
import requests

# 80, 50 = Temperature
# 113, 0 = Counter
# 242, 1 = Setpoint
# 243, 6 = Percentage
# 243, 8 = Voltage
# 243, 19 = Text
# 243, 23 = Current
# 243, 29 = Kwh
# 244, 62, 18 = Selector Switch
# 244, 73, 0 = Switch, On/Off
# 248, 1 = Usage

# item, [ Unit, Type, Subtype, Switchtype, OptionsList{}, Multiplier, Name, Used ]

OWN_DEVICES={
    "max_kwh"          :[1,   113,  0,  0, {}, 1, "Maximum Kwh", 1],
    "cur_kwh"          :[2,   113,  0,  0, {}, 1, "Current Kwh", 1],
    "in_kwh"           :[3,   243, 29,  0, {'EnergyMeterMode': '1'}, 1, "Input Kwh", 1],
    "out_kwh"          :[4,   243, 29,  4, {'EnergyMeterMode': '1'}, 1, "Output Kwh", 1],
    "soc"              :[5,   243,  6,  0, {}, 1, "soc", 1],
    "charge"           :[6,   248,  1,  0, {}, 1, "charge / discharge", 1],
}

RESPONSE_HEADER={
# Header
#    "timestamp"        :[10,  243, 19,  0, {}, 1, "timestamp", 1],
#    "messageId"        :[11,  243, 19,  0, {}, 1, "messageId", 1],
    "sn"               :[12,  243, 19,  0, {}, 1, "Serial Number", 1],
    "version"          :[13,  243, 19,  0, {}, 1, "Version", 1],
    "product"          :[14,  243, 19,  0, {}, 1, "Product", 1],
}

RESPONSE_PROPERTIES={
# Device Data Properties — Read Only
    "heatState"        :[20,  243, 19,  0, {}, 1, "Heating state", 1],
    "packInputPower"   :[21,  248,  1,  0, {}, 1, "Battery discharge power", 1],
    "outputPackPower"  :[22,  248,  1,  0, {}, 1, "Battery charge power", 1],
    "outputHomePower"  :[23,  248,  1,  0, {}, 1, "Output to home ", 1],
    "remainOutTime"    :[24,  243, 19,  0, {}, 1, "Remaining discharge time", 1],
    "packState"        :[25,  243, 19,  0, {}, 1, "Pack state", 1],
    "packNum"          :[26,  243, 19,  0, {}, 1, "Number of packs", 1],
    "electricLevel"    :[27,  243,  6,  0, {}, 1, "Average SOC", 1],
    "gridInputPower"   :[28,  248,  1,  0, {}, 1, "Grid input power", 1],
    "solarInputPower"  :[29,  248,  1,  0, {}, 1, "Total PV input", 0],
    "solarPower1"      :[30,  248,  1,  0, {}, 1, "PV channel power 1", 0],
    "solarPower2"      :[31,  248,  1,  0, {}, 1, "PV channel power 2", 0],
    "solarPower3"      :[32,  248,  1,  0, {}, 1, "PV channel power 3", 0],
    "solarPower4"      :[33,  248,  1,  0, {}, 1, "PV channel power 4", 0],
    "solarPower5"      :[34,  248,  1,  0, {}, 1, "PV channel power 5", 0],
    "solarPower6"      :[35,  248,  1,  0, {}, 1, "PV channel power 6", 0],
    "pass"             :[36,  243, 19,  0, {}, 1, "Pass-through state", 0],
    "reverseState"     :[37,  243, 19,  0, {}, 1, "Reverse flow state", 0],
    "socStatus"        :[38,  243, 19,  0, {}, 1, "SOC calibration", 1],
    "hyperTmp"         :[39,   80, 50,  0, {}, 1, "Enclosure temperature", 1],
    "dcStatus"         :[40,  243, 19,  0, {}, 1, "DC state", 0],
    "pvStatus"         :[41,  243, 19,  0, {}, 1, "PV state", 0],
    "acStatus"         :[42,  243, 19,  0, {}, 1, "AC state", 0],
    "dataReady"        :[43,  243, 19,  0, {}, 1, "Data ready flag", 0],
    "gridState"        :[44,  243, 19,  0, {}, 1, "Grid connection state", 0],
    "BatVolt"          :[45,  243,  8,  0, {}, 0.01, "Battery voltage", 1],
    "FMVolt"           :[46,  243, 19,  0, {}, 1, "Voltage activation value", 1],
    "socLimit"         :[47,  243, 19,  0, {}, 1, "SOC limit state", 0],
    "rssi"             :[48,  243, 19,  0, {}, 1, "Signal strength", 0],
    "gridOffPower"     :[49,  248,  1,  0, {}, 1, "Off-grid power", 1],
    "lampSwitch"       :[50,  243, 19,  0, {}, 1, "Lamp state", 0],
    "IOTState"         :[51,  243, 19,  0, {}, 1, "IoT connection", 0],
    "fanSwitch"        :[52,  243, 19,  0, {}, 1, "Fan state", 0],
    "fanSpeed"         :[53,  243, 19,  0, {}, 1, "Fan level", 0],
    "faultLevel"       :[54,  243, 19,  0, {}, 1, "Fault severity", 0],
    "bindstate"        :[55,  243, 19,  0, {}, 1, "Bind state", 0],
    "VoltWakeup"       :[56,  243,  8,  0, {}, 1, "Voltage wake-up", 0],
    "OldMode"          :[57,  243, 19,  0, {}, 1, "Legacy mode", 0],
    "OTAState"         :[58,  243, 19,  0, {}, 1, "OTA state", 0],
    "LCNState"         :[59,  243, 19,  0, {}, 1, "LCN state", 0],
    "factoryModeState" :[60,  243, 19,  0, {}, 1, "Factory mode", 0],
#    "timestamp"        :[61,  243, 19,  0, {}, 1, "System timestamp", 0],
#    "ts"               :[62,  243, 19,  0, {}, 1, "Unix timestamp", 0],
    "timeZone"         :[63,  243, 19,  0, {}, 1, "Timezone", 0],
    "tsZone"           :[64,  243, 19,  0, {}, 1, "Timezone offset", 0],
    "chargeMaxLimit"   :[65,  248,  1,  0, {}, 1, "Max charge power", 0],
    "phaseSwitch"      :[66,  243, 19,  0, {}, 1, "Phase switch", 0],
    "is_error"         :[67,  243, 19,  0, {}, 1, "Error flag", 0],
#| Bit | Meaning |
#|-----|--------|
#| Bit0 | AC-coupled input present, auto-cleared by DSP |
#| Bit1 | AC input present flag |
#| Bit2 | AC-coupled overload |
#| Bit3 | Excess AC input power |
    "acCouplingState"  :[68, 243, 19,  0, {}, 1, "AC Coupling State", 0],
    "dryNodeState"     :[69, 243, 19,  0, {}, 1, "Dry contact status", 0],

# Device Data Properties — Read / Write
#    "writeRsp"         :[70,  243, 19,  0, {}, 1, "Write response", 0],
    "acMode"           :[71,  244, 62, 18, {"LevelActions":"|", "LevelNames":"input|output", "LevelOffHidden":"false", "SelectorStyle":"0"}, 1, "Charge or discharge mode", 1],
    "inputLimit"       :[72,  242,  1,  0, {'ValueStep':'1', 'ValueMin':'0',  'ValueMax':'2400', 'ValueUnit':'W'}, 1, "AC charge limit", 1],
    "outputLimit"      :[73,  242,  1,  0, {'ValueStep':'1', 'ValueMin':'0',  'ValueMax':'3200', 'ValueUnit':'W'}, 1, "Output limit", 1],
    "socSet"           :[74,  242,  1,  0, {'ValueStep':'1', 'ValueMin':'70', 'ValueMax':'100', 'ValueUnit':'%'}, 0.1, "Target SOC", 1],
    "minSoc"           :[75,  242,  1,  0, {'ValueStep':'1', 'ValueMin':'0',  'ValueMax':'50',   'ValueUnit':'%'}, 0.1, "Minimum SOC", 1],
    "gridReverse"      :[76,  244, 62, 18, {"LevelActions":"||", "LevelNames":"disabled|allow|forbidden", "LevelOffHidden":"false", "SelectorStyle":"0"}, 1, "Reverse flow control", 1],
    "inverseMaxPower"  :[77,  242,  1,  0, {'ValueStep':'1', 'ValueMin':'0',  'ValueMax':'2400', 'ValueUnit':'W'}, 1, "Max inverter output", 1],
    "gridStandard"     :[78,  244, 62, 18, {"LevelActions":"|||||||||", "LevelNames":"Germany|France|Austria|Switzerland|Netherlands|Spain|Belgium|Greece|Denmark|Italy", "LevelOffHidden":"false", "SelectorStyle":"1"}, 1, "Country", 1],
# 1: Parameters are not written to flash
# Device restores previous flash values after reboot
# Recommended for frequent configuration changes
    "smartMode"        :[79,  244, 73,  0, {}, 1, "Flash write behavior", 1],
    "batCalTime"       :[80,  243, 19,  0, {}, 1, "BatCalTime(minutes). Unauthorized modifications are not recommended", 0],
    "Fanmode"          :[81,  243, 19,  0, {}, 1, "Fanmode. Unauthorized modification is not recommended", 0],
    "Fanspeed"         :[82,  243, 19,  0, {}, 1, "Fanspeed. Unauthorized modification is not recommended", 0],
    "gridOffMode"      :[83,  244, 62, 18, {"LevelActions":"||", "LevelNames":"normal|eco|off", "LevelOffHidden":"false", "SelectorStyle":"0"}, 1, "Grid Off Mode", 1],
}

RESPONSE_SIZE = 20

RESPONSE_PACK_DATA={
# Battery Pack Data Properties
    "sn"               :[100, 243, 19,  0, {}, 1, "Serial Number", 1],
    "packType"         :[101, 243, 19,  0, {}, 1, "pack Type", 0],
    "socLevel"         :[102, 243,  6,  0, {}, 1, "State of charge", 1],
    "state"            :[103, 243, 19,  0, {}, 1, "State", 1],
    "power"            :[104, 248,  1,  0, {}, 1, "Battery pack power", 0],
# float maxTemp_C = (maxTemp - 2731) / 10.0;
    "maxTemp"          :[105,  80, 50,  0, {}, 1, "Stored temperature value", 1],
    "totalVol"         :[106, 243,  8,  0, {}, 0.01, "Total voltage", 1],
# Raw format: 16-bit two’s complement
# Source container: uint8_t[3, 1]
# Convert to signed int16
# current_A = value / 10.0;
    "batcur"           :[107, 243, 23,  0, {}, 1, "Battery current", 0],
    "maxVol"           :[108, 243,  8,  0, {}, 0.01, "Max cell voltage", 0],
    "minVol"           :[109, 243,  8,  0, {}, 0.01, "Min cell voltage ", 0],
    "softVersion"      :[110, 243, 19,  0, {}, 1, "Firmware version", 1],
}

class ZendurePlugin:
    enabled = False
    def __init__(self):
        return

    def onStart(self):
        # Domoticz.Log("onStart called")
        self.address = str(Parameters["Address"])
        self.pollingInterval = int(Parameters["Mode1"])
        self.heartbeatWaits = int(self.pollingInterval / 30)
        self.heartbeatCount = 0
        self.busy = False
        Domoticz.Heartbeat(self.pollingInterval if self.pollingInterval <= 30 else 30)
        self.prefix = str(Parameters["Mode2"])
        self.max_kwh = 0
        self.cur_kwh = 0
        self.in_kwh = 0
        self.out_kwh = 0
        self.soc = 0
        self.charge = 0
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

        # Skip values that are not present in response message.
        # This allows maybe other devices then solarFlow2400AC+ to work.
        result, response = self.zendure_get()
        if result:
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
                result = False
        if result == False:
            Domoticz.Log("Battery not found. No devices are created")
            return

        for own in OWN_DEVICES:
            dev = OWN_DEVICES[own]
            DeviceID = "{:04x}{:04x}".format(self.Hwid, dev[0])
            if DeviceID not in Devices:
                Domoticz.Unit(DeviceID=DeviceID, Unit=dev[0], Name=self.prefix + dev[6], Type=dev[1], Subtype=dev[2], Switchtype=dev[3], Options=dev[4], Used=dev[7]).Create()
        for header in RESPONSE_HEADER:
            dev = RESPONSE_HEADER[header]
            DeviceID = "{:04x}{:04x}".format(self.Hwid, dev[0])
            if DeviceID not in Devices and present[dev[0]] == 1:
                Domoticz.Unit(DeviceID=DeviceID, Unit=dev[0], Name=self.prefix + dev[6], Type=dev[1], Subtype=dev[2], Switchtype=dev[3], Options=dev[4], Used=dev[7]).Create()
        for properties in RESPONSE_PROPERTIES:
            dev = RESPONSE_PROPERTIES[properties]
            DeviceID = "{:04x}{:04x}".format(self.Hwid, dev[0])
            if DeviceID not in Devices and present[dev[0]] == 1:
                Domoticz.Unit(DeviceID=DeviceID, Unit=dev[0], Name=self.prefix + dev[6], Type=dev[1], Subtype=dev[2], Switchtype=dev[3], Options=dev[4], Used=dev[7]).Create()
        for pack in range(self.maxPack):
            for packData in RESPONSE_PACK_DATA:
                dev = RESPONSE_PACK_DATA[packData]
                unit = dev[0] + pack * RESPONSE_SIZE
                DeviceID = "{:04x}{:04x}".format(self.Hwid, unit)
                if DeviceID not in Devices and present[unit] == 1:
                    Domoticz.Unit(DeviceID=DeviceID, Unit=unit, Name=self.prefix + dev[6] + "[" + str(pack) + "]", Type=dev[1], Subtype=dev[2], Switchtype=dev[3], Options=dev[4], Used=dev[7]).Create()

        if result:
            self.zendure_update_all(response)

        Domoticz.Log("Product: " + self.product + ", Serial Number: " + self.sn + ", Version: " + self.version)
        for i in range(len(self.pack_sn)):
            Domoticz.Log("Package: " + self.pack_name[i] + " " + self.pack_model[i] + ", Kwh: " + str(self.pack_kwh[i]) + ", Serial Number: " + self.pack_sn[i] + ", firmware Version: " + self.pack_firmware[i])

    def onStop(self):
        Domoticz.Log("onStop called")

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
        self.heartbeatCount += 1
        if self.busy and self.heartbeatCount < 5: # Wait some more if busy. Max 5 times
            return
        else:
            if self.heartbeatCount >= self.heartbeatWaits:
                self.heartbeatCount = 0
                self.busy = True
                result, response = self.zendure_get()
                if result:
                    self.zendure_update_all(response)
                self.busy = False
            
    def zendure_update_all(self, response):
        self.sn = str(response.get("sn"))
        self.product = str(response.get("product"))
        self.version = str(response.get("version"))

        if response.get("properties") != None:
            self.in_kwh = 0
            self.out_kwh = 0
            self.charge = 0
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
            if response["properties"].get("outputPackPower") != None:
                self.in_kwh = float(response["properties"]["outputPackPower"]) / 1000
            if response["properties"].get("packInputPower") != None:
                self.out_kwh = float(response["properties"]["packInputPower"]) / 1000
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
            self.zendure_update(own, dev[0], dev[1], dev[2], dev[5], value)
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
            value = round(float(multiplier * value), 0 if multiplier == 1 else 2)
            nValue = int(value)
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

    def zendure_get(self):
        try:
            get_response = requests.get("http://" + self.address + "/properties/report")
            response = json.loads(get_response.text)
            return True, response
        except:
            Domoticz.Error("Errors in getting Zendure data. Check results.")
            return False, ""

    def zendure_post(self, item, value):
        try:
            value = round(value, 0)
            post_response = requests.post("http://" + self.address + "/properties/write", json={"sn": self.sn, "properties": {str(item): value}})
            response = json.loads(post_response.text)
            return response["success"]
        except:
            Domoticz.Error("Errors in setting Zendure data. Check results.")
            return False

    # imported from https://github.com/Zendure/Zendure-HA.git
    def get_battery_type(self, sn):
        model = "???"
        kWh = 0.0
        match sn[0]:
            case "A":
                if sn[3] == "3":
                    model = "AIO2400"
                    kWh = 2.4
                else:
                    model = "AB1000"
                    kWh = 0.96
            case "B":
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
