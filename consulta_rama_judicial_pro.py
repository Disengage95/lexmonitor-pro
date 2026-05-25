import streamlit as st
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import cloudscraper
import time

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="LexMonitor Pro", page_icon="⚖️", layout="wide")

# CONEXIÓN A BASE DE DATOS
def conectar_db():
    conn = sqlite3.connect("procesos.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, correo TEXT UNIQUE, password_hash TEXT, nombre_bufete TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS radicados (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, numero_radicado TEXT, nombre_caso TEXT, ultima_actuacion TEXT, fecha_ultima_revision TEXT, UNIQUE(usuario_id, numero_radicado))')
    conn.commit()
    return conn

def encriptar_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# CONSULTA JUDICIAL BLINDADA
def consultar_rama_judicial_individual(radicado):
    url = f"https://consultaprocesos.ramajudicial.gov.co/api/v1/Procesos/NumeroRadicacion/{radicado}"
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, timeout=15)
        if resp.status_code == 200:
            datos = resp.json()
            if datos.get("procesos") and len(datos["procesos"]) > 0:
                # AQUÍ FUERZO LA CONVERSIÓN A STRING PARA EVITAR EL ERROR DE PANTALLA NEGRA
                return str(datos["procesos"][0].get("ultimaActuacion", "Sin actuaciones recientes"))
            return "No se encontraron registros"
        return f"Portal respondió con código: {resp.status_code}"
    except Exception as e:
        return f"Error de conexión local: {type(e).__name__}"

# INICIALIZACIÓN DE SESIÓN
if "logeado" not in st.session_state:
    st.session_state.update({"logeado": False, "usuario_id": None, "usuario_correo": ""})

st.title("⚖️ LexMonitor Pro")

# LÓGICA DE LOGIN / REGISTRO (Simplificada para estabilidad)
if not st.session_state["logeado"]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔑 Iniciar Sesión")
        with st.form("login"):
            c = st.text_input("Correo")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                conn = conectar_db()
                u = conn.cursor().execute("SELECT id, correo FROM usuarios WHERE correo=? AND password_hash=?", (c, encriptar_password(p))).fetchone()
                conn.close()
                if u:
                    st.session_state.update({"logeado": True, "usuario_id": u[0], "usuario_correo": u[1]})
                    st.rerun()
                else: st.error("Error en credenciales")
    with col2:
        st.subheader("📝 Registrar")
        with st.form("registro"):
            c = st.text_input("Correo ")
            p = st.text_input("Contraseña ", type="password")
            if st.form_submit_button("Crear cuenta"):
                conn = conectar_db()
                try:
                    conn.cursor().execute("INSERT INTO usuarios (correo, password_hash) VALUES (?, ?)", (c, encriptar_password(p)))
                    conn.commit()
                    st.success("Creado, inicie sesión.")
                except: st.error("Error en registro.")
                conn.close()
else:
    # PANEL PRINCIPAL
    if st.button("Cerrar Sesión"):
        st.session_state["logeado"] = False
        st.rerun()

    st.sidebar.header("📥 Nuevo Radicado")
    with st.sidebar.form("nuevo"):
        rad = st.text_input("Radicado")
        nom = st.text_input("Nombre Caso")
        if st.form_submit_button("Agregar"):
            conn = conectar_db()
            try:
                conn.cursor().execute("INSERT INTO radicados (usuario_id, numero_radicado, nombre_caso, ultima_actuacion, fecha_ultima_revision) VALUES (?, ?, ?, ?, ?)", 
                                     (st.session_state["usuario_id"], rad, nom, "Pendiente", "Nunca"))
                conn.commit()
            except: st.warning("Ya existe.")
            conn.close()

    st.header("📋 Procesos Activos")
    conn = conectar_db()
    procesos = conn.cursor().execute("SELECT id, numero_radicado, nombre_caso, ultima_actuacion, fecha_ultima_revision FROM radicados WHERE usuario_id=?", (st.session_state["usuario_id"],)).fetchall()
    conn.close()

    for pid, r, n, act, rev in procesos:
        with st.container(border=True):
            st.write(f"**Radicado:** {r} | **Cliente:** {n}")
            st.write(f"**Última Actuación:** {act}")
            if st.button(f"🔄 Actualizar {r}", key=f"btn_{pid}"):
                with st.spinner("Consultando..."):
                    res = consultar_rama_judicial_individual(r)
                    conn = conectar_db()
                    conn.cursor().execute("UPDATE radicados SET ultima_actuacion=?, fecha_ultima_revision=? WHERE id=?", (res, datetime.now().strftime("%Y-%m-%d %H:%M"), pid))
                    conn.commit()
                    conn.close()
                    st.rerun()
            if st.button(f"🗑️ Eliminar {r}", key=f"del_{pid}"):
                conn = conectar_db()
                conn.cursor().execute("DELETE FROM radicados WHERE id=?", (pid,))
                conn.commit()
                conn.close()
                st.rerun()