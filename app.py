"""app.py — Gastos hormiga y costo de oportunidad (app de Streamlit).

Cada persona carga sus gastos (archivo o a mano) y la app calcula cuánto tendría hoy si ese dinero se hubiera
invertido en plazo fijo, FCI, dólar o bitcoin, y cuánto tendría en N meses si lo ahorrara de ahora en adelante.
Los datos de mercado se descargan en vivo (se guardan en caché unas horas).
"""
import os

import pandas as pd
import streamlit as st

import core
import graficos

st.set_page_config(page_title="Gastos hormiga", page_icon="🐜", layout="wide")
HOY = pd.Timestamp.today().normalize()
NOMBRES = {"plazo fijo": "Plazo fijo", "fci": "FCI de dinero", "dolar": "Dólar", "bitcoin": "Bitcoin"}


# ───────────────────────── utilidades ─────────────────────────
def clave_claude():
    """Clave de la API de Claude (opcional): secretos de Streamlit o variable de entorno."""
    try:
        v = st.secrets.get("ANTHROPIC_API_KEY")
        if v:
            return v
    except Exception:  # noqa: BLE001  (no hay archivo de secretos)
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


@st.cache_data(ttl=6 * 3600, show_spinner="Descargando datos de inflación, plazo fijo, FCI, dólar y bitcoin…")
def bajar(fci_fondo, dolar_casa, dolar_cripto, btc_desde, hoy):
    return core.descargar_series(fci_fondo, dolar_casa, dolar_cripto, btc_desde, hoy)


def gastos_vacios():
    return pd.DataFrame({"fecha": pd.Series(dtype="datetime64[ns]"), "descripcion": pd.Series(dtype="str"),
                         "monto": pd.Series(dtype="float")})


ss = st.session_state
ss.setdefault("gastos", gastos_vacios())
ss.setdefault("version", 0)            # cambia cuando se agregan gastos, para refrescar la tabla editable
ss.setdefault("archivos_vistos", set())
ss.setdefault("sugerencias", {})       # categorías sugeridas por la IA


# ───────────────────────── barra lateral ─────────────────────────
with st.sidebar:
    st.header("⚙️ Parámetros")
    umbral = st.number_input("Tope de un gasto hormiga ($)", min_value=500, value=10_000, step=500,
                             help="Si lo que pagaste supera este monto, no cuenta como hormiga.")
    alternativas = st.multiselect("Alternativas a explicar", options=list(core.OPCIONES), default=list(core.OPCIONES),
                                  format_func=lambda k: NOMBRES[k])
    frecuencia = st.radio("Ahorrarías por…", ["mensual", "semanal"], horizontal=True)
    horizonte = st.slider("¿A cuántos meses?", 1, 36, 6)
    recorte = st.slider("¿Qué parte de tu gasto hormiga ahorrarías?", 10, 100, 100, step=10, format="%d%%") / 100
    with st.expander("Avanzado"):
        dolar_casa = st.selectbox("Dólar para la alternativa «Dólar»", ["bolsa", "cripto", "oficial", "blue"],
                                  format_func=lambda c: {"bolsa": "MEP (bolsa)", "cripto": "Cripto (USDT)",
                                                         "oficial": "Oficial", "blue": "Blue"}[c])
        fci_fondo = st.text_input("Nombre del FCI", "mercado-fondo-clase-a")
        fijar_infl = st.checkbox("Fijar yo la inflación mensual de los meses sin dato oficial")
        infl_manual = st.number_input("Inflación mensual (%)", 0.0, 30.0, 2.0, 0.1, disabled=not fijar_infl) / 100
        ventana_comun = st.checkbox("Comparar todas las alternativas sobre el mismo período", True)
    st.divider()
    clave = clave_claude() or st.text_input("Clave de Claude (opcional)", type="password",
                                            help="Sin clave, la app funciona igual: el resumen se arma con una plantilla "
                                                 "y las categorías con palabras clave. No se guarda.")
    llm = core.crear_llm(clave)
    st.caption("🤖 IA activa (Claude)" if llm else "ℹ️ Sin IA: resumen por plantilla")
    if st.button("🔄 Actualizar datos de mercado"):
        st.cache_data.clear()
        st.rerun()

st.title("🐜 Gastos hormiga y costo de oportunidad")
st.caption("Cargá tus gastos y mirá cuánto tendrías hoy —y en los próximos meses— si ese dinero se hubiera invertido. "
           "Ejercicio ilustrativo con datos reales, no una recomendación de inversión.")
