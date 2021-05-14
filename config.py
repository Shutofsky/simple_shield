import machine
from network import WLAN
from ubinascii import hexlify

ENV = 'dev'  

cfg = {
    'client_id': hexlify(machine.unique_id()),
    'mac': hexlify(WLAN().config('mac')),
    'wlan_ssid': 'ArmyDep',  
    'wlan_password': 'z0BcfpHu',
    'port': 1883,
    'user': b'mqtt',
    'password': b'skabent0mqtt',
}

pins = {
    'RELAY_IN': machine.Pin(16, machine.Pin.IN),
    'RELAY_POWER': machine.Pin(14, machine.Pin.OUT),
    'KBD_IN': machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP),
    'KBD_POWER': machine.Pin(12, machine.Pin.OUT),  
    'FAN_POWER': machine.Pin(13, machine.Pin.OUT)  
}

topics = {
    'sub': b'pwr/all/cup',          # Here commands fo shield
    'sub_id': b'pwr/' + cfg['mac'] + '/cup',          # Here commands fo shield
    'sub_ping': b'pwr/all/ping',    # Here pings for shield
    'pub': b'ask/pwr/all/cup',      # Here start config request 
    'pub_state': b'ask/pwr/all/sup', # Here changes of state
    'pub_id_pong': b'ask/pwr/' + cfg['mac'] + '/pong'     # Here answers for ping
}



