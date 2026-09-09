from PySide6.QtCore import QLibraryInfo, QTranslator


class _TraductorEspanolIntegrado(QTranslator):
    _TEXTOS = {
        "OK": "Aceptar",
        "&OK": "&Aceptar",
        "Yes": "Sí",
        "&Yes": "&Sí",
        "Yes to All": "Sí a todo",
        "&Yes to All": "Sí a &todo",
        "No": "No",
        "&No": "&No",
        "No to All": "No a todo",
        "N&o to All": "No a t&odo",
        "Cancel": "Cancelar",
        "&Cancel": "&Cancelar",
        "Save": "Guardar",
        "&Save": "&Guardar",
        "Close": "Cerrar",
        "&Close": "&Cerrar",
        "Open": "Abrir",
        "&Open": "&Abrir",
        "Apply": "Aplicar",
        "&Apply": "&Aplicar",
        "Reset": "Restablecer",
        "&Reset": "&Restablecer",
        "Retry": "Reintentar",
        "&Retry": "&Reintentar",
        "Ignore": "Ignorar",
        "&Ignore": "&Ignorar",
        "Discard": "Descartar",
        "&Discard": "&Descartar",
        "Help": "Ayuda",
        "&Help": "A&yuda",
        "Show Details...": "Mostrar detalles...",
        "Hide Details...": "Ocultar detalles...",
    }

    def translate(self, context, source_text, disambiguation=None, n=-1):
        return self._TEXTOS.get(source_text, "")


def configurar_idioma_espanol(aplicacion):
    if getattr(aplicacion, "_traductores_espanol", None) is not None:
        return aplicacion._traductores_espanol

    traductores = []
    ruta = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    qt = QTranslator(aplicacion)
    if qt.load("qtbase_es", ruta):
        aplicacion.installTranslator(qt)
        traductores.append(qt)

    integrado = _TraductorEspanolIntegrado(aplicacion)
    aplicacion.installTranslator(integrado)
    traductores.append(integrado)
    aplicacion._traductores_espanol = traductores
    return traductores