t1, t2, t3, t4 = st.tabs(["1️⃣ Mis gastos", "2️⃣ Resultados", "3️⃣ Proyección", "4️⃣ Resumen con IA"])


# ───────────────────────── 1. gastos ─────────────────────────
with t1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Subir un archivo")
        st.write("CSV o Excel con columnas **fecha**, **descripcion** y **monto** (por ejemplo, un extracto de tu billetera o banco).")
        archivo = st.file_uploader("Archivo de gastos", type=["csv", "xlsx", "xls"], label_visibility="collapsed")
        if archivo is not None:
            clave_arch = f"{archivo.name}-{archivo.size}"
            if clave_arch not in ss.archivos_vistos:
                try:
                    nuevos, avisos = core.leer_gastos(archivo.getvalue(), archivo.name, HOY)
                    ss.gastos = pd.concat([ss.gastos, nuevos], ignore_index=True).drop_duplicates()
                    ss.archivos_vistos.add(clave_arch)
                    ss.version += 1
                    for a in avisos:
                        st.warning(a)
                    st.success(f"✅ {len(nuevos)} gastos agregados.")
                except Exception as e:  # noqa: BLE001
                    st.error(f"No pude leer el archivo: {e}")
        st.download_button("⬇️ Descargar plantilla", "fecha,descripcion,monto\n".encode("utf-8"),
                           file_name="plantilla_gastos.csv", mime="text/csv")
    with c2:
        st.subheader("Cargar un gasto a mano")
        with st.form("rapida", clear_on_submit=True):
            f_fecha = st.date_input("Fecha", value=HOY.date(), max_value=HOY.date(), format="DD/MM/YYYY")
            f_desc = st.text_input("¿En qué lo gastaste?", placeholder="café, kiosco, SUBE…")
            f_monto = st.number_input("Monto ($)", min_value=0.0, step=500.0)
            if st.form_submit_button("Agregar"):
                if f_monto > 0 and f_desc.strip():
                    fila = pd.DataFrame({"fecha": [pd.Timestamp(f_fecha)], "descripcion": [f_desc.strip()], "monto": [float(f_monto)]})
                    ss.gastos = pd.concat([ss.gastos, fila], ignore_index=True)
                    ss.version += 1
                    st.rerun()
                else:
                    st.warning("Completá la descripción y un monto mayor a 0.")
    st.subheader("Tus gastos")
    st.caption("Podés editar, agregar o borrar filas. Los datos viven solo en esta sesión: descargalos para guardarlos.")
    editado = st.data_editor(
        ss.gastos, num_rows="dynamic", hide_index=True, key=f"editor_{ss.version}",
        column_config={"fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                       "descripcion": st.column_config.TextColumn("Descripción"),
                       "monto": st.column_config.NumberColumn("Monto ($)", min_value=0, format="$ %.0f")})
    ss.gastos = editado
    if len(ss.gastos):
        st.download_button("⬇️ Descargar mis gastos", ss.gastos.to_csv(index=False).encode("utf-8-sig"),
                           file_name="mis_gastos.csv", mime="text/csv")


# ───────────────────────── cálculo ─────────────────────────
res = p = m = None
error_proy = None
error = None
if len(ss.gastos) == 0:
    error = "Todavía no cargaste gastos. Subí un archivo o agregá uno a mano en la pestaña 1."
else:
    try:
        gastos, avisos_carga = core.limpiar_gastos(ss.gastos, HOY)
        primer = gastos["fecha"].min()
        series = bajar(fci_fondo, dolar_casa, "cripto", core.ventana_btc(primer, HOY), HOY)
        m = core.armar_mercado(series, primer, HOY, dolar_casa=dolar_casa,
                               inflacion_estimada=infl_manual if fijar_infl else None)
        res = core.analizar(gastos, m, umbral=umbral, ventana_comun=ventana_comun, sugerencias_ia=ss.sugerencias)
    except Exception as e:  # noqa: BLE001
        error = f"No pude calcular los resultados: {e}"
    if res is not None:
        try:
            tasas = core.tasas_vigentes(m)
            p = core.proyectar(res, m, tasas, alternativas, frecuencia=frecuencia, horizonte_meses=horizonte,
                               recorte=recorte, inflacion_proyectada=infl_manual if fijar_infl else None)
        except Exception as e:  # noqa: BLE001
            error_proy = f"No pude armar la proyección: {e}"
        else:
            error_proy = None
    else:
        error_proy = error


