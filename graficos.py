"""graficos.py — gráficos de Gastos Hormiga."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from core import INVERSIONES, N_EF, N_IPC, N_PF, N_FCI, N_USD, N_BTC, ars, conclusion_historica, por_categoria


# ───────────── PALETA VERDE ─────────────

VERDE_OSCURO = "#365D48"
VERDE = "#668875"
VERDE_MEDIO = "#8EAD91"
VERDE_CLARO = "#B9D0BA"
VERDE_PASTEL = "#DCEBDD"
FONDO = "#FFFFFF"
GRIS = "#A5A5A0"
ROSA = "#D991A0"

COLORES = {
    N_EF: GRIS,
    N_IPC: "#B9D0BA",
    N_PF: "#477B61",
    N_FCI: "#668875",
    N_USD: "#8EAD91",
    N_BTC: "#365D48"
}

MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun",
            "jul", "ago", "sep", "oct", "nov", "dic"]

fmt_ars = FuncFormatter(lambda v, _: ars(v))


# ───────────── ESTILO GENERAL ─────────────

def _estilo(fig, ax):
    fig.patch.set_facecolor("#FFF9F8")
    ax.set_facecolor(FONDO)

    ax.tick_params(axis="both", labelsize=11, colors=VERDE_OSCURO)

    ax.title.set_color(VERDE_OSCURO)
    ax.title.set_fontsize(15)
    ax.title.set_fontweight("bold")

    ax.grid(color="#E8EEE8", linewidth=0.9, alpha=0.9)
    ax.set_axisbelow(True)

    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)

    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#DCE7DC")

    ax.xaxis.label.set_color(VERDE_OSCURO)
    ax.yaxis.label.set_color(VERDE_OSCURO)


# ───────────── AGRUPACIÓN MENSUAL ─────────────

def _agrupar_mensual(df):
    p = df["fecha"].dt.to_period("M")
    g = df.groupby(p).agg(total=("monto_hoy", "sum"), gastos=("monto", "size"))
    g = g.reindex(pd.period_range(p.min(), p.max(), freq="M"), fill_value=0)
    g.index = g.index.to_timestamp()
    return g


# ───────────── GASTOS POR MES ─────────────

def fig_mensual(res):
    mens = _agrupar_mensual(res.hormiga)

    def cobertura(d):
        fin_mes = (d + pd.offsets.MonthEnd(0)).normalize()
        dias_cub = (min(res.fin_obs, fin_mes) - max(res.inicio_obs, d)).days + 1
        return max(dias_cub, 0) / d.days_in_month

    incompleto = [cobertura(d) < 0.9 for d in mens.index]

    etiquetas = [
        f"{MESES_ES[d.month - 1]} {d.year}" + ("*" if inc else "")
        for d, inc in zip(mens.index, incompleto)
    ]

    x = np.arange(len(mens))
    rotar = len(mens) > 8

    fig, ax = plt.subplots(
        figsize=(min(12, max(6.5, 1.1 * len(mens) + 3)), 5)
    )

    barras = ax.bar(
        x, mens["total"],
        width=0.62,
        color=VERDE,
        edgecolor=VERDE_OSCURO,
        linewidth=0.5,
        zorder=3
    )

    paso = max(1, int(np.ceil(len(mens) / 12)))
    ax.set_xticks(x[::paso])
    ax.set_xticklabels(
        etiquetas[::paso],
        rotation=45 if rotar else 0,
        ha="right" if rotar else "center"
    )

    if len(mens) <= 12:
        for b, v in zip(barras, mens["total"]):
            ax.annotate(
                ars(v),
                (b.get_x() + b.get_width() / 2, v),
                ha="center",
                va="bottom",
                xytext=(0, 5),
                textcoords="offset points",
                fontsize=10,
                color=VERDE_OSCURO,
                fontweight="bold"
            )

    ax.set_ylim(0, max(mens["total"].max(), 1) * 1.18)
    ax.yaxis.set_major_formatter(fmt_ars)

    ax.set_title(
        "Gastos hormiga por mes\n"
        "(pesos del " + res.corte.strftime("%d/%m/%Y") + ")",
        pad=18
    )

    if any(incompleto):
        ax.set_xlabel(
            f"* Mes incompleto: gastos cargados del "
            f"{res.inicio_obs:%d/%m/%Y} al {res.fin_obs:%d/%m/%Y}",
            fontsize=9,
            color=VERDE_OSCURO
        )

    _estilo(fig, ax)
    fig.tight_layout()
    return fig


# ───────────── GASTOS POR CATEGORÍA ─────────────

def fig_categorias(res):
    pc = por_categoria(res)

    fig, ax = plt.subplots(
        figsize=(8.5, max(4.5, 0.65 * len(pc) + 1.5))
    )

    tonos = [
        VERDE_OSCURO,
        VERDE,
        VERDE_MEDIO,
        "#A9C4AA",
        "#C5D9C5",
        "#DCEBDD"
    ]

    colores_barras = [
        tonos[i % len(tonos)]
        for i in range(len(pc))
    ][::-1]

    barras = ax.barh(
        pc.index[::-1],
        pc["total_hoy"][::-1],
        color=colores_barras,
        height=0.62,
        edgecolor="white",
        linewidth=1
    )

    for b, v in zip(barras, pc["total_hoy"][::-1]):
        ax.annotate(
            ars(v),
            (v, b.get_y() + b.get_height() / 2),
            va="center",
            ha="left",
            xytext=(7, 0),
            textcoords="offset points",
            fontsize=11,
            color=VERDE_OSCURO,
            fontweight="bold"
        )

    ax.set_xlim(0, max(pc["total_hoy"].max(), 1) * 1.25)
    ax.xaxis.set_major_formatter(fmt_ars)

    ax.set_title(
        "¿En qué se van tus gastos hormiga?",
        pad=18
    )

    _estilo(fig, ax)
    fig.tight_layout()
    return fig


# ───────────── COMPARACIÓN DE INVERSIONES ─────────────

def fig_valor_hoy(res):
    t = res.tabla
    con = conclusion_historica(res)

    orden = (
        t.loc[[N_EF] + INVERSIONES, "Valor hoy"]
        .dropna()
        .sort_values()
    )

    fig, ax = plt.subplots(figsize=(10, 5.8))

    barras = ax.barh(
        orden.index,
        orden.values,
        color=[COLORES[n] for n in orden.index],
        height=0.65,
        edgecolor="white",
        linewidth=1.2
    )

    for b, v in zip(barras, orden.values):
        ax.annotate(
            ars(v),
            (v, b.get_y() + b.get_height() / 2),
            va="center",
            ha="right",
            xytext=(-8, 0),
            textcoords="offset points",
            fontsize=11,
            color="white",
            fontweight="bold"
        )

    ax.axvline(
        con["aportado"],
        color=VERDE_OSCURO,
        linestyle="--",
        linewidth=1.8,
        label=f"Lo que gastaste: {ars(con['aportado'])}"
    )

    ax.axvline(
        con["referencia"],
        color=ROSA,
        linestyle=":",
        linewidth=2.2,
        label=f"Para mantener el poder adquisitivo: {ars(con['referencia'])}"
    )

    ax.set_xlim(
        0,
        max(orden.max(), con["referencia"], con["aportado"]) * 1.12
    )

    ax.xaxis.set_major_formatter(fmt_ars)

    ax.set_title(
        "¿Cuánto tendrías hoy si hubieras invertido?",
        pad=18
    )

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.13),
        fontsize=10,
        frameon=False,
        labelcolor=VERDE_OSCURO
    )

    _estilo(fig, ax)
    fig.tight_layout()
    return fig
