# solarFlow2400AC
Zendure solarFlow2400AC+ domoticz plugin

An implentation of zendure solarFlow2400AC+ plugin for domoticz.
The plugin might also work for other zendure devices.

## Overview

The plugin is developed using the BaseTemplate.txt as example.

The plugin uses the information from https://github.com/Zendure/zenSDK.git
I found some problems in the zenSDK documentation so I also looked at
https://github.com/Zendure/Zendure-HA.git

The plugin uses the local http interface and not the MQTT interface.

On linux you can use 'avahi-browse --all -r' to get ip address/hostname.
Use Zendure-<Model>-<ID>.local as hostname or use the ip address.
For solarFlow2400AC+ you have to change the hostname '\043' into a '+'.
Do not use Zendure-MeterReader-<ID>.local
Use search engine to find how this is done on Windows.

## Warning

When changing zendure parameters make sure you do not exceed max allowed values.
The parameters are not checked so you can set for example  the output power to 2400W
when only 800W is allowed.

## Installation

Instalation instructions:
- Login to the Domoticz server.
- Change to the plugin directory with "cd domoticz/plugins".
- Install this plugin with 'git clone https://github.com/hermantb/solarFlow2400AC'
- Restart Domoticz with "sudo service domoticz restart".
- Add the plugin in the Setup/Hardware of domoticz.

## Energie Dashboard

For the Energie Dashboard Setup you can use:
Battery:                "charge / discharge"
Battery SOC:            "soc"
Battery Voltage:        "Battery voltage"
Battery Energie In:     "Input Kwh"
Battery Energie Out::   "Output Kwh"
