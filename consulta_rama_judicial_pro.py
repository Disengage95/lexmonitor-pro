import streamlit as st
import sqlite3
import requests
import pandas as pd
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# CONFIGURACIÓN DE LA PÁGINA WEB
st.set_page_config(page_title="LexMonitor - Control de Radicados", page_icon="⚖️", layout="wide")

# CONFIGURACIÓN DE CORREO SALIENTE (Conectado a los Secrets de Streamlit)
SMTP_SERVER = st.secrets["correo"]["smtp_server"]
SMTP_PORT = st.secrets["correo"]["smtp_port"]
EMAIL_EMISOR = st.secrets["correo"]["email_emisor"]
EMAIL_PASSWORD = st.secrets["correo"]["email_password"]

def enviar_alerta_correo(correo_destino, radicado, nombre_caso, nueva_actuacion):
    asunto = f"⚖️ ALERTA: Novedad en el proceso - {nombre_caso}"
    cuerpo_mensaje = f"""
    Estimado(a) Doctor(a),
    
    Le informamos que el sistema LexMonitor Pro ha detectado una nueva actuación en uno de sus procesos bajo monitoreo:
    
    - Caso / Cliente: {nombre_caso}
    - Número de Radicado: {radicado}
    - Nueva Actuación Registrada: {nueva_actuacion}
    - Fecha de Revisión: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    
    Cordialmente,
    Equipo de Soporte - LexMonitor Pro
    """
    msg = MIMEText(cuerpo_mensaje)
    msg["Subject"] = asunto
    msg["From"] = EMAIL_EMISOR
    msg["To"] = correo_destino
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_EMISOR, EMAIL_PASSWORD)
        server.sendmail(EMAIL_EMISOR, correo_destino, msg.as_string())
        server.quit()
        return True
    except Exception:
        return False

