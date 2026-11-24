"""graficos.py — gráficos de la app (los mismos del notebook, devueltos como figuras de matplotlib)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from core import INVERSIONES, N_EF, N_IPC, N_PF, N_FCI, N_USD, N_BTC, ars, conclusion_historica, por_categoria

COLORES = {N_EF: "#999999", N_IPC: "#7A4FD6", N_PF: "#2E9E5B", N_FCI: "#1F8FBF", N_USD: "#E8A33A", N_BTC: "#E8583A"}
MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
fmt_ars = FuncFormatter(lambda v, _: ars(v))


def _agrupar_mensual(df):
    p = df["fecha"].dt.to_period("M")
    g = df.groupby(p).agg(total=("monto_hoy", "sum"), gastos=("monto", "size"))
    g = g.reindex(pd.period_range(p.min(), p.max(), freq="M"), fill_value=0)     # meses sin gasto = 0
    g.index = g.index.to_timestamp()
    return g


def fig_mensual(res):
    mens = _agrupar_mensual(res.hormiga)

    def cobertura(d):
        fin_mes = (d + pd.offsets.MonthEnd(0)).normalize()
        dias_cub = (min(res.fin_obs, fin_mes) - max(res.inicio_obs, d)).days + 1
        return max(dias_cub, 0) / d.days_in_month

    incompleto = [cobertura(d) < 0.9 for d in mens.index]       # se marca si falta más del 10 % del mes
    etiquetas = [f"{MESES_ES[d.month - 1]} {d.year}" + ("*" if inc else "") for d, inc in zip(mens.index, incompleto)]
    x = np.arange(len(mens))
    rotar = len(mens) > 8
    fig, ax = plt.subplots(figsize=(min(12, max(6.5, 1.1 * len(mens) + 3)), 4.5))
    barras = ax.bar(x, mens["total"], width=0.6, color="#E8833A")
    paso = max(1, int(np.ceil(len(mens) / 12)))
    ax.set_xticks(x[::paso])
    ax.set_xticklabels(etiquetas[::paso], rotation=45 if rotar else 0, ha="right" if rotar else "center")
    if len(mens) <= 12:
        for b, v in zip(barras, mens["total"]):
            ax.annotate(ars(v), (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom",
                        xytext=(0, 3), textcoords="offset points", fontsize=9)
    ax.set_ylim(0, max(mens["total"].max(), 1) * 1.15)
    ax.yaxis.set_major_formatter(fmt_ars)
    ax.set_title("Gasto hormiga por mes (pesos del " + res.corte.strftime("%d/%m/%Y") + ")")
    if any(incompleto):
        ax.set_xlabel(f"* mes incompleto: hay gastos cargados solo del {res.inicio_obs:%d/%m/%Y} al {res.fin_obs:%d/%m/%Y}",
                      fontsize=8, color="#555555")
    ax.grid(axis="y", alpha=.3)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    fig.tight_layout()
    return fig


def fig_categorias(res):
    pc = por_categoria(res)
    fig, ax = plt.subplots(figsize=(8, 0.6 * len(pc) + 1.5))
    barras = ax.barh(pc.index[::-1], pc["total_hoy"][::-1], color="#E8833A")
    for b, v in zip(barras, pc["total_hoy"][::-1]):
        ax.annotate(ars(v), (v, b.get_y() + b.get_height() / 2), va="center", ha="left",
                    xytext=(4, 0), textcoords="offset points", fontsize=9)
    ax.set_xlim(0, pc["total_hoy"].max() * 1.2)
    ax.xaxis.set_major_formatter(fmt_ars)
    ax.set_title("¿En qué se van los gastos hormiga? (pesos del " + res.corte.strftime("%d/%m/%Y") + ")")
    ax.grid(axis="x", alpha=.3)
    fig.tight_layout()
    return fig


def fig_valor_hoy(res):
    t = res.tabla
    con = conclusion_historica(res)
    orden = t.loc[[N_EF] + INVERSIONES, "Valor hoy"].dropna().sort_values()
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    barras = ax.barh(orden.index, orden.values, color=[COLORES[n] for n in orden.index])
    for b, v in zip(barras, orden.values):
        ax.annotate(ars(v), (v, b.get_y() + b.get_height() / 2), va="center", ha="right",
                    xytext=(-8, 0), textcoords="offset points", fontsize=10, color="white", fontweight="bold")
    ax.axvline(con["aportado"], color="black", ls="--", lw=1, label=f"Lo que gastaste: {ars(con['aportado'])}")
    ax.axvline(con["referencia"], color=COLORES[N_IPC], ls=":", lw=2,
               label=f"Para mantener el poder adquisitivo: {ars(con['referencia'])}")
    ax.set_xlim(0, max(orden.max(), con["referencia"], con["aportado"]) * 1.08)
    ax.xaxis.set_major_formatter(fmt_ars)
    ax.set_title("¿Cuánto tendrías hoy si ese gasto hormiga se hubiera invertido?")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), fontsize=9, frameon=False)
    ax.grid(axis="x", alpha=.3)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig
