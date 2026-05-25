import streamlit as st
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import requests
import time

# CONFIGURACIÓN DE LA PÁGINA WEB
st.set_page_config(page_title="LexMonitor - Control de Radicados", page_icon="⚖️", layout="wide")

# (Tu código de configuración de secretos sigue igual)
# Asegúrate de tener el archivo .streamlit/secrets.toml creado para evitar el error de la imagen 9e5224.png

def consultar_rama_judicial_individual(radicado):
    # Usamos una URL que emula una consulta de navegador
    url_objetivo = f"https://consultaprocesos.ramajudicial.gov.co/api/v1/Procesos/NumeroRadicacion/{radicado}"
    
    # Encabezados críticos para pasar por un usuario real y evitar bloqueos automáticos
    cabeceras = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://consultaprocesos.ramajudicial.gov.co/",
        "Connection": "keep-alive"
    }
    
    try:
        # Usamos Session para mantener las cookies que a veces requiere el firewall
        session = requests.Session()
        respuesta = session.get(url_objetivo, headers=cabeceras, timeout=10)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            if datos.get("procesos") and len(datos["procesos"]) > 0:
                return datos["procesos"][0].get("ultimaActuacion", "Sin actuaciones recientes")
            return "No se encontraron registros"
        elif respuesta.status_code == 403:
            return "Acceso restringido por el portal judicial (Intente en unos minutos)"
        else:
            return f"Error en la conexión (Código {respuesta.status_code})"
    except Exception:
        return "El servidor judicial no responde, intente manualmente en el portal"

# ... (El resto de tu lógica de la base de datos y botones permanece igual)