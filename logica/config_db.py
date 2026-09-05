import os
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, ForeignKey
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


class VariableArchivo(Base):
    __tablename__ = "variable_archivo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ruta_archivo = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    valor = Column(Float, nullable=False)


class FormulaPersonalizada(Base):
    __tablename__ = "formula_personalizada"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clave = Column(String, unique=True, nullable=False)
    nombre = Column(String, nullable=False)
    expresion = Column(String, nullable=False)
    unidad = Column(String, nullable=False, default="")
    descripcion = Column(String, nullable=False, default="")
    reutilizable = Column(Boolean, nullable=False, default=True)
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

    _asegurar_aliases_iniciales(session)

    session.close()
    return engine


def _asegurar_aliases_iniciales(session):
    """Agrega aliases incorporados en versiones nuevas sin pisar los aprendidos."""
    aliases_requeridos = [
        ("cx", "COP", "eje_x"),
        ("cy", "COP", "eje_y"),
        ("cz", "COP", "eje_z"),
    ]
    existentes = {
        alias.nombre for alias in session.query(AliasColumna).filter(
            AliasColumna.nombre.in_([nombre for nombre, _, _ in aliases_requeridos])
        )
    }
    for nombre, tipo, eje in aliases_requeridos:
        if nombre not in existentes:
            session.add(AliasColumna(nombre=nombre, tipo=tipo, eje=eje))
    session.commit()


def _migrar_db(engine):
    """Agrega columnas nuevas a tablas existentes si no existen."""
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(seccion_archivo)"))
        columnas = [row[1] for row in result]
        if "activo" not in columnas:
            conn.execute(text("ALTER TABLE seccion_archivo ADD COLUMN activo BOOLEAN DEFAULT 1"))
            conn.commit()

        result = conn.execute(text("PRAGMA table_info(formula_personalizada)"))
        columnas = [row[1] for row in result]
        if "reutilizable" not in columnas:
            conn.execute(text(
                "ALTER TABLE formula_personalizada "
                "ADD COLUMN reutilizable BOOLEAN NOT NULL DEFAULT 1"
            ))
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


def guardar_variable_archivo(session, ruta_archivo, nombre, valor):
    """Guarda (o actualiza) el valor de una variable numérica de un archivo."""
    existente = session.query(VariableArchivo).filter_by(
        ruta_archivo=ruta_archivo, nombre=nombre.lower()
    ).first()
    if existente:
        existente.valor = float(valor)
    else:
        session.add(VariableArchivo(
            ruta_archivo=ruta_archivo,
            nombre=nombre.lower(),
            valor=float(valor),
        ))
    session.commit()


def obtener_variable_archivo(session, ruta_archivo, nombre):
    """Retorna el valor guardado de una variable para un archivo, o None."""
    variable = session.query(VariableArchivo).filter_by(
        ruta_archivo=ruta_archivo, nombre=nombre.lower()
    ).first()
    return variable.valor if variable else None


def eliminar_variable_archivo(session, ruta_archivo, nombre):
    """Elimina una variable para que un valor viejo no reaparezca al recargar."""
    session.query(VariableArchivo).filter_by(
        ruta_archivo=ruta_archivo, nombre=nombre.lower()
    ).delete(synchronize_session=False)
    session.commit()


def formula_personalizada_a_dict(formula):
    return {
        "id": formula.id,
        "clave": formula.clave,
        "nombre": formula.nombre,
        "expresion": formula.expresion,
        "unidad": formula.unidad or "",
        "descripcion": formula.descripcion or "",
        "reutilizable": bool(formula.reutilizable),
    }


def listar_formulas_personalizadas(session):
    """Fórmulas guardadas por el usuario, listas para cargar en el registro."""
    return session.query(FormulaPersonalizada).filter_by(
        activo=True
    ).order_by(FormulaPersonalizada.nombre).all()


def guardar_formula_personalizada(
    session,
    nombre,
    expresion,
    unidad="",
    descripcion="",
    reutilizable=True,
    clave=None,
):
    """Crea o actualiza una fórmula sin modificar las incorporadas al programa."""
    nombre = str(nombre or "").strip()
    if not nombre:
        raise ValueError("Ingresá un nombre para la fórmula.")

    existente = (
        session.query(FormulaPersonalizada).filter_by(clave=clave).first()
        if clave
        else None
    )
    repetida = next(
        (
            formula
            for formula in session.query(FormulaPersonalizada).filter_by(activo=True)
            if formula.nombre.strip().casefold() == nombre.casefold()
            and (existente is None or formula.id != existente.id)
        ),
        None,
    )
    if repetida is not None:
        raise ValueError("Ya existe una fórmula guardada con ese nombre.")

    if existente is None:
        clave = f"personalizada_{uuid.uuid4().hex}"
        existente = FormulaPersonalizada(clave=clave)
        session.add(existente)

    existente.nombre = nombre
    existente.expresion = str(expresion or "").strip()
    existente.unidad = str(unidad or "").strip()
    existente.descripcion = str(descripcion or "").strip()
    existente.reutilizable = bool(reutilizable)
    existente.activo = True
    session.commit()
    session.refresh(existente)
    return existente


def importar_formulas_personalizadas(session, formulas):
    """Guarda un lote ya validado en una única transacción.

    Las claves internas siempre se regeneran en el equipo que importa. Los
    nombres deben llegar resueltos para no reemplazar fórmulas existentes.
    """
    formulas = list(formulas or [])
    nombres_existentes = {
        formula.nombre.strip().casefold()
        for formula in session.query(FormulaPersonalizada).filter_by(activo=True)
    }
    nombres_lote = set()
    registros = []
    try:
        for datos in formulas:
            nombre = str(datos.get("nombre") or "").strip()
            nombre_clave = nombre.casefold()
            if not nombre:
                raise ValueError("Ingresá un nombre para cada fórmula.")
            if nombre_clave in nombres_existentes or nombre_clave in nombres_lote:
                raise ValueError(
                    f"Ya existe una fórmula guardada con el nombre «{nombre}»."
                )
            registro = FormulaPersonalizada(
                clave=f"personalizada_{uuid.uuid4().hex}",
                nombre=nombre,
                expresion=str(datos.get("expresion") or "").strip(),
                unidad=str(datos.get("unidad") or "").strip(),
                descripcion=str(datos.get("descripcion") or "").strip(),
                reutilizable=bool(datos.get("reutilizable", True)),
                activo=True,
            )
            session.add(registro)
            registros.append(registro)
            nombres_lote.add(nombre_clave)
        session.commit()
        for registro in registros:
            session.refresh(registro)
        return registros
    except Exception:
        session.rollback()
        raise


def eliminar_formula_personalizada(session, clave):
    formula = session.query(FormulaPersonalizada).filter_by(clave=clave).first()
    if formula is None:
        return False
    formula.activo = False
    session.commit()
    return True


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
