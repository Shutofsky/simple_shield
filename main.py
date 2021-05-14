import machine
import time
import utime
import ujson
import network
import urandom
import umqttsimple
import config
import webrepl

station = network.WLAN(network.STA_IF)

manage_data = dict()
manage_data['mqtt_connect'] = False
manage_data['powerstate'] =  'OFF'
manage_data['ping_msg'] = b''
manage_data['ping_timestamp'] = 0 
manage_data['ping_millis'] = 0

def wifi_init():
    station.active(True)
    station.connect(config.cfg['wlan_ssid'], config.cfg['wlan_password'])
    while station.isconnected() == False:
        for x in range (6):
            config.pins['FAN_POWER'].value(1)
            time.sleep(.25)
            config.pins['FAN_POWER'].value(0)
            time.sleep(.25)
    print('Connection successful')
    print(station.ifconfig())
    webrepl.start()
    
def reset_out():
    for pin_ctrl in config.pins:
        config.pins[pin_ctrl].value(0)

def parse_command(new_command):
    print(new_command)
    data = new_command.get('powerstate') 
    print(data)
    if not data:
        return
    if data == 'RESET':
        machine.reset()
    else:
        change_state(data, 0)

def change_state(power_state, inner_flag):
    global client
    print(power_state, manage_data['powerstate'])
    if power_state == 'AUX' and manage_data['powerstate'] !='AUX': 
        manage_data['powerstate'] ='AUX'
        config.pins['FAN_POWER'].value(1)
        config.pins['RELAY_POWER'].value(1)
        time.sleep(2)
        config.pins['RELAY_POWER'].value(0)
        if inner_flag:
            ts_tmp = manage_data['ping_timestamp'] + int((utime.ticks_ms() - manage_data['ping_millis'])/1000)
            t_com = '{"timestamp":' + str(ts_tmp) + ', "datahold":{"powerstate":"AUX"}}'
            client.publish(config.topics['pub_state'], t_com)
        time.sleep(1)
        config.pins['RELAY_POWER'].value(1)
        time.sleep(2)
        config.pins['FAN_POWER'].value(0)
        config.pins['RELAY_POWER'].value(0)
        time.sleep(2)
        config.pins['FAN_POWER'].value(1)
        config.pins['RELAY_POWER'].value(1)
        time.sleep(2)
        config.pins['RELAY_POWER'].value(0)
        time.sleep(2)
        config.pins['KBD_POWER'].value(1)
        time.sleep(5)
        config.pins['FAN_POWER'].value(0)
    elif power_state == 'PWR' and manage_data['powerstate'] !='PWR':
        manage_data['powerstate'] ='PWR'
        config.pins['FAN_POWER'].value(1)
        config.pins['RELAY_POWER'].value(0)
        config.pins['KBD_POWER'].value(1)
        if inner_flag:
            ts_tmp = manage_data['ping_timestamp'] + int((utime.ticks_ms() - manage_data['ping_millis'])/1000)
            t_com = '{"timestamp":' + str(ts_tmp) + ', "datahold":{"powerstate":"PWR"}}'
            client.publish(config.topics['pub_state'], t_com)
    elif power_state == 'OFF' and manage_data['powerstate'] !='OFF':
        manage_data['powerstate'] ='OFF'
        config.pins['FAN_POWER'].value(0)
        config.pins['RELAY_POWER'].value(0)
        config.pins['KBD_POWER'].value(0)
        if inner_flag:
            ts_tmp = manage_data['ping_timestamp'] + int((utime.ticks_ms() - manage_data['ping_millis'])/1000)
            t_com = '{"timestamp":' + str(ts_tmp) + ', "datahold":{"powerstate":"OFF"}}'     
            client.publish(config.topics['pub_state'], t_com)

def mqtt_callback(topic, msg):
    global ping_msg
    if (topic == config.topics['sub']):
        try:
            cmd = ujson.loads(msg)
            datahold = cmd.get('datahold')
            print(datahold)
            parse_command(datahold)
            return 
        except:
            time.sleep(.2)
            return
    elif (topic == config.topics['sub_ping']):
        manage_data['ping_msg'] = msg


def connect_and_subscribe():
    bList = str(station.ifconfig()[0]).split('.')
    bList[-1] = '254'
    brokerIP = '.'.join(bList)
    server = brokerIP
    port = config.cfg.get('port')
    user = config.cfg.get('user')
    password = config.cfg.get('password')
    client = umqttsimple.MQTTClient(config.cfg.get('client_id'), server, port, user, password)
    client.set_callback(mqtt_callback)
    try:
        client.connect()
    except:
        manage_data['mqtt_connect'] = False
        return client
    sub_topics = [config.topics[t] for t in config.topics if 'sub' in t]
    for t in sub_topics:
        client.subscribe(t)
    print('connected to {}, subscribed to {}'.format(server, sub_topics))
    try:
        cmd_out = '{"timestamp":1}'
        client.publish(config.topics['pub'], cmd_out)
        manage_data['mqtt_connect'] = True
    except:
        manage_data['mqtt_connect'] = False
        restart_and_reconnect()
    reset_out()
    return client

def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    if station.isconnected() == False:
        print('WiFi connection lost!')
        wifi_init()
    for x in range(4):
        config.pins['FAN_POWER'].value(1)
        time.sleep(.5)
        config.pins['FAN_POWER'].value(0)
        time.sleep(.5)

def mqtt_init():
    manage_data['mqtt_connect'] = False
    while manage_data['mqtt_connect'] == False:
        restart_and_reconnect()
        client = connect_and_subscribe()
    return client

def send_pong(msg, client):
    client.publish(config.topics['pub_id_pong'], msg)
    return
    
def main():
    global client
    reset_out()
    wifi_init()
    client = mqtt_init()    
    while True:
        try:
            client.check_msg()
        except OSError as e:
            client = mqtt_init()    
        if manage_data['ping_msg'] != b'':
            send_pong(manage_data['ping_msg'], client)
            manage_data['ping_timestamp'] = (ujson.loads(manage_data['ping_msg'])).get('timestamp')
            print(manage_data['ping_timestamp'])
            manage_data['ping_millis'] = utime.ticks_ms()
            print(manage_data['ping_millis'])
            manage_data['ping_msg'] = b''
            continue
        if config.pins['RELAY_IN'].value() == 0 and manage_data['powerstate'] == 'OFF' :
            change_state('AUX', 1)
            continue
        if config.pins['KBD_IN'].value() == 0 and manage_data['powerstate'] == 'AUX' :
            change_state('PWR', 1)

main()