# ───────────────────────── 2. resultados ─────────────────────────
with t2:
    if res is None:
        st.info(error)
    else:
        for a in m.avisos + res.avisos:
            st.info(a)
        gasto_mensual = res.hormiga["monto_hoy"].sum() / (res.dias_obs / core.DIAS_MES)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Gastos hormiga", f"{len(res.hormiga)} de {len(res.gastos)}")
        k2.metric("Total (pesos de hoy)", core.ars(res.hormiga["monto_hoy"].sum()))
        k3.metric("Promedio por mes", core.ars(gasto_mensual))
        k4.metric("Promedio por semana", core.ars(gasto_mensual * 12 / 52))
        if res.dias_obs < 28:
            st.warning(f"Tenés solo {res.dias_obs} días de gastos cargados: los promedios son una estimación gruesa. "
                       "Cuanto más historia cargues, más confiable.")
        g1, g2 = st.columns(2)
        with g1:
            fig = graficos.fig_mensual(res)
            st.pyplot(fig)
            graficos.plt.close(fig)
        with g2:
            fig = graficos.fig_categorias(res)
            st.pyplot(fig)
            graficos.plt.close(fig)
            st.dataframe(core.vista_categorias(res))

        st.subheader("¿Cuánto tendrías hoy si lo hubieras invertido?")
        fig = graficos.fig_valor_hoy(res)
        st.pyplot(fig)
        graficos.plt.close(fig)
        con = core.conclusion_historica(res)
        st.success(f"💡 Con los gastos hormiga analizados ({core.ars(con['aportado'])}), la inversión con mejor resultado fue "
                   f"**{con['mejor']}**: hoy tendrías {core.ars(con['valor_hoy_mejor'])} "
                   f"(costo de oportunidad nominal: {core.ars(con['costo_mejor'])}).")
        if con["rr"] >= 0:
            st.write(f"Le ganó a la inflación: rendimiento real de {core.pct(con['rr'], 2)} "
                     f"(para mantener el poder adquisitivo alcanzaban {core.ars(con['ref_mejor'])}).")
        else:
            st.write(f"Ninguna inversión le ganó a la inflación en este período: la mejor perdió {core.pct(-con['rr'], 2)} de poder adquisitivo.")
        st.write(f"Tenerlos en efectivo hizo perder {core.pct(con['perdida_efectivo'], 2)} de poder adquisitivo.")
        if con["mejor_monto"] != con["mejor"]:
            st.caption(f"Ojo: por monto total hoy tendrías más en «{con['mejor_monto']}», pero cubre distinta cantidad de gastos: "
                       "por eso el ranking se hace por rendimiento.")
        st.dataframe(core.vista_costo(res))

        sin = res.sin_clasificar
        if len(sin):
            with st.expander(f"🏷️ {len(sin)} descripciones sin clasificar"):
                st.write("No coinciden con ninguna categoría hormiga, así que no cuentan. Si alguna sí es hormiga, "
                         "podés pedirle a la IA que las clasifique (solo se envían las descripciones, sin montos ni fechas).")
                st.dataframe(sin.rename("veces"))
                if llm is not None and st.button("🤖 Clasificar con IA"):
                    sug = core.clasificar_con_ia(list(sin.index), list(core.REGLAS), llm)
                    if sug:
                        ss.sugerencias.update(sug)
                        st.rerun()
                    else:
                        st.warning("La IA no devolvió categorías válidas" + (f" ({llm.ultimo_error})." if llm.ultimo_error else "."))
        if ss.sugerencias:
            with st.expander("🤖 Categorías sugeridas por la IA (revisalas)"):
                st.dataframe(pd.Series(ss.sugerencias, name="categoría").rename_axis("descripción"))
                if st.button("Descartar sugerencias"):
                    ss.sugerencias = {}
                    st.rerun()
        with st.expander("📅 Fuentes y cobertura de datos"):
            st.markdown(
                "| Alternativa | Dato que usa | Fuente |\n|---|---|---|\n"
                "| Plazo fijo | TNA de depósitos a 30 días (promedio del sistema) | BCRA, vía ArgentinaDatos |\n"
                "| FCI de dinero | Valor de la cuotaparte diaria del fondo elegido | CNV, vía ArgentinaDatos |\n"
                "| Dólar | Precio medio (compra y venta) del dólar elegido | ArgentinaDatos |\n"
                "| Bitcoin | Cierre diario de BTC-USD por el dólar cripto | Yahoo Finance y ArgentinaDatos |\n"
                "| Inflación (referencia) | Inflación mensual nacional | INDEC, vía ArgentinaDatos |")
            st.dataframe(core.cobertura(m))
            st.caption(f"Datos descargados el {series['descargado']:%d/%m/%Y %H:%M} (se actualizan solos cada 6 horas o con el botón de la barra lateral).")


