import os
import streamlit as st
from streamlit.components.v1 import html
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import datetime as dt
from streamlit_option_menu import option_menu
from  PIL import Image
import base64
import mysql.connector
import time
from lorasender import LoRaSender
import RPi.GPIO as GPIO

import pandas as pd
import random
import paho.mqtt.client as mqtt



def store_action_in_server(data:dict):

    sql_client = mysql.connector.connect(host="localhost", user="root", password="raspberry", database="artificial_rain")
    cursor = sql_client.cursor()
    cursor.execute("DELETE FROM TmpAction")
    sql_client.commit()

    names = ",".join(data.keys())
    values = ",".join( ["'"+str(i)+"'" for i in data.values()])
    print(f"INSERT INTO TmpAction ({names}) VALUES ({values})")
    cursor.execute(f"INSERT INTO TmpAction ({names}) VALUES ({values})")
    sql_client.commit()
    cursor.close()
    sql_client.close()
    
  



def submit_action(action:str):
    sql_client = mysql.connector.connect(host="localhost", user="root", password="raspberry", database="artificial_rain")
    cursor = sql_client.cursor()
    cursor.execute("SELECT * FROM TmpAction ORDER BY n DESC LIMIT 1")
    results = cursor.fetchall()[0]
    print("results ",results)
    print(cursor.description)
    columns = [desc[0] for desc in cursor.description]
    names = "action,"
    values = f"'{action}',"
    for c, v in zip(columns, results):
        names += c + ","
        values += f"'{v}',"
    
    names = names[:-1]
    values = values[:-1]
    print(f"INSERT INTO Action ({names}) VALUES ({values})")
    cursor.execute(f"INSERT INTO Action ({names}) VALUES ({values})")
    sql_client.commit()
    cursor.close()
    sql_client.close()
    
    lora_sender = LoRaSender()    
    lora_sender.send_msg(f"{names}|{values}")
    GPIO.cleanup()
    

def get_latest():
    sql_client = mysql.connector.connect(host="localhost", user="root", password="raspberry", database="artificial_rain")
    cursor = sql_client.cursor()
    # Retrieve the latest values from the database
    cursor.execute("SELECT * FROM Sensors ORDER BY date_creationClients DESC LIMIT 1")

    result = cursor.fetchone()
    
    data =  {
        "n": result[0],
        "p": result[1],
        "k": result[2],
        "ground_hum": result[3],
        "ground_temp": result[4],
        "air_hum": result[5],
        "air_temp": result[6],
        "rain_state": result[7],
        "conductivity": result[8],
        "ground_ph": result[9],
        "SNR": result[10],
        "RSSI": result[11]
        }
    cursor.close()
    sql_client.close()
    return data

def build_about_us():


    def get_img_as_base64(file):
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()

    img = get_img_as_base64("/home/pi/Desktop/streamlitv6/watering6.jpg")

    html_template = """
    <div style="font-family: Arial; font-size: 18px; line-height: 1.6; color: #EEE; display: flex; flex-direction: column; align-items: center;">
        <h1 style="color: #FFF; text-align: center; font-weight: bold;">AgriFlow</h1>
        <p style="text-align: center; font-weight: bold;">Le projet AgriFlow a été créé dans le cadre d'un projet de fin d'études par Adel Ouali et Fouzi Kara, encadré par le professeur CHIBANI Youcef, avec pour objectif d'optimiser l'arrosage de l'eau et l'apport d'engrais NPK.</p>
        <img src="data:image/png;base64,{img}" alt="Watering Image" style="width: 90%; max-width: 1200px; height: auto;">
        <hr>
        <h2 style="color: #FFF; font-weight: bold;">Ce que cette plateforme propose :</h2>
        <ul>
            <li><b>L'affichage en temps réel des dernières mesures obtenues après une collecte de données faites par nos capteurs.</b></li>
            <li><b>Un historique contenant toutes les anciennes mesures.</b></li>
            <li><b>La possibilité de contrôler les actions de l'arrosage de l'eau manuellement ou automatiquement.</b></li>
            <li><b>La possibilité de contrôler les actions de l'arrosage de l'engrais.</b></li>
        </ul>
        <hr>
        <h2 style="color: #FFF; font-weight: bold;">Les différentes sections disponibles :</h2>
        <ul>
            <li><b>A propos:</b> Quelques informations utiles sur SmartAgri.</li>
            <li><b>Dashboard:</b> Aperçu global des dernières données mesurées.</li>
            <li><b>Histogramme:</b> Récapitulatif de toutes les statistiques disponibles.</li>
            <li><b>Arrosage:</b> Contrôle des différents actions de l'eau selon les paramètres .</li>
            <li><b>Fertilisation:</b> Contrôle des différents actions de l'engrais selon les paramètres seuils.</li>
        </ul>
        <hr>
    </div>
    """.format(img=img)

    st.markdown(html_template, unsafe_allow_html=True)


