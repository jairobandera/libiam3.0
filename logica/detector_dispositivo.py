def detectar_dispositivo(df):

    columnas = [c.lower() for c in df.columns]

    if any(c in columnas for c in ["fx", "fy", "fz"]):
        return "Plataforma de Fuerza"

    if any("emg" in c for c in columnas):
        return "Delsys Trigno (EMG)"

    return "CSV Genérico"