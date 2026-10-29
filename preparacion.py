"""Preparación de datos - Momento 2.
Uso:  python preparacion.py   -> genera frutales_limpio.csv y muestra el registro de limpieza.
El dashboard (app.py) llama a la misma función limpiar(), así que no hay pasos manuales ocultos.
"""
import pandas as pd

def limpiar(ruta="frutales.csv", verbose=False):
    d = pd.read_csv(ruta, dtype=str)
    log = {"filas_originales": len(d)}
    # 1. Producción viene como texto "2.124,4": quitar puntos de miles y cambiar coma decimal
    d["Produccion_toneladas"] = (d["Produccion_toneladas"].str.replace(".", "", regex=False)
                                 .str.replace(",", ".", regex=False).astype(float))
    # 2. Faltantes: se revisan columna por columna. Estrategia: si hubiera vacíos se eliminaría la fila
    #    (no se imputa, porque inventar toneladas cambiaría los totales). En este dataset hay 0 vacíos.
    log["celdas_vacias"] = int(d.isna().sum().sum())
    d = d.dropna()
    # 3. Duplicados exactos: se eliminan (misma fila repetida = mismo dato contado dos veces)
    antes = len(d)
    d = d.drop_duplicates()
    log["duplicados_eliminados"] = antes - len(d)
    # 4. Ceros: se conservan (son reportes reales de producción nula) y se anotan como limitación
    log["registros_en_cero"] = int((d["Produccion_toneladas"] == 0).sum())
    # 5. Tipos y nombres
    d = d.rename(columns={"año": "anio"})
    d["anio"] = d["anio"].astype(int)
    d["Subregion"] = d["Subregion"].replace({"Pacifico": "Pacífico"})
    log["filas_finales"] = len(d)
    if verbose:
        for k, v in log.items():
            print(f"{k:>24}: {v}")
    return d, log

if __name__ == "__main__":
    df, _ = limpiar(verbose=True)
    df.to_csv("frutales_limpio.csv", index=False)
    print("Guardado frutales_limpio.csv")
