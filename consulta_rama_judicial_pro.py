import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="LexMonitor Pro", layout="wide")

# CONEXIÓN DB (Igual que antes)
def conectar_db():
    conn = sqlite3.connect("procesos.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, correo TEXT UNIQUE, password_hash TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS radicados (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, numero_radicado TEXT, nombre_caso TEXT, ultima_actuacion TEXT, fecha_ultima_revision TEXT, UNIQUE(usuario_id, numero_radicado))')
    conn.commit()
    return conn

# FUNCIÓN DE CONSULTA CON PLAYWRIGHT (Navegación Real)
def consultar_proceso_playwright(radicado):
    try:
        with sync_playwright() as p:
            # Lanzamos navegador real
            browser = p.chromium.launch(headless=True) # Cambia a False si quieres ver el navegador abriéndose
            page = browser.new_page()
            
            # Entramos al portal
            page.goto("https://consultaprocesos.ramajudicial.gov.co/", wait_until="networkidle")
            
            # Llenamos la búsqueda
            page.fill("input[type='text']", radicado)
            page.press("input[type='text']", "Enter")
            
            # Esperamos a que la tabla cargue (Vuetify usa v-data-table)
            page.wait_for_selector("table", timeout=15000)
            
            # Extraemos el texto de la última actuación (celda específica de la tabla)
            # En base a tu inspección, el texto suele estar en la última celda <td> de la fila
            resultado = page.inner_text("tbody tr:first-child td:nth-child(5)")
            
            browser.close()
            return str(resultado)
    except Exception as e:
        return f"Error de navegación: {str(e)[:30]}"

# --- INTERFAZ STREAMLIT ---
st.title("⚖️ LexMonitor Pro - Motor de Navegación Real")

if "logeado" not in st.session_state: st.session_state.update({"logeado": False, "usuario_id": 1})

# (Aquí mantienes tu lógica de login y base de datos)

st.header("📋 Mis Procesos")
# ... (Tu código para mostrar la lista de procesos)

if st.button("🔄 Ejecutar Actualización Real"):
    with st.spinner("Simulando navegación humana en el portal..."):
        # Ejemplo con el radicado que probamos
        resultado = consultar_proceso_playwright("11001310300120140019200")
        st.success(f"Resultado obtenido: {resultado}")