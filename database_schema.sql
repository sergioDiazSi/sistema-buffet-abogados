-- Base de Datos para Sistema de Gestión de Bufete de Abogados
CREATE DATABASE IF NOT EXISTS bufete_abogados;
USE bufete_abogados;

-- Tabla de usuarios base
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    rol ENUM('administrador', 'abogado', 'cliente') NOT NULL,
    hash_password VARCHAR(255) NOT NULL,
    estado ENUM('activo', 'inactivo', 'suspendido') DEFAULT 'activo',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tabla de abogados
CREATE TABLE abogados (
    id_abogado INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    especialidad VARCHAR(100),
    experiencia_anos INT,
    licencia_profesional VARCHAR(50),
    telefono VARCHAR(20),
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Tabla de clientes
CREATE TABLE clientes (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    direccion TEXT,
    telefono VARCHAR(20),
    cedula VARCHAR(20),
    fecha_nacimiento DATE,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Tabla de casos
CREATE TABLE casos (
    id_caso INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_abogado INT NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    tipo VARCHAR(100) NOT NULL,
    descripcion TEXT,
    estado ENUM('en_revision', 'en_proceso', 'archivado', 'ganado', 'perdido') DEFAULT 'en_revision',
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    presupuesto DECIMAL(10,2),
    notas TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE RESTRICT,
    FOREIGN KEY (id_abogado) REFERENCES abogados(id_abogado) ON DELETE RESTRICT
);

-- Tabla de documentos
CREATE TABLE documentos (
    id_doc INT AUTO_INCREMENT PRIMARY KEY,
    id_caso INT NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta VARCHAR(500) NOT NULL,
    version INT DEFAULT 1,
    tipo_documento VARCHAR(50),
    tamanio_kb INT,
    fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    subido_por INT NOT NULL,
    FOREIGN KEY (id_caso) REFERENCES casos(id_caso) ON DELETE CASCADE,
    FOREIGN KEY (subido_por) REFERENCES usuarios(id)
);

-- Tabla de citas
CREATE TABLE citas (
    id_cita INT AUTO_INCREMENT PRIMARY KEY,
    id_abogado INT NOT NULL,
    id_cliente INT NOT NULL,
    id_caso INT,
    fecha_cita DATE NOT NULL,
    hora_cita TIME NOT NULL,
    motivo VARCHAR(200),
    estado ENUM('programada', 'confirmada', 'completada', 'cancelada') DEFAULT 'programada',
    notas TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_abogado) REFERENCES abogados(id_abogado),
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente),
    FOREIGN KEY (id_caso) REFERENCES casos(id_caso)
);

-- Tabla de mensajería
CREATE TABLE mensajes (
    id_mensaje INT AUTO_INCREMENT PRIMARY KEY,
    id_remitente INT NOT NULL,
    id_destinatario INT NOT NULL,
    id_caso INT,
    asunto VARCHAR(200),
    mensaje TEXT NOT NULL,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    leido BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (id_remitente) REFERENCES usuarios(id),
    FOREIGN KEY (id_destinatario) REFERENCES usuarios(id),
    FOREIGN KEY (id_caso) REFERENCES casos(id_caso)
);

-- ===============================
-- PROCEDIMIENTOS ALMACENADOS
-- ===============================

DELIMITER //

