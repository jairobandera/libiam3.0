from scipy.signal import butter, filtfilt

class ProcesamientoFiltros:
    MAPA_TIPOS = {
        "Butterworth": "lowpass",
        "Butterworth High-pass": "highpass",
        "Butterworth Band-pass": "bandpass",
        "Butterworth Band-stop": "bandstop",
    }

    @classmethod
    def aplicar(cls, tipo_filtro, y, orden, fc_low, fc_high, fs):
        btype_real = cls.MAPA_TIPOS.get(tipo_filtro) # Obtener el tipo real del filtro
        if btype_real is None:
            raise ValueError(f"Tipo de filtro desconocido: {tipo_filtro}")

        nyq = fs / 2.0 # Calcular la frecuencia de Nyquist. Ningun fitro digital puede trabajar por encima de Nyquist.

    #--------------------------------------------------------------------------------------------------------------------
    #Paso banda o rechazo
    #Ejemplo: fc_low = 20, fc_high = 100, fs = 1000
        if btype_real in ("lowpass", "highpass"):
            Wn = fc_low / nyq #Wn=[0.02,0.10]
            btype = "low" if btype_real == "lowpass" else "high"
        else:
            Wn = [fc_low / nyq, fc_high / nyq]
            btype = "band" if btype_real == "bandpass" else "bandstop"

        b, a = butter(orden, Wn, btype=btype)
        return filtfilt(b, a, y)

#En la linea 30
#Dentro de butter() SciPy hace automaticamente esto:
# 1-Toma el orden del filtro.
# 2-Toma la frecuencia de corte normalizada (Wn) que debe estar entre 0 y 1, donde 1 corresponde a la frecuencia de Nyquist.
# 3-Determina el tipo de filtro (low, high, band, bandstop) según el parámetro btype.
# 4-Construye el filtro digital Butterworth.
# 5-Calcula los polos del filtro.
# 6-Si corresponde, transforma el paso bajo en pasos altos,paso banda o rechazo de banda.
# 7-Convrierte el filtro analógico en digital (transformación bilineal).
# 8-Calcula los coeficientes b y a y los devuelve.
# 
#  ¿Qué son b y a?
# Los coeficientes b y a son los coeficientes del filtro.
# Por ejemplo, podria quedar asi:
# b = [0.0048, 0.0193, 0.0289, 0.0193, 0.0048]
# a = [1.0000, -2.3695, 2.3140, -1.0547, 0.1874]
# Estos numeros son de los resultados matematicos, yo no calculo nada, los calcula SciPy.