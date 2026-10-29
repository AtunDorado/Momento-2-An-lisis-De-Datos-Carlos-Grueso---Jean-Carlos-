"""Dashboard Momento 2 - Producción de frutales del Valle del Cauca (2000-2022).
Ejecutar:  streamlit run app.py
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from preparacion import limpiar

st.set_page_config(page_title="Frutales Valle del Cauca", layout="wide")
VERDE, NARANJA, GRIS = "#2f7d4f", "#b0561c", "#b9bfba"
UMBRAL = 500  # t mínimas en cada tramo para comparar crecimiento (mismo criterio del Momento 1)


@st.cache_data
def cargar():
    return limpiar("frutales.csv")


df, log = cargar()


def fmt(x):
    if x >= 1e6:
        return f"{x/1e6:,.2f} M".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{x:,.0f}".replace(",", ".")


def pct(x):
    return f"{x:+.0f}%"


# ---------------- Filtros ----------------
st.sidebar.header("Filtros")
subs = st.sidebar.multiselect("Subregión", ["Centro", "Norte", "Sur", "Pacífico"],
                              default=["Centro", "Norte", "Sur", "Pacífico"])
orden_cult = df.groupby("Cultivo")["Produccion_toneladas"].sum().sort_values(ascending=False).index.tolist()
cults = st.sidebar.multiselect("Cultivos (vacío = todos)", orden_cult, default=[], placeholder="Todos los cultivos")
ciclos = st.sidebar.multiselect("Ciclo", ["Anual", "Semestre 1", "Semestre 2"],
                                default=["Anual", "Semestre 1", "Semestre 2"])
y0, y1 = st.sidebar.slider("Periodo", 2000, 2022, (2000, 2022))
metrica = st.sidebar.radio("Métrica", ["Total (t)", "Mediana por registro (t)"],
                           help="La mediana es el valor típico de un registro; no la afectan los pocos registros gigantes.")
st.sidebar.caption("Fuente: datos.gov.co · MinAgricultura, Evaluaciones Agropecuarias Municipales. Descarga 28-sep-2026.")

f = df[(df.Subregion.isin(subs)) & (df.Ciclo.isin(ciclos)) & (df.anio.between(y0, y1))]
if cults:
    f = f[f.Cultivo.isin(cults)]

st.title("El Valle casi duplicó su fruta, pero la sostienen cuatro cultivos")
st.caption("Producción frutícola del Valle del Cauca 2000–2022 · cada indicador y gráfico responde a los filtros de la izquierda")

if f.empty:
    st.warning("No hay registros para esta combinación de filtros. Agregue subregiones, cultivos o ciclos, o amplíe el periodo.")
    st.stop()

agg = "sum" if metrica.startswith("Total") else "median"
P = "Produccion_toneladas"

# ---------------- Cálculos ----------------
anios = list(range(y0, y1 + 1))
por_anio = f.groupby("anio")[P].sum().reindex(anios, fill_value=0)
total = f[P].sum()
k = max(1, min(5, len(anios) // 2))
ini, fin = por_anio.iloc[:k].sum(), por_anio.iloc[-k:].sum()
crec = (fin / ini - 1) * 100 if ini > 0 else None
r_anio = np.corrcoef(por_anio.index, por_anio.values)[0, 1] if len(anios) >= 3 and por_anio.std() > 0 else None
por_cult = f.groupby("Cultivo")[P].sum().sort_values(ascending=False)
por_mun = f.groupby("Municipio")[P].sum().sort_values(ascending=False)
lider_share = por_cult.iloc[0] / total * 100 if total else 0
top5_mun = por_mun.head(5).sum() / total * 100 if total else 0
tramo = f"{y0}–{y0+k-1} vs {y1-k+1}–{y1}" if k > 1 else f"{y0} vs {y1}"

# ---------------- KPIs ----------------
c = st.columns(5)
c[0].metric("Producción total", f"{fmt(total)} t", f"{len(f):,} registros".replace(",", "."), delta_color="off")
c[1].metric("Crecimiento entre tramos", pct(crec) if crec is not None else "—", tramo, delta_color="off",
            help="Compara la suma de los primeros 5 años con la de los últimos 5 años del periodo.")
c[2].metric("Tendencia con el año (r)", f"{r_anio:.2f}".replace(".", ",") if r_anio is not None else "—",
            ("crecimiento sostenido" if r_anio and r_anio >= .7 else "caída sostenida" if r_anio and r_anio <= -.7
             else "tendencia moderada" if r_anio and abs(r_anio) >= .4 else "sin tendencia clara"), delta_color="off")
c[3].metric("Peso del cultivo líder", f"{lider_share:.1f}%".replace(".", ","), por_cult.index[0], delta_color="off",
            help="Riesgo de dependencia: qué parte de la producción depende de un solo cultivo.")
c[4].metric("Concentración territorial", f"{top5_mun:.1f}%".replace(".", ","),
            f"top 5 de {f.Municipio.nunique()} municipios", delta_color="off")

# Lectura dinámica
crec_c = pd.DataFrame({
    "ini": f[f.anio < y0 + k].groupby("Cultivo")[P].sum(),
    "fin": f[f.anio > y1 - k].groupby("Cultivo")[P].sum()}).fillna(0)
crec_c = crec_c[(crec_c.ini >= UMBRAL) & (crec_c.fin >= UMBRAL)].copy()
crec_c["cambio"] = (crec_c.fin / crec_c.ini - 1) * 100
crec_c = crec_c.sort_values("cambio", ascending=False)
txt = (f"**Lectura de la selección:** {por_cult.index[0]} aporta el {lider_share:.1f}%".replace(".", ",")
       + f" y {por_mun.index[0]} es el municipio que más produce. ")
if crec is not None:
    txt += f"La producción {'creció' if crec >= 0 else 'cayó'} {pct(crec)} ({tramo}). "
if len(crec_c) >= 2:
    txt += (f"Más dinámico: {crec_c.index[0]} ({pct(crec_c.cambio.iloc[0])}); "
            f"mayor retroceso: {crec_c.index[-1]} ({pct(crec_c.cambio.iloc[-1])}).")
st.info(txt)

# ---------------- Gráfico 1: tendencia ----------------
serie = f.groupby("anio")[P].agg(agg).reindex(anios, fill_value=0)
tit1 = (f"La producción {'sube' if (crec or 0) >= 0 else 'baja'} {pct(crec)} entre tramos (r = {r_anio:.2f})".replace(".", ",")
        if crec is not None and r_anio is not None else "Producción por año")
fig1 = go.Figure(go.Scatter(x=serie.index, y=serie.values, mode="lines+markers", line=dict(color=VERDE, width=3),
                            fill="tozeroy", fillcolor="rgba(47,125,79,.12)",
                            hovertemplate="%{x}: %{y:,.0f} t<extra></extra>"))
if len(anios) >= 4:
    for a, b in [(y0, y0 + k - 1), (y1 - k + 1, y1)]:
        fig1.add_vrect(x0=a - .4, x1=b + .4, fillcolor=GRIS, opacity=.2, line_width=0)
fig1.update_layout(title=tit1, xaxis_title="Año", yaxis_title=f"Producción – {metrica.lower()}",
                   yaxis_rangemode="tozero", height=380, margin=dict(t=60, b=40))
st.plotly_chart(fig1, width="stretch")
st.caption("Bandas grises: los dos tramos que compara el KPI de crecimiento. El eje vertical empieza en cero.")

col1, col2 = st.columns(2)

# ---------------- Gráfico 2: top 10 ----------------
with col1:
    dim = st.radio("Ver top 10 por", ["Cultivo", "Municipio"], horizontal=True)
    top = f.groupby(dim)[P].agg(agg).sort_values(ascending=False).head(10)
    share10 = f.groupby(dim)[P].sum().sort_values(ascending=False).head(10).sum() / total * 100
    tit2 = (f"El top 10 de {dim.lower()}s concentra el {share10:.1f}%".replace(".", ",") if agg == "sum"
            else f"Mayor mediana por registro: {top.index[0]}")
    fig2 = px.bar(x=top.values[::-1], y=top.index[::-1], orientation="h",
                  color=[("Líder" if i == len(top) - 1 else "Resto") for i in range(len(top))],
                  color_discrete_map={"Líder": VERDE, "Resto": GRIS})
    fig2.update_layout(title=tit2, xaxis_title=f"Producción – {metrica.lower()}", yaxis_title=dim,
                       showlegend=False, height=420)
    st.plotly_chart(fig2, width="stretch")

# ---------------- Gráfico 3: crecimiento por cultivo ----------------
with col2:
    if len(crec_c) >= 2:
        sel = pd.concat([crec_c.head(7), crec_c.tail(7)]) if len(crec_c) > 14 else crec_c
        sel = sel[~sel.index.duplicated()].sort_values("cambio")
        sube = (crec_c.cambio > 0).sum()
        fig3 = px.bar(sel, x="cambio", y=sel.index, orientation="h",
                      color=np.where(sel.cambio >= 0, "Crece", "Retrocede"),
                      color_discrete_map={"Crece": VERDE, "Retrocede": NARANJA},
                      custom_data=["ini", "fin"])
        fig3.update_traces(hovertemplate="%{y}: %{x:+.0f}%<br>Primer tramo %{customdata[0]:,.0f} t<br>Último tramo %{customdata[1]:,.0f} t<extra></extra>")
        fig3.update_layout(title=f"{sube} de {len(crec_c)} cultivos crecen; {len(crec_c)-sube} retroceden",
                           xaxis_title=f"Cambio % ({tramo})", yaxis_title="Cultivo", legend_title="", height=420)
        st.plotly_chart(fig3, width="stretch")
        st.caption(f"Solo cultivos con al menos {UMBRAL} t en ambos tramos (evita porcentajes enormes sobre bases mínimas).")
    else:
        st.warning("Se necesitan al menos 2 cultivos con producción en ambos tramos para comparar crecimiento.")

col3, col4 = st.columns(2)

# ---------------- Gráfico 4: subregiones (categórica vs numérica) ----------------
with col3:
    g = f.groupby("Subregion")[P].agg(total="sum", mediana="median", registros="count").reindex(
        ["Centro", "Norte", "Sur", "Pacífico"]).dropna()
    g["participacion"] = g.total / g.total.sum() * 100
    lider = g.participacion.idxmax()
    fig4 = px.bar(g, x=g.index, y="mediana" if agg == "median" else "participacion",
                  color=[("Líder" if i == lider else "Resto") for i in g.index],
                  color_discrete_map={"Líder": VERDE, "Resto": GRIS},
                  custom_data=["registros", "mediana", "participacion"])
    fig4.update_traces(hovertemplate="%{x}<br>Participación %{customdata[2]:.1f}%<br>Mediana %{customdata[1]:,.0f} t"
                                     "<br>%{customdata[0]} registros<extra></extra>")
    fig4.update_layout(title=f"{lider} aporta el {g.participacion.max():.1f}% de la producción".replace(".", ","),
                       xaxis_title="Subregión",
                       yaxis_title="Mediana por registro (t)" if agg == "median" else "Participación en la producción (%)",
                       showlegend=False, height=400)
    st.plotly_chart(fig4, width="stretch")
    st.caption("Comparación de grupos (categórica vs numérica): por eso se usa la mediana y no la correlación. "
               "Pacífico tiene pocos registros, todos anuales.")

# ---------------- Gráfico 5: heatmap de correlación ----------------
with col4:
    top8 = f.groupby("Cultivo")[P].sum().sort_values(ascending=False).head(8).index
    piv = (f[f.Cultivo.isin(top8)].pivot_table(index="anio", columns="Cultivo", values=P, aggfunc="sum")
           .reindex(anios).fillna(0)[list(top8)])
    if len(top8) >= 2 and len(anios) >= 4:
        piv["Año"] = piv.index
        m = piv.corr().fillna(0)
        tri = m.where(~np.eye(len(m), dtype=bool)).drop(index="Año", columns="Año").abs().stack()
        a, b = tri.idxmax()
        rv = m.loc[a, b]
        fig5 = px.imshow(m.round(2), text_auto=".2f", zmin=-1, zmax=1, aspect="auto",
                         color_continuous_scale=[[0, NARANJA], [.5, "#f1f1ee"], [1, VERDE]])
        fig5.update_layout(title=f"{a} y {b} {'se mueven juntos' if rv > 0 else 'van en sentido opuesto'} (r = {rv:.2f})".replace(".", ","),
                           height=400, coloraxis_colorbar_title="r")
        st.plotly_chart(fig5, width="stretch")
        st.caption("r de Pearson entre totales anuales (numérica vs numérica). Verde: suben y bajan juntos; "
                   "naranja: sentido opuesto. Fila «Año» = tendencia. Correlación no implica causa.")
    else:
        st.warning("Para la correlación se necesitan al menos 2 cultivos y 4 años.")

# ---------------- Preguntas y preparación ----------------
with st.expander("Preguntas de investigación y dónde se responden"):
    st.markdown("""