# ───────────────────────── 3. proyección ─────────────────────────
with t3:
    if res is None:
        st.info(error)
    elif p is None:
        st.warning(error_proy)
    else:
        st.write(f"Ahorrando **{core.ars(p.aporte_per)} por {p.periodo_txt}** durante **{p.horizonte_meses} meses** "
                 f"({p.n_per} aportes). Inflación supuesta: {core.pct(p.pi_m, 2)} por mes.")
        st.info(f"**Para ganarle a la inflación** necesitás llegar a **{core.ars(p.necesario_final)}** en {p.horizonte_meses} meses: "
                f"es lo que valen tus aportes si se hubieran movido con los precios. Equivale a rendir al menos "
                f"{core.pct(p.r30_empate, 2)} por 30 días (una tasa nominal anual de {core.pct(p.tna_empate, 1)} o más).")
        cols = st.columns(len(p.elegidas))
        for col, n in zip(cols, p.elegidas):
            f = p.proy.loc[n]
            dif = f["Valor final"] - p.necesario_final
            col.metric(n, core.ars(f["Valor final"]), f"{core.ars(dif)} vs. el mínimo" if dif >= 0 else f"{core.ars(dif)} vs. el mínimo")
            col.caption(("✅ Le gana a la inflación" if dif >= 0 else "⚠️ No alcanza a la inflación") +
                        f" · ganancia real {core.ars(f['Ganancia real'])}")
        st.dataframe(core.vista_proyeccion(p))
        if core.N_USD in p.elegidas or core.N_BTC in p.elegidas:
            st.caption("Dólar y bitcoin se proyectan suponiendo que se repite el promedio del último año: "
                       "es un ejercicio, no una predicción.")
        with st.expander("¿Qué significa «ganarle a la inflación»?"):
            st.write("Que tu plata termine valiendo más que tus aportes de hoy, medidos en pesos de hoy. "
                     "El valor final mínimo para empatar es lo aportado en pesos de hoy, llevado al final con la inflación:")
            st.latex(r"\text{mínimo}=\left(\sum_{k=0}^{n-1}\dfrac{c}{(1+\pi)^{k\,d/30{,}4375}}\right)\cdot(1+\pi)^{N}")
            st.write("Equivale a rendir, por cada 30 días, al menos "
                     "$r_{30}=(1+\\pi)^{30/30{,}4375}-1$, o una tasa nominal anual de $r_{30}\\cdot 365/30$.")


# ───────────────────────── 4. resumen con IA ─────────────────────────
with t4:
    if res is None:
        st.info(error)
    elif p is None:
        st.warning(error_proy)
    else:
        d = core.datos_resumen(res, p)
        if st.button("✨ Explicar mis resultados"):
            ss.resumen = core.responder(core.prompt_resumen(d), d, llm)
            ss.resumen_ia_error = getattr(llm, "ultimo_error", None) if llm else None
        if "resumen" in ss:
            texto, usada, extra = ss.resumen
            st.markdown(f"**{'🤖 Generado por IA' if usada else '📝 Armado con una plantilla (sin IA)'}**")
            st.write(texto)
            if extra:
                st.warning(f"La IA mencionó cifras que no están en tus datos ({', '.join(extra)}): revisalas antes de usarlas.")
            if not usada and ss.get("resumen_ia_error"):
                st.caption(f"La IA no respondió ({ss.resumen_ia_error}); se usó la plantilla.")
        st.divider()
        pregunta = st.text_input("Preguntale a la IA sobre tus resultados", placeholder="¿Qué categoría pesa más y por qué importa?",
                                 disabled=llm is None)
        if llm is None:
            st.caption("Para hacer preguntas hace falta una clave de Claude (barra lateral).")
        elif st.button("Preguntar") and pregunta.strip():
            texto, usada, extra = core.responder(core.prompt_pregunta(d, pregunta), d, llm)
            st.write(texto if usada else "La IA no respondió. Probá de nuevo en un rato.")
            if extra:
                st.warning(f"La IA mencionó cifras que no están en tus datos ({', '.join(extra)}).")
