#import mariadb
import mysql.connector
import paho.mqtt.client as mqtt
import datetime
import time

class LoRaSender:
    def __init__(self):
        pass
    
    def send_msg(self, msg):
        print("sending action msg", msg)

LORA_SENDER = LoRaSender()

def format_query(names:str, values:str) ->"str":
    print("format query")
    return f"INSERT INTO Sensors ({names}) VALUES ({values})"

def commit_to_db(query:"str"):
    sql_client = mysql.connector.connect(host="localhost",  user="root", password="raspberry",  database="artificial_rain")
    cursor = sql_client.cursor(buffered=True)
    cursor.execute(query)
    #cursor.close()
    sql_client.commit()
    
    sql_client.close()


def get_last_action_fields_for_check():
    sql_client = mysql.connector.connect(host="localhost", user="root", password="raspberry", database="artificial_rain")
    cursor = sql_client.cursor(buffered=True)
    cursor.execute(f"SELECT ground_humidity_threshold, action, watering_mode FROM Action ORDER BY date_execute DESC LIMIT 1")
    sql_client.commit()
    results = cursor.fetchall()[0]
    cursor.close()
    sql_client.close()
    try:
        ground_humidity_threshold = float(results[0])
    except:
        ground_humidity_threshold = 0
    
    return dict(
        ground_humidity_threshold = ground_humidity_threshold,
        action = results[1],
        watering_mode = results[2]
    )
    

def check_action_for_stopping(names:"str", values:"str"):
    names = names.split(",")
    values = values.split(",")
    data = {}
    for k, v in zip(names, values):
        data.update({k : v})
        
    actions = get_last_action_fields_for_check()
    ground_hum = data["ground_hum"]
    ground_hum = float(ground_hum.replace("'",""))

    if (ground_hum >= actions["ground_humidity_threshold"] 
        and actions["watering_mode"] == "Auto"
        and actions["action"] == "Start"):
        LORA_SENDER.send_msg("B6|action|Stop") 
    
'''
def on_message(client, userdata, message):
    print("on_message")
    msg = str(message.payload.decode("utf-8"))
    print("Received message:", msg)
    data=msg.split("|")
    print("Data:", data)
    query_str = format_query(data[0], data[1])
    print("Query:", query_str)
    commit_to_db(query_str)
    time.sleep(0.1)
    check_action_for_stopping(data[0], data[1])
'''    
def on_message(client, userdata, message):
    topic = message.topic
    message = str(message.payload.decode("utf-8"))
    print("Received message: Topic={}, Message={}".format(topic, message))
    data=message.split("|")
    #print("Data:", data)
    query_str = format_query(data[0], data[1])
    #print("Query:", query_str)
    commit_to_db(query_str)
    check_action_for_stopping(data[0], data[1])
    
if __name__ == "__main__":
    
    client = mqtt.Client("website")
    client.connect("localhost")
    #print ("avant subscribe")
    client.subscribe("app")
    #print ("apres subscribe")
    client.on_message = on_message
    #print("apres on message ")
    client.loop_forever()
    #print("quiet")
