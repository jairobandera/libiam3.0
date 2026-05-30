import pandas as pd

def cargar_csv(file_path):

    try:
        df = pd.read_csv(
            file_path,
            sep=None,
            engine="python",
            encoding="utf-8",
            on_bad_lines="skip"
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            file_path,
            sep=None,
            engine="python",
            encoding="latin-1",
            on_bad_lines="skip"
        )

    return df