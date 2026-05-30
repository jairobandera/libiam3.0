def aplicar_formula(df, formula, mask):

    region_df = df.loc[mask].copy()

    region_df.eval(
        formula,
        inplace=True
    )

    nueva_columna = formula.split("=")[0].strip()

    df[nueva_columna] = None

    df.loc[
        mask,
        nueva_columna
    ] = region_df[nueva_columna]

    return df