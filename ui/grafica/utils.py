def separar_señales(señales_visibles):

    nuevo = {}

    for categoria, señales in señales_visibles.items():
        for señal in señales:
            nuevo[señal] = [señal]

    return nuevo


def normalizar(signal):

    min_val = signal.min()
    max_val = signal.max()

    if max_val - min_val == 0:
        return signal

    return (signal - min_val) / (max_val - min_val)