-- Procedimiento para registrar usuario
CREATE PROCEDURE sp_registrar_usuario(
    IN p_nombre VARCHAR(100),
    IN p_correo VARCHAR(100),
    IN p_rol ENUM('administrador', 'abogado', 'cliente'),
    IN p_hash_password VARCHAR(255)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    INSERT INTO usuarios (nombre, correo, rol, hash_password) 
    VALUES (p_nombre, p_correo, p_rol, p_hash_password);
    COMMIT;
END //

-- Procedimiento para asignar caso
CREATE PROCEDURE sp_asignar_caso(
    IN p_id_cliente INT,
    IN p_id_abogado INT,
    IN p_titulo VARCHAR(200),
    IN p_tipo VARCHAR(100),
    IN p_descripcion TEXT,
    IN p_fecha_inicio DATE,
    IN p_presupuesto DECIMAL(10,2)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    INSERT INTO casos (id_cliente, id_abogado, titulo, tipo, descripcion, fecha_inicio, presupuesto)
    VALUES (p_id_cliente, p_id_abogado, p_titulo, p_tipo, p_descripcion, p_fecha_inicio, p_presupuesto);
    COMMIT;
END //

-- Procedimiento para agendar cita
CREATE PROCEDURE sp_agendar_cita(
    IN p_id_abogado INT,
    IN p_id_cliente INT,
    IN p_id_caso INT,
    IN p_fecha_cita DATE,
    IN p_hora_cita TIME,
    IN p_motivo VARCHAR(200)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    INSERT INTO citas (id_abogado, id_cliente, id_caso, fecha_cita, hora_cita, motivo)
    VALUES (p_id_abogado, p_id_cliente, p_id_caso, p_fecha_cita, p_hora_cita, p_motivo);
    COMMIT;
END //

-- Procedimiento para subir documento
CREATE PROCEDURE sp_subir_documento(
    IN p_id_caso INT,
    IN p_nombre_archivo VARCHAR(255),
    IN p_ruta VARCHAR(500),
    IN p_tipo_documento VARCHAR(50),
    IN p_tamanio_kb INT,
    IN p_subido_por INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    INSERT INTO documentos (id_caso, nombre_archivo, ruta, tipo_documento, tamanio_kb, subido_por)
    VALUES (p_id_caso, p_nombre_archivo, p_ruta, p_tipo_documento, p_tamanio_kb, p_subido_por);
    COMMIT;
END //

-- Procedimiento para generar reporte de casos
CREATE PROCEDURE sp_generar_reporte_casos(
    IN p_id_abogado INT,
    IN p_fecha_inicio DATE,
    IN p_fecha_fin DATE
)
BEGIN
    SELECT 
        c.id_caso,
        c.titulo,
        c.tipo,
        c.estado,
        c.fecha_inicio,
        c.fecha_fin,
        cl.nombre as cliente_nombre,
        ab.nombre as abogado_nombre
    FROM casos c
    JOIN clientes cl_table ON c.id_cliente = cl_table.id_cliente
    JOIN usuarios cl ON cl_table.id_usuario = cl.id
    JOIN abogados ab_table ON c.id_abogado = ab_table.id_abogado
    JOIN usuarios ab ON ab_table.id_usuario = ab.id
    WHERE (p_id_abogado IS NULL OR c.id_abogado = p_id_abogado)
    AND c.fecha_inicio BETWEEN p_fecha_inicio AND p_fecha_fin
    ORDER BY c.fecha_inicio DESC;
END //

-- Procedimiento para autenticación
CREATE PROCEDURE sp_autenticar_usuario(
    IN p_correo VARCHAR(100)
)
BEGIN
    SELECT id, nombre, correo, rol, hash_password, estado
    FROM usuarios 
    WHERE correo = p_correo AND estado = 'activo';
END //

-- Procedimiento para obtener casos por abogado
CREATE PROCEDURE sp_casos_por_abogado(
    IN p_id_abogado INT
)
BEGIN
    SELECT 
        c.id_caso,
        c.titulo,
        c.tipo,
        c.estado,
        c.fecha_inicio,
        u.nombre as cliente_nombre
    FROM casos c
    JOIN clientes cl ON c.id_cliente = cl.id_cliente
    JOIN usuarios u ON cl.id_usuario = u.id
    WHERE c.id_abogado = p_id_abogado
    ORDER BY c.fecha_inicio DESC;
END //

-- Procedimiento para obtener casos por cliente
CREATE PROCEDURE sp_casos_por_cliente(
    IN p_id_cliente INT
)
BEGIN
    SELECT 
        c.id_caso,
        c.titulo,
        c.tipo,
        c.estado,
        c.fecha_inicio,
        u.nombre as abogado_nombre
    FROM casos c
    JOIN abogados a ON c.id_abogado = a.id_abogado
    JOIN usuarios u ON a.id_usuario = u.id
    WHERE c.id_cliente = p_id_cliente
    ORDER BY c.fecha_inicio DESC;
END //

DELIMITER ;