1. **¿Ha crecido la producción total entre 2000 y 2022?** → KPI de crecimiento, KPI de tendencia (r) y gráfico anual.
2. **¿Qué cultivos y subregiones concentran más producción?** → KPI del cultivo líder, top 10 y gráfico de subregiones.
3. **¿Cambia el comportamiento según subregión o ciclo?** → filtros de subregión y ciclo con la métrica *mediana*.
4. **¿Qué municipios producen más? ¿Hay concentración?** → top 10 por municipio y KPI de concentración territorial.
5. **¿Qué cultivos ganaron o perdieron más producción?** → gráfico de crecimiento por cultivo y mapa de correlación.
""")
with st.expander("Preparación de datos (preparacion.py)"):
    st.write(log)
    st.markdown("""
- Producción convertida de texto (`2.124,4`) a número.
- **Faltantes:** 0 celdas vacías. Estrategia documentada: se eliminaría la fila, no se imputa (inventar toneladas cambia los totales).
- **Duplicados:** 39 filas idénticas eliminadas.
- **Ceros:** 202 registros se conservan (son reportes reales) y se anotan como limitación.
- **Cambio desde el Momento 1:** la limpieza pasó del notebook a un script reutilizable que el dashboard ejecuta al arrancar; se unificó la tilde de *Pacífico*.
""")
