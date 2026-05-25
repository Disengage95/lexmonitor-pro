import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN Y BASE DE DATOS IGUAL QUE ANTES ---
# (Usa el mismo código de conexión de base de datos que ya tenías)

def consultar_proceso_playwright(radicado):
    try:
        with sync_playwright() as p:
            # Lanzamos navegador invisible (headless=True)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navegamos a la web oficial
            url = f"https://consultaprocesos.ramajudicial.gov.co/Procesos/NombreParte/1"
            # NOTA: En la web, primero se debe buscar el radicado en la caja de búsqueda
            page.goto("https://consultaprocesos.ramajudicial.gov.co/")
            
            # Esperamos a que la caja de texto cargue
            page.wait_for_selector("input[type='text']")
            page.fill("input[type='text']", radicado)
            page.press("input[type='text']", "Enter")
            
            # Esperamos a que aparezca el resultado (ajusta el selector según la web)
            page.wait_for_timeout(5000) # Espera 5 segundos a que cargue
            
            # Obtenemos el texto de la última actuación
            actuacion = page.inner_text(".clase-de-la-actuacion") # Necesitas inspeccionar la web para el selector real
            browser.close()
            return actuacion
    except Exception as e:
        return f"Error de automatización: {str(e)}"

# --- LÓGICA DE STREAMLIT ---
st.title("LexMonitor Pro - Navegación Real")
rad = st.text_input("Radicado")
if st.button("Consultar"):
    with st.spinner("Navegando..."):
        res = consultar_proceso_playwright(rad)
        st.write(res)