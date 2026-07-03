import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "libiam_config.db")

Base = declarative_base()


class AliasColumna(Base):
    __tablename__ = "alias_columna"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, unique=True, nullable=False)
    tipo = Column(String, nullable=False)
    eje = Column(String, nullable=False, default="ninguno")

    cabeceras_asignadas = relationship("CabeceraAsignada", back_populates="alias")


class SeccionArchivo(Base):
    __tablename__ = "seccion_archivo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ruta_archivo = Column(String, nullable=False)
    fila_inicio = Column(Integer, nullable=False)
    fila_fin = Column(Integer, nullable=False)
    columnas = Column(String, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)


class CabeceraAsignada(Base):
    __tablename__ = "cabecera_asignada"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ruta_archivo = Column(String, nullable=False)
    alias_id = Column(Integer, ForeignKey("alias_columna.id"), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)

    alias = relationship("AliasColumna", back_populates="cabeceras_asignadas")


def _crear_engine():
    return create_engine(f"sqlite:///{DB_PATH}")


def init_db():
    engine = _crear_engine()
    Base.metadata.create_all(engine)
    _migrar_db(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    if session.query(AliasColumna).count() == 0:
        _seed_inicial(session)

    session.close()
    return engine


def _migrar_db(engine):
    """Agrega columnas nuevas a tablas existentes si no existen."""
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(seccion_archivo)"))
        columnas = [row[1] for row in result]
        if "activo" not in columnas:
            conn.execute(text("ALTER TABLE seccion_archivo ADD COLUMN activo BOOLEAN DEFAULT 1"))
            conn.commit()


def _seed_inicial(session):
    seeds = [
        ("fx", "Fuerza", "eje_x"),
        ("fy", "Fuerza", "eje_y"),
        ("fz", "Fuerza", "eje_z"),
        ("force_x", "Fuerza", "eje_x"),
        ("force_y", "Fuerza", "eje_y"),
        ("force_z", "Fuerza", "eje_z"),
        ("fuerza_x", "Fuerza", "eje_x"),
        ("fuerza_y", "Fuerza", "eje_y"),
        ("fuerza_z", "Fuerza", "eje_z"),
        ("force_1", "Fuerza", "eje_x"),
        ("force_2", "Fuerza", "eje_y"),
        ("force_3", "Fuerza", "eje_z"),
        ("fuerzax", "Fuerza", "eje_x"),
        ("fuerzay", "Fuerza", "eje_y"),
        ("fuerzaz", "Fuerza", "eje_z"),
        ("potenciax", "Fuerza", "eje_x"),
        ("empujey", "Fuerza", "eje_y"),
        ("cargaz", "Fuerza", "eje_z"),
        ("mx", "Momento", "eje_x"),
        ("my", "Momento", "eje_y"),
        ("mz", "Momento", "eje_z"),
        ("moment_x", "Momento", "eje_x"),
        ("moment_y", "Momento", "eje_y"),
        ("moment_z", "Momento", "eje_z"),
        ("momento_x", "Momento", "eje_x"),
        ("momento_y", "Momento", "eje_y"),
        ("momento_z", "Momento", "eje_z"),
        ("torque_x", "Momento", "eje_x"),
        ("torque_y", "Momento", "eje_y"),
        ("torque_z", "Momento", "eje_z"),
        ("copx", "COP", "eje_x"),
        ("copy", "COP", "eje_y"),
        ("copz", "COP", "eje_z"),
        ("cop_x", "COP", "eje_x"),
        ("cop_y", "COP", "eje_y"),
        ("cop_z", "COP", "eje_z"),
        ("centro_presion_x", "COP", "eje_x"),
        ("centro_presion_y", "COP", "eje_y"),
        ("centro_presion_z", "COP", "eje_z"),
        ("center_pressure_x", "COP", "eje_x"),
        ("center_pressure_y", "COP", "eje_y"),
        ("center_pressure_z", "COP", "eje_z"),
        ("centropresiona", "COP", "eje_x"),
        ("centropresionb", "COP", "eje_y"),
        ("time", "Tiempo", "ninguno"),
        ("time_s", "Tiempo", "ninguno"),
        ("tiempo", "Tiempo", "ninguno"),
        ("t_s", "Tiempo", "ninguno"),
        ("timestamp", "Tiempo", "ninguno"),
        ("frame", "Frame", "ninguno"),
        ("muestra", "Frame", "ninguno"),
        ("sample", "Frame", "ninguno"),
        ("n_frame", "Frame", "ninguno"),
    ]

    for nombre, tipo, eje in seeds:
        session.add(AliasColumna(nombre=nombre, tipo=tipo, eje=eje))

    session.commit()


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()


def cargar_aliases(session):
    aliases = session.query(AliasColumna).all()
    resultado = {}

    for alias in aliases:
        tipo = alias.tipo
        if tipo not in resultado:
            resultado[tipo] = {}

        if alias.eje != "ninguno":
            if alias.eje not in resultado[tipo]:
                resultado[tipo][alias.eje] = []
            resultado[tipo][alias.eje].append(alias.nombre.lower())
        else:
            if "_simple" not in resultado[tipo]:
                resultado[tipo]["_simple"] = []
            resultado[tipo]["_simple"].append(alias.nombre.lower())

    return resultado


def agregar_alias(session, nombre, tipo, eje="ninguno"):
    existente = session.query(AliasColumna).filter_by(nombre=nombre.lower()).first()
    if existente:
        existente.tipo = tipo
        existente.eje = eje
    else:
        session.add(AliasColumna(nombre=nombre.lower(), tipo=tipo, eje=eje))
    session.commit()


def eliminar_alias(session, nombre):
    alias = session.query(AliasColumna).filter_by(nombre=nombre.lower()).first()
    if alias:
        session.delete(alias)
        session.commit()
    return alias is not None


def listar_aliases(session):
    return session.query(AliasColumna).order_by(AliasColumna.tipo, AliasColumna.eje).all()


def buscar_alias(session, nombre_columna):
    nombre_lower = nombre_columna.lower().strip()

    # 1. Match exacto
    alias = session.query(AliasColumna).filter_by(nombre=nombre_lower).first()
    if alias:
        return {"tipo": alias.tipo, "eje": alias.eje}

    # 2. Match parcial: buscar aliases que esten contenidos en el nombre
    # Elegir el alias mas largo (mas especifico)
    todos = session.query(AliasColumna).all()
    mejores_matches = []

    for alias in todos:
        if alias.nombre in nombre_lower:
            mejores_matches.append(alias)

    if mejores_matches:
        # Ordenar por longitud descendente y elegir el mas largo
        mejores_matches.sort(key=lambda a: len(a.nombre), reverse=True)
        mejor = mejores_matches[0]
        return {"tipo": mejor.tipo, "eje": mejor.eje}

    return None


def guardar_seccion_archivo(session, ruta_archivo, fila_inicio, fila_fin, columnas):
    existente = session.query(SeccionArchivo).filter_by(
        ruta_archivo=ruta_archivo,
        fila_inicio=fila_inicio,
        fila_fin=fila_fin,
    ).first()
    if existente:
        existente.columnas = columnas
        existente.activo = True
    else:
        session.add(SeccionArchivo(
            ruta_archivo=ruta_archivo,
            fila_inicio=fila_inicio,
            fila_fin=fila_fin,
            columnas=columnas,
            activo=True,
        ))
    session.commit()


def desactivar_secciones_archivo(session, ruta_archivo):
    """Marca todas las secciones de un archivo como inactivas (activo=False)."""
    session.query(SeccionArchivo).filter_by(
        ruta_archivo=ruta_archivo
    ).update({"activo": False})
    session.commit()


def listar_secciones_archivo(session, ruta_archivo):
    return session.query(SeccionArchivo).filter_by(
        ruta_archivo=ruta_archivo, activo=True
    ).order_by(SeccionArchivo.fila_inicio).all()


def eliminar_seccion_archivo(session, seccion_id):
    seccion = session.query(SeccionArchivo).filter_by(id=seccion_id).first()
    if seccion:
        session.delete(seccion)
        session.commit()
    return seccion is not None


def guardar_cabecera_asignada(session, ruta_archivo, nombre, tipo, eje):
    """Guarda un alias en alias_columna y lo vincula al archivo en cabecera_asignada."""
    agregar_alias(session, nombre, tipo, eje)

    alias = session.query(AliasColumna).filter_by(nombre=nombre.lower()).first()

    existente = session.query(CabeceraAsignada).filter_by(
        ruta_archivo=ruta_archivo, alias_id=alias.id
    ).first()

    if existente:
        existente.activo = True
    else:
        session.add(CabeceraAsignada(ruta_archivo=ruta_archivo, alias_id=alias.id, activo=True))
    session.commit()


def desactivar_cabeceras_archivo(session, ruta_archivo):
    """Marca todas las cabeceras asignadas de un archivo como inactivas."""
    session.query(CabeceraAsignada).filter_by(
        ruta_archivo=ruta_archivo
    ).update({"activo": False})
    session.commit()


def desactivar_cabecera(session, cabecera_id):
    """Marca una cabecera asignada individual como inactiva."""
    cab = session.query(CabeceraAsignada).filter_by(id=cabecera_id).first()
    if cab:
        cab.activo = False
        session.commit()
    return cab is not None


def listar_cabeceras_asignadas(session, ruta_archivo):
    """Retorna las cabeceras asignadas activas para un archivo, con datos del alias."""
    resultado = []
    cabeceras = session.query(CabeceraAsignada).filter_by(
        ruta_archivo=ruta_archivo, activo=True
    ).all()

    for cab in cabeceras:
        if cab.alias:
            resultado.append({
                "id": cab.id,
                "nombre": cab.alias.nombre,
                "tipo": cab.alias.tipo,
                "eje": cab.alias.eje,
            })
    return resultado
