import sys
from time import sleep
from SX127x.LoRa import LoRa, MODE, CODING_RATE, BW
from SX127x.board_config import BOARD
import paho.mqtt.client as mqtt
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app import App

import mysql.connector
import logging


def get_last_action_fields_for_check():
    sql_client = mysql.connector.connect(host="localhost", user="root", password="raspberry", database="artificial_rain")
    cursor = sql_client.cursor()
    cursor.execute(f"SELECT ground_humidity_threshold, action, watering_mode FROM Action ORDER BY date_execute DESC LIMIT 1")
    sql_client.commit()
    results = cursor.fetchall()
    cursor.close()
    sql_client.close()
    return dict(
        ground_humidity_threshold = float(results[0]),
        action = results[1],
        watering_mode = results[2]
    )
    


class LoRaGateway(LoRa):
    def __init__(self, frequency=433, verbose=False):
        self.mqqt_client  = mqtt.Client("meteo")
        self.mqqt_client.connect("localhost")
        super(LoRaGateway, self).__init__(verbose)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0] * 6)
        self.set_mode(MODE.STDBY) # Initialisation de LoRa en mode standby (Attente)
        self.set_pa_config(pa_select=1)
        self.set_freq(frequency) # Fréquence d'émission 434 Mhz
        self.set_bw(BW.BW125) # Largeur de bande 125 Khz
        self.set_spreading_factor(7) # SF = 7
        self.set_coding_rate(CODING_RATE.CR4_5) # Codage pour la correction d'erreur
        self.set_sync_word(0xF1)
        
        self.data:"dict" = {}

    def start(self):
        self.reset_ptr_rx()
        self.set_mode(MODE.RXCONT)
        while True:
            sleep(.1)
            self.get_rssi_value()
            self.get_modem_status()
            sys.stdout.flush()
        
        
    def _parse_msg_and_update_data(self, msg:"str"):
        msg =  msg.split("|")[1:]
        self.data = dict(
            n = msg[0],
            p = msg[1],
            k = msg[2],
            ground_hum = msg[3],
            ground_temp = msg[4],
            air_hum = msg[5],
            air_temp = msg[6],
            rain_state = msg[7],
            conductivity = msg[8],
            ground_ph = msg[9],

        )
            
    
    def send_to_mqtt_broker(self, rssi:"float", snr:"float"):
        names = ",".join(self.data.keys()) + ",RSSI,SNR"
        values = ",".join([ "'" + str(i) + "'" for i in self.data.values()]) + f",'{rssi}','{snr}'"
        msg = names + "|" + values
        #print("msg " ,msg)
        
        self.mqqt_client.publish("app",msg)
        print("msg a publier ")
        
    def on_rx_done(self):
        logging.info("Message reçu: ")
        self.clear_irq_flags(RxDone=1)
        payloadReceived = self.read_payload(nocheck=True)
        payload = bytes(payloadReceived).decode("utf-8",'ignore')
        if payload.startswith("A7"):
            self._parse_msg_and_update_data(payload)
            self.send_to_mqtt_broker(self.get_rssi_value(), self.get_pkt_snr_value())
            print(payload)
            self.set_mode(MODE.SLEEP)
            self.reset_ptr_rx()
            self.set_mode(MODE.RXCONT) 
            
            

if __name__ == "__main__":

    try:
        import RPi.GPIO as GPIO

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        
        print("Starting LoRa")
        BOARD.setup()
        lora = LoRaGateway(verbose=False)
        print("Before lora started")
        lora.start()
        print("Successfully started LoRa")
    except KeyboardInterrupt:
        sys.stdout.flush()
        logging.info("Interruption du clavier")
        
    except Exception as ex:
        logging.error(f"Exception occured while running LoRa ==> {ex}")

    finally:
        sys.stdout.flush()
        lora.set_mode(MODE.SLEEP)
        BOARD.teardown()
    