def build_figure_view():
    
    ind_map = {
        "RSSI": {
            "range": [0, -140],
            "green": [0, -115],
            "orange": [-115, -120],
            "red": [-120, -140]
        },
        "SNR": {
            "range": [0, -14],
            "green": [0, -7],
            "orange": [-7, -13],
            "red": [-13, -14]
        },
        "air_temp": {
            "range": [0, 45],
            "green": [0, 35],
            "orange": [35, 45],
            "red": [35, 45]
        },
        "air_hum": {
            "range": [0, 100],
            "green": [0, 50],
            "orange": [50, 80],
            "red": [80, 100]
        },
        "ground_temp": {
            "range": [0, 120],
            "green": [0, 35],
            "orange": [35, 75],
            "red": [75, 120]
        },
        "ground_hum": {
            "range": [0, 100],
            "green": [0, 60],
            "orange": [60, 80],
            "red": [75, 100]
        },
        "n": {
            "range": [0, 3000],
            "green": [0, 1500],
            "orange": [1500, 2000],
            "red": [2000, 3000]
        },
        "p": {
            "range": [0, 3000],
            "green": [0, 1500],
            "orange": [1500, 2000],
            "red": [2000, 3000]
        },
        "k": {
            "range": [0, 3000],
            "green": [0, 1500],
            "orange": [1500, 2000],
            "red": [2000, 3000]
        },
        "rain_state": {
            "range": [0, 1030],
            "green": [500, 1030],
            "orange": [330, 500],
            "red": [0, 330]
        },
        "conductivity": {
            "range": [0, 200000],
            "green": [0, 10000],
            "orange": [10000, 100000],
            "red": [100000, 200000]
        },
        "ground_ph": {
            "range": [0, 14],
            "green": [6.5, 7.4],
            "orange": [7.4, 14],
            "red": [0, 6.5]
        }
    }
    def _build_indicator(value, old, name, min_v, max_v, col, row):
        fig = go.Indicator(
            mode="gauge+number+delta",
            value=value,
            delta={'reference': old},
            title=name,
            gauge={
                'bar': {'color': 'lightblue'},
                'axis': {'range': ind_map[name]["range"], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': 'lightblue'},
                'bgcolor': 'white',
                'borderwidth': 1,
                'bordercolor': "#189E18",
                'steps': [
                    {'range': ind_map[name]["green"], 'color': "green"},
                    {'range': ind_map[name]["orange"], 'color': "orange"},
                    {'range': ind_map[name]["red"], 'color': 'red'}
                ],
            },
            domain={"row": row, "column": col}
        )

        return fig
    def _generate_rain_state_icon(rs:"str", plc_hol):
        if rs == "rainy":
            icon = "☀️"  # Streamlit-Icons syntax for rainy icon
        elif rs == "sunny":
            icon = "☔"  # Streamlit-Icons syntax for sunny icon
        
        icon = f'''
            <div style="position: fixed; top: 75px; right: 80px;">
                <span style="font-size: 75px;">{icon}</span>
            </div>
        '''
        plc_hol.markdown(icon, unsafe_allow_html=True)

    # Retrieve the latest values from the database
    data: dict = get_latest()
    n_fig = len(data)
    n_rows = 3
    n_cols = int(n_fig / n_rows) + min(n_fig % n_rows, 1)

    fig = make_subplots(
        rows=n_rows,
        cols=n_cols,
        specs=[[{"type": "indicator"} for _ in range(0, n_cols)] for _ in range(0, n_rows)],
        vertical_spacing=0.2,
        horizontal_spacing=0.1
    )

    for i, (k, v) in enumerate(data.items(), start=1):
        row = (i - 1) // n_cols + 1
        col = (i - 1) % n_cols + 1
        indicator = _build_indicator(v, v, k, 0, 100, col, row)
        fig.add_trace(indicator, row=row, col=col)

    st.markdown("<h1 style='text-align: center;'>Dashboard</h1>", unsafe_allow_html=True)
    
    def _choose_rain_state():
        return random.choice(["rainy", "sunny"])
    fig.update_layout(height=600, width=800)
    rain_state = 'sunny' if data['rain_state'] < 500 else 'rainy' #_choose_rain_state()
    
    rain_state_place_holder = st.empty()
    chart_placeholder = st.empty()
    
    _generate_rain_state_icon(rain_state, rain_state_place_holder)
    chart_placeholder.plotly_chart(fig)
    
    
    st.write("")
    st.write("")
    st.write("")
    st.write("")
    st.write("")
    


    while True:
        time.sleep(5)
        data: dict = get_latest()
        i = 0
        for k, v in data.items():
            fig.data[i].value = v
            i += 1
        
        rain_state_place_holder.empty()
        chart_placeholder.empty()
        
        rain_state = 'sunny' if data['rain_state'] < 500 else 'rainy' #_choose_rain_state()
        _generate_rain_state_icon(rain_state, rain_state_place_holder)
        chart_placeholder.plotly_chart(fig)
        
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        st.write("")
    
#-------------------------------



def build_histogramme_view():
    # Se connecter à la base de données


    # Fonction pour récupérer les 20 derniers enregistrements de la base de données
    def get_latest_values():
        sql_client = mysql.connector.connect(host="localhost", user="root", password="raspberry", database="artificial_rain")
        cursor = sql_client.cursor()
        cursor.execute("SELECT * FROM Sensors ORDER BY date_creationClients DESC LIMIT 20")
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(results, columns=columns)

        cursor.close()
        sql_client.close()
        return df

    # Fonction pour construire la vue des histogrammes
    def build_histogram_view():
        # Récupérer les 20 derniers enregistrements de la base de données
        data = get_latest_values()

        # Sélectionner la colonne à afficher dans l'histogramme
        selected_column = st.selectbox("Sélectionnez la colonne à afficher", data.columns)

        # Créer l'histogramme en fonction de la colonne sélectionnée
        fig = px.histogram(data, x='date_creationClients', y=selected_column, title=selected_column)
        st.plotly_chart(fig)

    # Appel de la fonction pour construire la vue des histogrammes
    build_histogram_view()
    
    
    
    
    
    
def build_ferilization_view():
    st.markdown("<h1 style='text-align: center;'>Quantités de fertilisation</h1>", unsafe_allow_html=True)
    st.session_state.n = st.number_input(label="N", value=0)
    st.session_state.p = st.number_input(label="P", value=0)
    st.session_state.k = st.number_input(label="K", value=0)
    st.session_state.water = st.number_input(label="Eau", value=0)
        
    STATE = {

        "watering_mode":None,
        "watering_duration":None,
        "watering_option":"Fertilization",
        "n":st.session_state.n ,
        "p":st.session_state.p ,
        "k":st.session_state.k ,
        "water":st.session_state.water ,
        "ground_humidity_threshold":None


    }
    store_action_in_server(STATE)
        
        
def build_watering_view():
    st.markdown("<h1 style='text-align: center;'>Mode Arrosage</h1>", unsafe_allow_html=True)
    st.session_state.watering_mode = st.radio("CHOIX DU MODE", ("Auto", "Manual"))
    if st.session_state.watering_mode == "Auto":
        st.session_state.ground_humidity_threshold = st.slider("RÉGLAGE HUMIDTÉ DE LA TERRE", 0, 100, 0)
    
    if st.session_state.watering_mode == "Manual":
        st.session_state.watering_duration = st.time_input("DURÉE D'ARROSAGE", dt.time(0, 0, 0))
        
    st.write(" ")
    st.write(" ")
    st.write(" ")

    
    STATE = {
            "watering_mode":st.session_state.watering_mode,
            "watering_duration":st.session_state.watering_duration if st.session_state.watering_mode == "Manual" else None,
            "watering_option":"Watering",
            "n":None,
            "p":None,
            "k":None,
            "water":None,
            "ground_humidity_threshold":st.session_state.ground_humidity_threshold if st.session_state.watering_mode == "Auto" else None 
        }
    





    
    
    
    
    
    store_action_in_server(STATE)
    


def main():


    # Define custom CSS
    with st.sidebar:
        #st.markdown("<h1 style='text-align: left; font-size: 50px;'>Navigation</h1>", unsafe_allow_html=True)
        page = option_menu(
            None, ["A propos","Dashboard","Histogramme", "Arrosage", "Fertilisation"],
            icons=['house','book', 'clipboard-data', 'cloud-sun', 'book'],
            menu_icon="app-indicator", default_index=0,
            styles={ 
                "container": {"padding": "5!important", "background-color": "#34A56F"},
                "icon": {"color": "#ccd5ae", "font-size": "25px"}, 
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#ffffff"},
                "nav-link-selected": {"background-color": "#617C58"},
            }
        )
    
    
    start_watering_plc_hold = st.sidebar.empty()
    stop_watering_plc_hold = st.sidebar.empty()
    
    st.start_watering = start_watering_plc_hold.button("Arrosage ON")
    st.stop_watering = stop_watering_plc_hold.button("Arrosage OFF")
        
    #page = st.sidebar.radio("", ())#"Page 2", "Page 3"
    
    if page == "A propos":
        build_about_us()
    if page == "Dashboard":
        build_figure_view()
    elif page == "Histogramme":
        build_histogramme_view()
    elif page == "Arrosage":
        build_watering_view()
    elif page == "Fertilisation":
        build_ferilization_view()
    print("submit start_watering ",st.start_watering," stop_watering ",st.stop_watering)

    if st.start_watering is True:
        submit_action("Start")
        st.start_watering = False
  
    if st.stop_watering is True:
        submit_action("Stop")
        st.stop_watering = False


if __name__ == "__main__":
    main()

