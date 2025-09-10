import streamlit as st
import mysql.connector
import bcrypt
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Gestión - Bufete de Abogados",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para diseño responsivo
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        text-align: center;
        margin-bottom: 2rem;
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #374151;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
    }
    .status-en-proceso { background-color: #fbbf24; color: #92400e; }
    .status-completado { background-color: #34d399; color: #065f46; }
    .status-pendiente { background-color: #f87171; color: #991b1b; }
    
    @media (max-width: 768px) {
        .main-header { font-size: 1.8rem; }
        .sub-header { font-size: 1.2rem; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CONFIGURACIÓN DE BASE DE DATOS
# ==========================================

@st.cache_resource
def init_db_connection():
    """Inicializar conexión a la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(
            host=st.secrets.get("DB_HOST", "localhost"),
            user=st.secrets.get("DB_USER", "root"),
            password=st.secrets.get("DB_PASSWORD", ""),
            database=st.secrets.get("DB_NAME", "bufete_abogados"),
            autocommit=True
        )
        return connection
    except Exception as e:
        st.error(f"Error de conexión a la base de datos: {e}")
        return None

def execute_stored_procedure(procedure_name, params=None):
    """Ejecutar procedimiento almacenado"""
    try:
        conn = init_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            if params:
                cursor.callproc(procedure_name, params)
            else:
                cursor.callproc(procedure_name)
            
            results = []
            for result in cursor.stored_results():  # ✅ sin paréntesis
                results.extend(result.fetchall())
            
            cursor.close()
            return results
    except Exception as e:
        st.error(f"Error ejecutando procedimiento {procedure_name}: {e}")
        return []


def execute_query(query, params=None):
    """Ejecutar consulta SQL"""
    try:
        conn = init_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
            else:
                results = cursor.rowcount
            
            cursor.close()
            return results
    except Exception as e:
        st.error(f"Error ejecutando consulta: {e}")
        return [] if query.strip().upper().startswith('SELECT') else 0

# ==========================================
# FUNCIONES DE AUTENTICACIÓN
# ==========================================

def hash_password(password):
    """Generar hash de contraseña usando bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verificar contraseña"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def login_user(email, password):
    """Autenticar usuario"""
    users = execute_stored_procedure('sp_autenticar_usuario', [email])
    if users and verify_password(password, users[0]['hash_password']):
        return users[0]
    return None

def logout_user():
    """Cerrar sesión"""
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# ==========================================
# FUNCIONES DE GESTIÓN DE USUARIOS
# ==========================================

def get_user_profile(user_id, role):
    """Obtener perfil específico del usuario"""
    if role == 'abogado':
        query = """
        SELECT a.*, u.nombre, u.correo 
        FROM abogados a 
        JOIN usuarios u ON a.id_usuario = u.id 
        WHERE u.id = %s
        """
    elif role == 'cliente':
        query = """
        SELECT c.*, u.nombre, u.correo 
        FROM clientes c 
        JOIN usuarios u ON c.id_usuario = u.id 
        WHERE u.id = %s
        """
    else:
        return None
    
    result = execute_query(query, [user_id])
    return result[0] if result else None

def register_user(nombre, correo, rol, password, extra_data=None):
    """Registrar nuevo usuario"""
    try:
        hashed_pw = hash_password(password)
        execute_stored_procedure('sp_registrar_usuario', [nombre, correo, rol, hashed_pw])
        
        # Obtener ID del usuario creado
        user_result = execute_query("SELECT id FROM usuarios WHERE correo = %s", [correo])
        if user_result:
            user_id = user_result[0]['id']
            
            # Crear perfil específico
            if rol == 'abogado' and extra_data:
                execute_query("""
                    INSERT INTO abogados (id_usuario, especialidad, experiencia_anos, licencia_profesional, telefono)
                    VALUES (%s, %s, %s, %s, %s)
                """, [user_id, extra_data.get('especialidad'), extra_data.get('experiencia'), 
                     extra_data.get('licencia'), extra_data.get('telefono')])
            elif rol == 'cliente' and extra_data:
                execute_query("""
                    INSERT INTO clientes (id_usuario, direccion, telefono, cedula, fecha_nacimiento)
                    VALUES (%s, %s, %s, %s, %s)
                """, [user_id, extra_data.get('direccion'), extra_data.get('telefono'),
                     extra_data.get('cedula'), extra_data.get('fecha_nacimiento')])
        
        return True
    except Exception as e:
        st.error(f"Error registrando usuario: {e}")
        return False

# ==========================================
# INTERFAZ DE USUARIO - LOGIN
# ==========================================

def show_login_page():
    """Página de inicio de sesión"""
    st.markdown('<h1 class="main-header">⚖️ Sistema de Gestión - Bufete de Abogados</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Iniciar Sesión")
        
        email = st.text_input("📧 Correo Electrónico", placeholder="usuario@bufete.com")
        password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingrese su contraseña")
        
        col_login, col_register = st.columns(2)
        
        with col_login:
            if st.button("🚀 Iniciar Sesión", use_container_width=True):
                if email and password:
                    user = login_user(email, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.authenticated = True
                        st.success("✅ ¡Bienvenido!")
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas")
                else:
                    st.warning("⚠️ Complete todos los campos")
        
        with col_register:
            if st.button("📝 Registrar Usuario", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()

def show_register_page():
    """Página de registro de usuarios"""
    st.markdown('<h2 class="sub-header">📝 Registro de Nuevo Usuario</h2>', unsafe_allow_html=True)
    
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("Nombre Completo*")
            correo = st.text_input("Correo Electrónico*")
            password = st.text_input("Contraseña*", type="password")
        
        with col2:
            rol = st.selectbox("Rol*", ["cliente", "abogado", "administrador"])
            confirm_password = st.text_input("Confirmar Contraseña*", type="password")
        
        # Campos específicos según el rol
        extra_data = {}
        if rol == "abogado":
            st.subheader("Información Profesional")
            col3, col4 = st.columns(2)
            with col3:
                extra_data['especialidad'] = st.text_input("Especialidad")
                extra_data['experiencia'] = st.number_input("Años de Experiencia", min_value=0, max_value=50)
            with col4:
                extra_data['licencia'] = st.text_input("Licencia Profesional")
                extra_data['telefono'] = st.text_input("Teléfono")
        
        elif rol == "cliente":
            st.subheader("Información Personal")
            extra_data['direccion'] = st.text_area("Dirección")
            col5, col6 = st.columns(2)
            with col5:
                extra_data['telefono'] = st.text_input("Teléfono")
                extra_data['cedula'] = st.text_input("Cédula/DNI")
            with col6:
                extra_data['fecha_nacimiento'] = st.date_input("Fecha de Nacimiento")
        
        col_submit, col_cancel = st.columns(2)
        
        with col_submit:
            submitted = st.form_submit_button("✅ Registrar", use_container_width=True)
        
        with col_cancel:
            cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)
        
        if cancel:
            st.session_state.show_register = False
            st.rerun()
        
        if submitted:
            if not all([nombre, correo, password, confirm_password]):
                st.error("Complete todos los campos obligatorios")
            elif password != confirm_password:
                st.error("Las contraseñas no coinciden")
            else:
                if register_user(nombre, correo, rol, password, extra_data):
                    st.success("✅ Usuario registrado exitosamente")
                    st.session_state.show_register = False
                    st.rerun()

# ==========================================
# DASHBOARDS POR ROL
# ==========================================

def show_admin_dashboard():
    """Dashboard para administradores"""
    st.markdown('<h1 class="main-header">👤 Panel de Administrador</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumen", "👥 Usuarios", "📋 Casos", "📈 Reportes"])
    
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        
        # Métricas generales
        total_casos = execute_query("SELECT COUNT(*) as total FROM casos")[0]['total']
        total_abogados = execute_query("SELECT COUNT(*) as total FROM abogados")[0]['total']
        total_clientes = execute_query("SELECT COUNT(*) as total FROM clientes")[0]['total']
        casos_activos = execute_query("SELECT COUNT(*) as total FROM casos WHERE estado IN ('en_revision', 'en_proceso')")[0]['total']
        
        with col1:
            st.metric("Total Casos", total_casos)
        with col2:
            st.metric("Abogados Activos", total_abogados)
        with col3:
            st.metric("Clientes", total_clientes)
        with col4:
            st.metric("Casos Activos", casos_activos)
        
        # Gráfico de casos por estado
        casos_estado = execute_query("""
            SELECT estado, COUNT(*) as cantidad 
            FROM casos 
            GROUP BY estado
        """)
        if casos_estado:
            df_casos = pd.DataFrame(casos_estado)
            st.subheader("📊 Distribución de Casos por Estado")
            st.bar_chart(df_casos.set_index('estado'))
    
    with tab2:
        show_user_management()
    
    with tab3:
        show_case_management()
    
    with tab4:
        show_reports()

def show_lawyer_dashboard():
    """Dashboard para abogados"""
    st.markdown('<h1 class="main-header">⚖️ Panel de Abogado</h1>', unsafe_allow_html=True)
    
    # Obtener perfil del abogado
    profile = get_user_profile(st.session_state.user['id'], 'abogado')
    abogado_id = profile['id_abogado'] if profile else None
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Mis Casos", "📅 Agenda", "💬 Mensajes", "📁 Documentos"])
    
    with tab1:
        if abogado_id:
            mis_casos = execute_stored_procedure('sp_casos_por_abogado', [abogado_id])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Casos Asignados", len(mis_casos))
            with col2:
                casos_activos = len([c for c in mis_casos if c['estado'] in ['en_revision', 'en_proceso']])
                st.metric("Casos Activos", casos_activos)
            
            st.subheader("📋 Lista de Casos")
            if mis_casos:
                df_casos = pd.DataFrame(mis_casos)
                st.dataframe(df_casos, use_container_width=True)
            else:
                st.info("No tiene casos asignados")
    
    with tab2:
        show_calendar_management(abogado_id)
    
    with tab3:
        show_messaging(st.session_state.user['id'])
    
    with tab4:
        show_document_management()

def show_client_dashboard():
    """Dashboard para clientes"""
    st.markdown('<h1 class="main-header">👤 Portal del Cliente</h1>', unsafe_allow_html=True)
    
    # Obtener perfil del cliente
    profile = get_user_profile(st.session_state.user['id'], 'cliente')
    cliente_id = profile['id_cliente'] if profile else None
    
    tab1, tab2, tab3 = st.tabs(["📋 Mis Casos", "💬 Mensajes", "📄 Documentos"])
    
    with tab1:
        if cliente_id:
            mis_casos = execute_stored_procedure('sp_casos_por_cliente', [cliente_id])
            
            st.subheader("📊 Estado de Mis Casos")
            if mis_casos:
                for caso in mis_casos:
                    with st.expander(f"📁 {caso['titulo']} - {caso['tipo']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Estado:** {caso['estado']}")
                            st.write(f"**Fecha Inicio:** {caso['fecha_inicio']}")
                        with col2:
                            st.write(f"**Abogado:** {caso['abogado_nombre']}")
            else:
                st.info("No tiene casos registrados")
    
    with tab2:
        show_messaging(st.session_state.user['id'])
    
    with tab3:
        show_document_management(cliente_view=True)

# ==========================================
# MÓDULOS ESPECÍFICOS
# ==========================================

def show_user_management():
    """Gestión de usuarios"""
    st.subheader("👥 Gestión de Usuarios")
    
    # Listar usuarios existentes
    usuarios = execute_query("""
        SELECT u.id, u.nombre, u.correo, u.rol, u.estado, u.fecha_creacion
        FROM usuarios u
        ORDER BY u.fecha_creacion DESC
    """)
    
    if usuarios:
        df_usuarios = pd.DataFrame(usuarios)
        st.dataframe(df_usuarios, use_container_width=True)
    
    # Formulario para nuevo usuario
    with st.expander("➕ Agregar Nuevo Usuario"):
        show_register_page()

def show_case_management():
    """Gestión de casos"""
    st.subheader("📋 Gestión de Casos")
    
    # Listar casos existentes
    casos = execute_query("""
        SELECT c.id_caso, c.titulo, c.tipo, c.estado, c.fecha_inicio,
               u_cliente.nombre as cliente, u_abogado.nombre as abogado
        FROM casos c
        JOIN clientes cl ON c.id_cliente = cl.id_cliente
        JOIN usuarios u_cliente ON cl.id_usuario = u_cliente.id
        JOIN abogados ab ON c.id_abogado = ab.id_abogado
        JOIN usuarios u_abogado ON ab.id_usuario = u_abogado.id
        ORDER BY c.fecha_inicio DESC
    """)
    
    if casos:
        df_casos = pd.DataFrame(casos)
        st.dataframe(df_casos, use_container_width=True)
    
    # Formulario para nuevo caso
    with st.expander("➕ Crear Nuevo Caso"):
        with st.form("nuevo_caso"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Obtener clientes disponibles
                clientes = execute_query("""
                    SELECT c.id_cliente, u.nombre
                    FROM clientes c
                    JOIN usuarios u ON c.id_usuario = u.id
                    WHERE u.estado = 'activo'
                """)
                cliente_options = {f"{c['nombre']} (ID: {c['id_cliente']})": c['id_cliente'] for c in clientes}
                cliente_seleccionado = st.selectbox("Cliente", list(cliente_options.keys()) if cliente_options else [])
                
                titulo = st.text_input("Título del Caso*")
                tipo = st.selectbox("Tipo de Caso", [
                    "Derecho Civil", "Derecho Penal", "Derecho Laboral", 
                    "Derecho Familiar", "Derecho Comercial", "Otro"
                ])
            
            with col2:
                # Obtener abogados disponibles
                abogados = execute_query("""
                    SELECT a.id_abogado, u.nombre, a.especialidad
                    FROM abogados a
                    JOIN usuarios u ON a.id_usuario = u.id
                    WHERE u.estado = 'activo'
                """)
                abogado_options = {f"{a['nombre']} - {a['especialidad']} (ID: {a['id_abogado']})": a['id_abogado'] for a in abogados}
                abogado_seleccionado = st.selectbox("Abogado Asignado", list(abogado_options.keys()) if abogado_options else [])
                
                fecha_inicio = st.date_input("Fecha de Inicio", value=datetime.now().date())
                presupuesto = st.number_input("Presupuesto (S/)", min_value=0.0, step=100.0)
            
            descripcion = st.text_area("Descripción del Caso")
            
            if st.form_submit_button("✅ Crear Caso", use_container_width=True):
                if titulo and cliente_seleccionado and abogado_seleccionado:
                    try:
                        cliente_id = cliente_options[cliente_seleccionado]
                        abogado_id = abogado_options[abogado_seleccionado]
                        
                        execute_stored_procedure('sp_asignar_caso', [
                            cliente_id, abogado_id, titulo, tipo, descripcion, fecha_inicio, presupuesto
                        ])
                        st.success("✅ Caso creado exitosamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando caso: {e}")
                else:
                    st.error("Complete los campos obligatorios")

def show_calendar_management(abogado_id):
    """Gestión de calendario y citas"""
    st.subheader("📅 Gestión de Citas")
    
    if not abogado_id:
        st.error("No se pudo obtener información del abogado")
        return
    
    # Mostrar citas próximas
    citas_proximas = execute_query("""
        SELECT c.*, u.nombre as cliente_nombre, casos.titulo as caso_titulo
        FROM citas c
        JOIN clientes cl ON c.id_cliente = cl.id_cliente
        JOIN usuarios u ON cl.id_usuario = u.id
        LEFT JOIN casos ON c.id_caso = casos.id_caso
        WHERE c.id_abogado = %s AND c.fecha_cita >= CURDATE()
        ORDER BY c.fecha_cita, c.hora_cita
    """, [abogado_id])
    
    if citas_proximas:
        st.subheader("🗓️ Próximas Citas")
        for cita in citas_proximas:
            with st.expander(f"📅 {cita['fecha_cita']} - {cita['hora_cita']} | {cita['cliente_nombre']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Motivo:** {cita['motivo']}")
                    st.write(f"**Estado:** {cita['estado']}")
                with col2:
                    if cita['caso_titulo']:
                        st.write(f"**Caso:** {cita['caso_titulo']}")
                    if cita['notas']:
                        st.write(f"**Notas:** {cita['notas']}")
    
    # Formulario para nueva cita
    with st.expander("➕ Agendar Nueva Cita"):
        with st.form("nueva_cita"):
            # Obtener clientes del abogado
            clientes_abogado = execute_query("""
                SELECT DISTINCT cl.id_cliente, u.nombre
                FROM casos c
                JOIN clientes cl ON c.id_cliente = cl.id_cliente
                JOIN usuarios u ON cl.id_usuario = u.id
                WHERE c.id_abogado = %s
            """, [abogado_id])
            
            col1, col2 = st.columns(2)
            
            with col1:
                if clientes_abogado:
                    cliente_options = {c['nombre']: c['id_cliente'] for c in clientes_abogado}
                    cliente_seleccionado = st.selectbox("Cliente", list(cliente_options.keys()))
                    fecha_cita = st.date_input("Fecha de la Cita")
                    hora_cita = st.time_input("Hora de la Cita")
                else:
                    st.warning("No hay clientes asignados para agendar citas")
                    cliente_seleccionado = None
            
            with col2:
                # Obtener casos del cliente seleccionado
                if clientes_abogado and cliente_seleccionado:
                    cliente_id = cliente_options[cliente_seleccionado]
                    casos_cliente = execute_query("""
                        SELECT id_caso, titulo
                        FROM casos
                        WHERE id_cliente = %s AND id_abogado = %s
                    """, [cliente_id, abogado_id])
                    
                    caso_options = {c['titulo']: c['id_caso'] for c in casos_cliente}
                    caso_options['Sin caso específico'] = None
                    caso_seleccionado = st.selectbox("Caso Relacionado", list(caso_options.keys()))
                
                motivo = st.text_input("Motivo de la Cita")
            
            if st.form_submit_button("📅 Agendar Cita", use_container_width=True):
                if clientes_abogado and cliente_seleccionado and fecha_cita and hora_cita and motivo:
                    try:
                        cliente_id = cliente_options[cliente_seleccionado]
                        caso_id = caso_options.get(caso_seleccionado) if 'caso_seleccionado' in locals() else None
                        
                        execute_stored_procedure('sp_agendar_cita', [
                            abogado_id, cliente_id, caso_id, fecha_cita, hora_cita, motivo
                        ])
                        st.success("✅ Cita agendada exitosamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error agendando cita: {e}")

def show_messaging(user_id):
    """Sistema de mensajería"""
    st.subheader("💬 Centro de Mensajes")
    
    tab1, tab2 = st.tabs(["📥 Bandeja de Entrada", "✉️ Enviar Mensaje"])
    
    with tab1:
        # Mostrar mensajes recibidos
        mensajes_recibidos = execute_query("""
            SELECT m.*, u.nombre as remitente, c.titulo as caso_titulo
            FROM mensajes m
            JOIN usuarios u ON m.id_remitente = u.id
            LEFT JOIN casos c ON m.id_caso = c.id_caso
            WHERE m.id_destinatario = %s
            ORDER BY m.fecha_envio DESC
        """, [user_id])
        
        if mensajes_recibidos:
            for mensaje in mensajes_recibidos:
                with st.expander(f"✉️ De: {mensaje['remitente']} | {mensaje['fecha_envio']} {'🔴' if not mensaje['leido'] else ''}"):
                    if mensaje['caso_titulo']:
                        st.write(f"**Caso:** {mensaje['caso_titulo']}")
                    if mensaje['asunto']:
                        st.write(f"**Asunto:** {mensaje['asunto']}")
                    st.write(f"**Mensaje:** {mensaje['mensaje']}")
                    
                    if not mensaje['leido']:
                        if st.button(f"✅ Marcar como leído", key=f"read_{mensaje['id_mensaje']}"):
                            execute_query("UPDATE mensajes SET leido = TRUE WHERE id_mensaje = %s", [mensaje['id_mensaje']])
                            st.rerun()
        else:
            st.info("No hay mensajes en la bandeja de entrada")
    
    with tab2:
        # Formulario para enviar mensaje
        with st.form("enviar_mensaje"):
            # Obtener destinatarios disponibles según el rol
            user_role = st.session_state.user['rol']
            
            if user_role == 'cliente':
                # Cliente puede enviar mensajes solo a sus abogados
                destinatarios = execute_query("""
                    SELECT DISTINCT u.id, u.nombre
                    FROM usuarios u
                    JOIN abogados a ON u.id = a.id_usuario
                    JOIN casos c ON a.id_abogado = c.id_abogado
                    JOIN clientes cl ON c.id_cliente = cl.id_cliente
                    WHERE cl.id_usuario = %s
                """, [user_id])
            else:
                # Abogados y administradores pueden enviar a cualquier usuario activo
                destinatarios = execute_query("""
                    SELECT id, nombre, rol
                    FROM usuarios
                    WHERE estado = 'activo' AND id != %s
                """, [user_id])
            
            if destinatarios:
                destinatario_options = {f"{d['nombre']} ({d.get('rol', 'Usuario')})": d['id'] for d in destinatarios}
                destinatario_seleccionado = st.selectbox("Destinatario", list(destinatario_options.keys()))
                
                # Obtener casos relevantes
                casos_disponibles = execute_query("""
                    SELECT c.id_caso, c.titulo
                    FROM casos c
                    WHERE c.id_abogado IN (
                        SELECT a.id_abogado FROM abogados a WHERE a.id_usuario = %s
                    ) OR c.id_cliente IN (
                        SELECT cl.id_cliente FROM clientes cl WHERE cl.id_usuario = %s
                    )
                """, [user_id, user_id])
                
                caso_options = {'Sin caso específico': None}
                if casos_disponibles:
                    caso_options.update({c['titulo']: c['id_caso'] for c in casos_disponibles})
                
                caso_seleccionado = st.selectbox("Caso Relacionado (opcional)", list(caso_options.keys()))
                asunto = st.text_input("Asunto")
                mensaje = st.text_area("Mensaje*")
                
                if st.form_submit_button("📤 Enviar Mensaje", use_container_width=True):
                    if destinatario_seleccionado and mensaje:
                        try:
                            destinatario_id = destinatario_options[destinatario_seleccionado]
                            caso_id = caso_options[caso_seleccionado]
                            
                            execute_query("""
                                INSERT INTO mensajes (id_remitente, id_destinatario, id_caso, asunto, mensaje)
                                VALUES (%s, %s, %s, %s, %s)
                            """, [user_id, destinatario_id, caso_id, asunto, mensaje])
                            
                            st.success("✅ Mensaje enviado exitosamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error enviando mensaje: {e}")
                    else:
                        st.error("Complete los campos obligatorios")
            else:
                st.info("No hay destinatarios disponibles")

def show_document_management(cliente_view=False):
    """Gestión de documentos"""
    st.subheader("📁 Gestión de Documentos")
    
    user_id = st.session_state.user['id']
    user_role = st.session_state.user['rol']
    
    # Obtener casos disponibles según el rol del usuario
    if user_role == 'cliente':
        profile = get_user_profile(user_id, 'cliente')
        cliente_id = profile['id_cliente'] if profile else None
        casos_disponibles = execute_query("""
            SELECT c.id_caso, c.titulo
            FROM casos c
            WHERE c.id_cliente = %s
        """, [cliente_id])
    elif user_role == 'abogado':
        profile = get_user_profile(user_id, 'abogado')
        abogado_id = profile['id_abogado'] if profile else None
        casos_disponibles = execute_query("""
            SELECT c.id_caso, c.titulo
            FROM casos c
            WHERE c.id_abogado = %s
        """, [abogado_id])
    else:  # administrador
        casos_disponibles = execute_query("SELECT id_caso, titulo FROM casos")
    
    if casos_disponibles:
        caso_options = {c['titulo']: c['id_caso'] for c in casos_disponibles}
        caso_seleccionado = st.selectbox("Seleccionar Caso", list(caso_options.keys()))
        
        if caso_seleccionado:
            caso_id = caso_options[caso_seleccionado]
            
            # Mostrar documentos del caso
            documentos = execute_query("""
                SELECT d.*, u.nombre as subido_por_nombre
                FROM documentos d
                JOIN usuarios u ON d.subido_por = u.id
                WHERE d.id_caso = %s
                ORDER BY d.fecha_subida DESC
            """, [caso_id])
            
            if documentos:
                st.subheader(f"📄 Documentos del Caso: {caso_seleccionado}")
                for doc in documentos:
                    with st.expander(f"📎 {doc['nombre_archivo']} (v{doc['version']})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Tipo:** {doc['tipo_documento']}")
                            st.write(f"**Tamaño:** {doc['tamanio_kb']} KB")
                        with col2:
                            st.write(f"**Subido por:** {doc['subido_por_nombre']}")
                            st.write(f"**Fecha:** {doc['fecha_subida']}")
                        
                        # Simulación de descarga (en producción sería descarga real)
                        if st.button(f"⬇️ Descargar", key=f"download_{doc['id_doc']}"):
                            st.info(f"Descargando: {doc['nombre_archivo']}")
            
            # Formulario para subir documentos (solo si no es cliente o es su propio caso)
            if not cliente_view or user_role != 'cliente':
                with st.expander("📤 Subir Nuevo Documento"):
                    uploaded_file = st.file_uploader(
                        "Seleccionar archivo",
                        type=['pdf', 'doc', 'docx', 'jpg', 'png', 'txt']
                    )
                    
                    if uploaded_file:
                        col1, col2 = st.columns(2)
                        with col1:
                            tipo_documento = st.selectbox("Tipo de Documento", [
                                "Contrato", "Demanda", "Resolución", "Prueba", 
                                "Comunicación", "Informe", "Otro"
                            ])
                        
                        if st.button("📤 Subir Documento", use_container_width=True):
                            try:
                                # Simular guardado de archivo (en producción se guardaría en servidor/cloud)
                                file_size = len(uploaded_file.getvalue()) // 1024  # KB
                                file_path = f"uploads/{caso_id}/{uploaded_file.name}"
                                
                                execute_stored_procedure('sp_subir_documento', [
                                    caso_id, uploaded_file.name, file_path, 
                                    tipo_documento, file_size, user_id
                                ])
                                
                                st.success("✅ Documento subido exitosamente")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error subiendo documento: {e}")
    else:
        st.info("No hay casos disponibles para gestionar documentos")

def show_reports():
    """Módulo de reportes y estadísticas"""
    st.subheader("📈 Reportes y Estadísticas")
    
    tab1, tab2, tab3 = st.tabs(["📊 Casos", "👥 Abogados", "💰 Financiero"])
    
    with tab1:
        st.subheader("📋 Reporte de Casos")
        
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha Inicio", value=datetime(2024, 1, 1).date())
        with col2:
            fecha_fin = st.date_input("Fecha Fin", value=datetime.now().date())
        
        if st.button("🔍 Generar Reporte de Casos"):
            reporte_casos = execute_stored_procedure('sp_generar_reporte_casos', [None, fecha_inicio, fecha_fin])
            
            if reporte_casos:
                df_reporte = pd.DataFrame(reporte_casos)
                
                # Mostrar métricas
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Casos", len(df_reporte))
                with col2:
                    casos_ganados = len(df_reporte[df_reporte['estado'] == 'ganado'])
                    st.metric("Casos Ganados", casos_ganados)
                with col3:
                    casos_perdidos = len(df_reporte[df_reporte['estado'] == 'perdido'])
                    st.metric("Casos Perdidos", casos_perdidos)
                with col4:
                    if casos_ganados + casos_perdidos > 0:
                        tasa_exito = casos_ganados / (casos_ganados + casos_perdidos) * 100
                        st.metric("Tasa de Éxito", f"{tasa_exito:.1f}%")
                
                # Tabla detallada
                st.subheader("📋 Detalle de Casos")
                st.dataframe(df_reporte, use_container_width=True)
                
                # Gráficos
                if len(df_reporte) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Casos por tipo
                        casos_por_tipo = df_reporte['tipo'].value_counts()
                        st.subheader("📊 Casos por Tipo")
                        st.bar_chart(casos_por_tipo)
                    
                    with col2:
                        # Casos por estado
                        casos_por_estado = df_reporte['estado'].value_counts()
                        st.subheader("📈 Casos por Estado")
                        st.bar_chart(casos_por_estado)
            else:
                st.info("No hay datos para el período seleccionado")
    
    with tab2:
        st.subheader("👥 Rendimiento de Abogados")
        
        # Estadísticas por abogado
        estadisticas_abogados = execute_query("""
            SELECT 
                u.nombre as abogado,
                COUNT(c.id_caso) as total_casos,
                SUM(CASE WHEN c.estado = 'ganado' THEN 1 ELSE 0 END) as casos_ganados,
                SUM(CASE WHEN c.estado = 'perdido' THEN 1 ELSE 0 END) as casos_perdidos,
                SUM(CASE WHEN c.estado IN ('en_revision', 'en_proceso') THEN 1 ELSE 0 END) as casos_activos
            FROM abogados a
            JOIN usuarios u ON a.id_usuario = u.id
            LEFT JOIN casos c ON a.id_abogado = c.id_abogado
            GROUP BY a.id_abogado, u.nombre
            ORDER BY total_casos DESC
        """)

        if estadisticas_abogados:
            df_abogados = pd.DataFrame(estadisticas_abogados)

            # 🔧 Normaliza a numérico por si vienen Decimals/None/strings
            for col in ["total_casos", "casos_ganados", "casos_perdidos", "casos_activos"]:
                df_abogados[col] = pd.to_numeric(df_abogados[col], errors="coerce").fillna(0)

            # ✅ Evita división por 0 y asegura tipos numéricos
            g = df_abogados["casos_ganados"]
            p = df_abogados["casos_perdidos"]
            den = g + p
            df_abogados["tasa_exito"] = (g.div(den.where(den != 0, 1)).mul(100)).round(1)

            st.dataframe(df_abogados, use_container_width=True)

            if len(df_abogados) > 0:
                st.subheader("📊 Casos Totales por Abogado")
                st.bar_chart(df_abogados.set_index('abogado')["total_casos"])
        else:
            st.info("No hay estadísticas de abogados disponibles")
    
    with tab3:
        st.subheader("💰 Reporte Financiero")
        
        # Resumen financiero
        resumen_financiero = execute_query("""
            SELECT 
                COUNT(*) as total_casos,
                SUM(presupuesto) as presupuesto_total,
                AVG(presupuesto) as presupuesto_promedio,
                SUM(CASE WHEN estado = 'ganado' THEN presupuesto ELSE 0 END) as ingresos_ganados
            FROM casos
            WHERE presupuesto IS NOT NULL
        """)
        
        if resumen_financiero:
            datos = resumen_financiero[0]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Casos", datos['total_casos'])
            with col2:
                st.metric("Presupuesto Total", f"S/ {datos['presupuesto_total']:,.2f}")
            with col3:
                st.metric("Presupuesto Promedio", f"S/ {datos['presupuesto_promedio']:,.2f}")
            with col4:
                st.metric("Ingresos por Casos Ganados", f"S/ {datos['ingresos_ganados']:,.2f}")
            
            # Ingresos por mes (simulado)
            ingresos_mes = execute_query("""
                SELECT 
                    MONTH(fecha_inicio) as mes,
                    YEAR(fecha_inicio) as año,
                    SUM(presupuesto) as presupuesto_mes
                FROM casos
                WHERE presupuesto IS NOT NULL
                GROUP BY YEAR(fecha_inicio), MONTH(fecha_inicio)
                ORDER BY año, mes
            """)
            
            if ingresos_mes:
                df_ingresos = pd.DataFrame(ingresos_mes)
                df_ingresos['periodo'] = df_ingresos['año'].astype(str) + '-' + df_ingresos['mes'].astype(str).str.zfill(2)
                
                st.subheader("📈 Presupuesto por Mes")
                st.line_chart(df_ingresos.set_index('periodo')['presupuesto_mes'])

# ==========================================
# APLICACIÓN PRINCIPAL
# ==========================================

def main():
    """Función principal de la aplicación"""
    
    # Inicializar estado de sesión
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'show_register' not in st.session_state:
        st.session_state.show_register = False
    
    # Sidebar con información del usuario si está autenticado
    if st.session_state.authenticated and st.session_state.user:
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"**👤 Usuario:** {st.session_state.user['nombre']}")
            st.markdown(f"**🎭 Rol:** {st.session_state.user['rol'].title()}")
            st.markdown(f"**📧 Email:** {st.session_state.user['correo']}")
            st.markdown("---")
            
            if st.button("🚪 Cerrar Sesión", use_container_width=True):
                logout_user()
    
    # Lógica de navegación
    if not st.session_state.authenticated:
        if st.session_state.show_register:
            show_register_page()
        else:
            show_login_page()
    else:
        # Mostrar dashboard según el rol del usuario
        user_role = st.session_state.user['rol']
        
        if user_role == 'administrador':
            show_admin_dashboard()
        elif user_role == 'abogado':
            show_lawyer_dashboard()
        elif user_role == 'cliente':
            show_client_dashboard()

if __name__ == "__main__":
    main()