# BASE DE DATOS ROBUSTA
def conectar_db():
    conn = sqlite3.connect("procesos.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correo TEXT UNIQUE,
            password_hash TEXT,
            nombre_bufete TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS radicados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            numero_radicado TEXT,
            nombre_caso TEXT,
            ultima_actuacion TEXT,
            fecha_ultima_revision TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
            UNIQUE(usuario_id, numero_radicado)
        )
    ''')
    conn.commit()
    return conn

def encriptar_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def consultar_rama_judicial(radicado):
    url = f"https://consultaprocesos.ramajudicial.gov.co/api/v1/Procesos/NumeroRadicacion/{radicado}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Origin": "https://consultaprocesos.ramajudicial.gov.co",
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            datos = response.json()
            if "procesos" in datos and len(datos["procesos"]) > 0:
                ultima_actuacion = datos["procesos"][0].get("ultimaActuacion", "Sin actuaciones recientes")
                return ultima_actuacion
            else:
                return "Proceso no encontrado en la Rama Judicial (Verifica el radicado)"
        else:
            return f"Error de conexión con la Rama Judicial (Código: {response.status_code})"
            
    except requests.exceptions.Timeout:
        return "El servidor de la Rama Judicial tardó demasiado en responder (Timeout)"
    except Exception as e:
        return f"Error inesperado al consultar el juzgado: {str(e)}"

# Inicializar estados de sesión esenciales
if "logeado" not in st.session_state:
    st.session_state["logeado"] = False
    st.session_state["usuario_id"] = None
    st.session_state["usuario_correo"] = ""

st.title("⚖️ LexMonitor Pro")
st.subheader("Plataforma de Monitoreo Automatizado de Procesos - Rama Judicial")
st.markdown("---")

# MANEJO DE SESIONES (LOGIN / REGISTRO)
if not st.session_state["logeado"]:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔑 Iniciar Sesión")
        with st.form("form_login"):
            login_correo = st.text_input("Correo Electrónico")
            login_pass = st.text_input("Contraseña", type="password")
            boton_login = st.form_submit_button("Entrar a mi Panel")
            
            if boton_login:
                if login_correo and login_pass:
                    conn = conectar_db()
                    cursor = conn.cursor()
                    hash_p = encriptar_password(login_pass)
                    cursor.execute("SELECT id, correo FROM usuarios WHERE correo = ? AND password_hash = ?", (login_correo, hash_p))
                    usuario = cursor.fetchone()
                    conn.close()
                    
                    if usuario:
                        st.session_state["logeado"] = True
                        st.session_state["usuario_id"] = usuario[0]
                        st.session_state["usuario_correo"] = usuario[1]
                        st.success("¡Bienvenido doctor! Cargando panel...")
                        st.rerun()
                    else:
                        st.error("❌ Correo o contraseña incorrectos.")
                else:
                    st.error("Por favor completa todos los campos.")

    with col2:
        st.subheader("📝 Registrarse como Cliente")
        with st.form("form_registro", clear_on_submit=True):
            reg_correo = st.text_input("Correo Electrónico")
            reg_pass = st.text_input("Contraseña", type="password")
            reg_bufete = st.text_input("Nombre de la Firma / Bufete")
            boton_registro = st.form_submit_button("Crear Cuenta Suscripción")
            
            if boton_registro:
                if reg_correo and reg_pass:
                    conn = conectar_db()
                    cursor = conn.cursor()
                    hash_p = encriptar_password(reg_pass)
                    try:
                        cursor.execute("INSERT INTO usuarios (correo, password_hash, nombre_bufete) VALUES (?, ?, ?)", (reg_correo, hash_p, reg_bufete))
                        conn.commit()
                        st.success("🎉 ¡Cuenta creada con éxito! Ya puede iniciar sesión en el panel de la izquierda.")
                    except sqlite3.IntegrityError:
                        st.error("⚠️ Este correo ya se encuentra registrado.")
                    finally:
                        conn.close()
                else:
                    st.error("Por favor rellene los campos obligatorios.")

else:
    # PANEL DEL ABOGADO LOGUEADO
    st.sidebar.write(f"👤 **Bufete Activo:** {st.session_state['usuario_correo']}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["logeado"] = False
        st.session_state["usuario_id"] = None
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.header("📥 Registrar Nuevo Proceso")
    
    with st.sidebar.form("form_nuevo_proceso", clear_on_submit=True):
        nuevo_radicado = st.text_input("Número de Radicado (21 o 23 dígitos)", max_chars=23)
        nombre_caso = st.text_input("Nombre del Caso / Cliente")
        boton_agregar = st.form_submit_button("Agregar a Monitoreo")

        if boton_agregar:
            nuevo_radicado = nuevo_radicado.strip()
            
            if len(nuevo_radicado) == 21 and nuevo_radicado.isdigit():
                nuevo_radicado = nuevo_radicado + "00"
                
            if len(nuevo_radicado) == 23 and nuevo_radicado.isdigit():
                conn = conectar_db()
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                        INSERT INTO radicados (usuario_id, numero_radicado, nombre_caso, ultima_actuacion, fecha_ultima_revision)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (st.session_state["usuario_id"], nuevo_radicado, nombre_caso, "Pendiente de revisión", "Nunca"))
                    conn.commit()
                    st.success(f"✅ Radicado guardado exitosamente.")
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Ya está monitoreando este radicado.")
                finally:
                    conn.close()
                st.rerun()
            else:
                st.error("❌ El radicado debe tener 21 o 23 dígitos numéricos.")

    st.header("📋 Tus Procesos Activos")
    conn = conectar_db()
    df = pd.read_sql_query('''
        SELECT numero_radicado as 'Radicado', nombre_caso as 'Caso / Cliente', 
               ultima_actuacion as 'Última Actuación', fecha_ultima_revision as 'Última Revisión' 
        FROM radicados 
        WHERE usuario_id = ?
    ''', conn, params=(st.session_state["usuario_id"],))
    conn.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        if st.button("🔄 Ejecutar Revisión Diaria de Términos"):
            with st.spinner("Revisando estados de sus radicados..."):
                conn = conectar_db()
                cursor = conn.cursor()
                cursor.execute("SELECT id, numero_radicado, nombre_caso, ultima_actuacion FROM radicados WHERE usuario_id = ?", (st.session_state["usuario_id"],))
                procesos = cursor.fetchall()
                
                alertas_disparadas = 0
                for pid, rad, nombre, actuacion_anterior in procesos:
                    actuacion_actual = consultar_rama_judicial(rad)
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    if actuacion_actual != actuacion_anterior and actuacion_anterior != "Pendiente de revisión":
                        enviar_alerta_correo(st.session_state["usuario_correo"], rad, nombre, actuacion_actual)
                        alertas_disparadas += 1
                    
                    cursor.execute('''
                        UPDATE radicados 
                        SET ultima_actuacion = ?, fecha_ultima_revision = ?
                        WHERE id = ?
                    ''', (actuacion_actual, fecha_actual, pid))
                
                conn.commit()
                conn.close()
                
                if alertas_disparadas > 0:
                    st.success(f"ℹ️ Revisión terminada. Se detectaron {alertas_disparadas} cambios y se enviaron las alertas.")
                else:
                    st.success("ℹ️ Sus procesos se han actualizado. No se detectaron cambios nuevos.")
                st.rerun()
    else:
        st.info("Su cuenta no tiene procesos registrados. Utilice el panel lateral de la izquierda para guardar el primero.")