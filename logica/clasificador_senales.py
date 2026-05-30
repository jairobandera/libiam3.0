def clasificar_senales(df):

    grupos = {
        "Fuerza": [],
        "Momento": [],
        "COP": [],
        "EMG": [],
    }

    for col in df.columns:

        c = col.lower()

        if c.startswith("fx") or c.startswith("fy") or c.startswith("fz"):
            grupos["Fuerza"].append(col)

        elif c.startswith("mx") or c.startswith("my") or c.startswith("mz"):
            grupos["Momento"].append(col)

        elif "cop" in c:
            grupos["COP"].append(col)

        elif "emg" in c:
            grupos["EMG"].append(col)

    return grupos