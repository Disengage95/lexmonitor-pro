import streamlit as st
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import requests
import json

# CONFIGURACIÓN DE LA PÁGINA WEB
st.set_page_config(page_title="LexMonitor - Control de Radicados", page_icon="⚖️", layout="wide")

# CONTROL ROBUSTO DE SECRETOS
try:
    SMTP_SERVER = st.secrets["correo"]["smtp_server"]
    SMTP_PORT = st.secrets["correo"]["smtp_port"]
    EMAIL_EMISOR = st.secrets["correo"]["email_emisor"]
    EMAIL_PASSWORD = st.secrets["correo"]["email_password"]
    CORREO_CONFIGURADO = True
except Exception:
    SMTP_SERVER = ""
    SMTP_PORT = 587
    EMAIL_EMISOR = ""
    EMAIL_PASSWORD = ""
    CORREO_CONFIGURADO = False

def enviar_alerta_correo(correo_destino, radicado, nombre_caso, nueva_actuacion):
    if not CORREO_CONFIGURADO:
        return False
        
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

# BASE DE DATOS
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

# FUNCIÓN INDIVIDUAL DE CONSULTA (Bypass de Red Seguro)
def consultar_rama_judicial_individual(radicado):
    url_objetivo = f"https://consultaprocesos.ramajudicial.gov.co/api/v1/Procesos/NumeroRadicacion/{radicado}"
    url_proxy = f"https://api.allorigins.win/get?url={url_objetivo}"
    try:
        respuesta = requests.get(url_proxy, timeout=15)
        if respuesta.status_code == 200:
            contenedor_proxy = respuesta.json()
            datos_originales = json.loads(contenedor_proxy["contents"])
            if datos_originales.get("procesos") and len(datos_originales["procesos"]) > 0:
                return datos_originales["procesos"][0].get("ultimaActuacion", "Sin actuaciones recientes")
            else:
                return "No encontrado (Verifique que el radicado exista en la web judicial)"
        else:
            return f"Error en bypass de red (Status {respuesta.status_code})"
    except Exception:
        return "Servidor judicial saturado, reintente en unos minutos"

# Inicializar estados de sesión esenciales
if "logeado" not in st.session_state:
    st.session_state["logeado"] = False
    st.session_state["usuario_id"] = None
    st.session_state["usuario_correo"] = ""

st.title("⚖️ LexMonitor Pro")
st.subheader("Plataforma de Monitoreo Automatizado de Procesos - Rama Judicial")
if not CORREO_CONFIGURADO:
    st.warning("⚠️ Modo Local Activo: Utilizando bypass de conexión para IPs residenciales.")
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
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, numero_radicado, nombre_caso, ultima_actuacion, fecha_ultima_revision 
        FROM radicados 
        WHERE usuario_id = ?
    ''', (st.session_state["usuario_id"],))
    procesos_usuario = cursor.fetchall()
    conn.close()

    # MOSTRAR LISTADO DE TARJETAS
    if procesos_usuario:
        for pid, rad, nombre, actuacion, revision in procesos_usuario:
            with st.container(border=True):
                col_info, col_acciones = st.columns([4.2, 1.8])
                
                with col_info:
                    st.markdown(f"**⚖️ Radicado:** `{rad}`")
                    st.markdown(f"**👤 Caso / Cliente:** {nombre}")
                    st.markdown(f"**📄 Última Actuación:** {actuacion}")
                    st.markdown(f"**🕒 Última Revisión:** {revision}")
                
                with col_acciones:
                    st.write("")  
                    # BOTÓN DE CONSULTA INDIVIDUAL
                    if st.button("🔄 Actualizar este proceso", key=f"upd_{pid}", type="secondary", use_container_width=True):
                        with st.spinner("Consultando proceso..."):
                            actuacion_real = consultar_rama_judicial_individual(rad)
                            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                            
                            # Guardar en base de datos inmediatamente
                            conn = conectar_db()
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE radicados SET ultima_actuacion = ?, fecha_ultima_revision = ? WHERE id = ?
                            ''', (actuacion_real, fecha_actual, pid))
                            conn.commit()
                            conn.close()
                            
                            # Alerta por correo si cambió
                            if actuacion_real != actuacion and actuacion != "Pendiente de revisión" and "Error" not in actuacion_real:
                                enviar_alerta_correo(st.session_state["usuario_correo"], rad, nombre, actuacion_real)
                                
                            st.rerun()
                    
                    # BOTÓN DE ELIMINAR INDIVIDUAL
                    if st.button("🗑️ Eliminar Proceso", key=f"del_{pid}", type="primary", use_container_width=True):
                        conn = conectar_db()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM radicados WHERE id = ?", (pid,))
                        conn.commit()
                        conn.close()
                        st.rerun()
                        
        st.markdown("---")
        
        # BOTÓN GLOBAL (POR SI ACASO SE REQUIERE ACTUALIZAR TODO AL TIEMPO)
        if st.button("🔄 Ejecutar Revisión de TODOS los Términos", type="secondary"):
            with st.spinner("Actualizando todo el historial de procesos..."):
                conn = conectar_db()
                cursor = conn.cursor()
                
                for pid, rad, nombre, actuacion_anterior, revision_anterior in procesos_usuario:
                    actuacion_real = consultar_rama_judicial_individual(rad)
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    cursor.execute('''
                        UPDATE radicados SET ultima_actuacion = ?, fecha_ultima_revision = ? WHERE id = ?
                    ''', (actuacion_real, fecha_actual, pid))
                    
                    if actuacion_real != actuacion_anterior and actuacion_anterior != "Pendiente de revisión" and "Error" not in actuacion_real:
                        enviar_alerta_correo(st.session_state["usuario_correo"], rad, nombre, actuacion_real)
                
                conn.commit()
                conn.close()
                st.rerun()
    else:
        st.info("Su cuenta no tiene procesos registrados. Utilice el panel lateral de la izquierda para guardar el primero.")