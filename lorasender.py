import sys
import time
from SX127x.LoRa import LoRa, MODE, CODING_RATE, BW
from SX127x.board_config import BOARD


import traceback
from typing import Dict, Any
import mysql.connector
import RPi.GPIO as GPIO
'''
class BOARD:
    DIO0 = 4   # RaspPi GPIO 4
    DIO1 = 17   # RaspPi GPIO 17
    DIO2 = 18   # RaspPi GPIO 18
    DIO3 = 27   # RaspPi GPIO 27
    RST  = 22   # RaspPi GPIO 22
'''
class LoRaSender:
    def __init__(self, frequency=433, verbose=False):
        #try:
         #   GPIO.cleanup()
        #except:
         #   pass
        GPIO.setmode(GPIO.BCM)
         
        GPIO.setup(BOARD.DIO0, GPIO.IN)
        GPIO.setup(BOARD.DIO1, GPIO.IN)
        GPIO.setup(BOARD.DIO2, GPIO.IN)
        GPIO.setup(BOARD.DIO3, GPIO.IN)
        
        self._sql_client = None
        self.lora = LoRa(verbose=verbose)
        if self.lora.get_mode() != MODE.SLEEP:
            self.lora.set_mode(MODE.SLEEP)
        
        self.lora.set_mode(MODE.SLEEP)
        self.lora.set_pa_config(pa_select=1)
        self.lora.set_freq(frequency)
        self.lora.set_bw(BW.BW125)
        self.lora.set_spreading_factor(7)
        self.lora.set_coding_rate(CODING_RATE.CR4_5)
        self.lora.set_sync_word(0xF3)
        
        
    def send_msg(self, msg: Dict[str, str]):
        try:
            msg_str = msg# "|".join(msg.values())
            print('before sending message ',msg_str)
            msg_str = "B6" + "|" + msg_str
            self.lora.set_mode(MODE.STDBY)
            self.lora.write_payload([ord(char) for char in msg_str])
            self.lora.set_mode(MODE.TX)
            time.sleep(0.1)
            self.lora.set_mode(MODE.SLEEP)
            print('message sent from lorasender ',msg_str)
        except Exception as ex:
            traceback.print_exc()
            raise Exception(f"Exception occurred while sending msg  ==> {ex}")
    
if __name__ == "__main__":
    x = LoRaSender()
    
    s = 0
