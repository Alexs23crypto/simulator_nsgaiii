#==============================GRAPHIC MUNICIPALITY VS NSGA-III=======================

#1. RISK MAP

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe

# =========================
# USER PARAMETERS
# =========================
SHAPEFILE_MANZANAS_PATH = "/content/drive/Shareddrives/Tesis Final /Códigos/Soledad[AppliedScience]/manzanas_caracterizadas_lima.shp"
SHAPEFILE_PATH = "/content/drive/Shareddrives/Tesis Final /Códigos/Soledad[AppliedScience]/peru_shapes/per_admbnda_adm3_ign_20200714.shp"
TARGET_CRS = "EPSG:32718"
OUTPUT_PREFIX = "figure_block_risk_lima"

SHOW_DISTRICT_LABELS = True

# =========================
# HELPERS
# =========================
def km_formatter(x, pos):
    return f"{x/1000:.0f}"

def add_north_arrow(ax):
    ax.annotate(
        "N",
        xy=(0.94, 0.90),
        xytext=(0.94, 0.80),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="black",
        arrowprops=dict(
            facecolor="black",
            edgecolor="black",
            width=2,
            headwidth=10
        )
    )

def add_scale_bar(ax, length_km=10):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()

    bar_length = length_km * 1000
    x_start = x0 + 0.06 * (x1 - x0)
    y_start = y0 + 0.05 * (y1 - y0)
    tick_h = 0.008 * (y1 - y0)

    ax.plot([x_start, x_start + bar_length], [y_start, y_start],
            color="black", lw=2.0, zorder=10)
    ax.plot([x_start, x_start], [y_start - tick_h, y_start + tick_h],
            color="black", lw=2.0, zorder=10)
    ax.plot([x_start + bar_length, x_start + bar_length],
            [y_start - tick_h, y_start + tick_h],
            color="black", lw=2.0, zorder=10)

    ax.text(
        x_start + bar_length / 2,
        y_start + 1.5 * tick_h,
        f"{length_km} km",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#333333"
    )

def style_axes(ax, bounds):
    xmin, ymin, xmax, ymax = bounds
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")

    ax.grid(True, linestyle="--", linewidth=0.30, color="#DADADA", alpha=0.55)
    ax.xaxis.set_major_formatter(FuncFormatter(km_formatter))
    ax.yaxis.set_major_formatter(FuncFormatter(km_formatter))

    ax.set_xlabel("UTM Easting (km) — EPSG:32718", fontsize=10, color="#666666")
    ax.set_ylabel("UTM Northing (km) — EPSG:32718", fontsize=10, color="#666666")
    ax.tick_params(axis="both", colors="#666666", labelsize=9.5)

    for spine in ax.spines.values():
        spine.set_linewidth(0.55)
        spine.set_color("#A8A8A8")


def add_district_labels(ax, districts_gdf, fontsize=5.2, color="#666666", alpha=0.85):
    for _, row in districts_gdf.iterrows():
        if pd.notna(row["ADM3_ES"]):
            pt = row["GEOMETRY"].representative_point()  # ← GEOMETRY en mayúsculas
            txt = ax.text(
                pt.x,
                pt.y,
                str(row["ADM3_ES"]),
                fontsize=fontsize,
                color=color,
                alpha=alpha,
                ha="center",
                va="center",
                zorder=6
            )
            txt.set_path_effects([
                pe.withStroke(linewidth=1.2, foreground="white", alpha=0.9)
            ])

# =========================
# CATEGORY MAPPING (ES → EN)
# =========================
VULN_ES_TO_EN = {
    "SIN RIESGO": "None",
    "BAJO":      "Low",
    "MEDIO":     "Medium",
    "ALTO":      "High",
    "MUY ALTO":  "Very High",
}

VULN_ORDER = ["None", "Low", "Medium", "High", "Very High"]

# COLORS = {
#     "None":      None,         # sin color → no se plotea
#     "Low":       "#2ECC71",    # verde
#     "Medium":    "#F4D03F",    # amarillo
#     "High":      "#E67E22",    # naranja
#     "Very High": "#E74C3C",    # rojo
# }

COLORS = {
    "None":      None,
    "Low":       "#FDEBD0",
    "Medium":    "#F5CBA7",
    "High":      "#EB984E",
    "Very High": "#CB4335",
}

# COLORS = {
#     "None":      None,
#     "Low":       "#E3F2FD",
#     "Medium":    "#90CAF9",
#     "High":      "#2196F3",
#     "Very High": "#0D47A1",
# }

# =========================
# LOAD MANZANAS SHAPEFILE
# =========================
manzanas = gpd.read_file(SHAPEFILE_MANZANAS_PATH)
manzanas.columns = [c.strip() for c in manzanas.columns]  # preserve original case

# Identify the vulnerability column (case-insensitive search)
vuln_col = next(
    (c for c in manzanas.columns if c.upper() == "NIV_RIESGO"), None
)
if vuln_col is None:
    raise ValueError("Column 'NIV_RIESGO' not found in manzanas shapefile.")

# Translate categories to English
manzanas["VULN_EN"] = (
    manzanas[vuln_col]
    .astype(str)
    .str.strip()
    .str.upper()
    .map(VULN_ES_TO_EN)
)

unmapped = manzanas["VULN_EN"].isna().sum()
if unmapped > 0:
    unique_vals = manzanas[vuln_col].unique()
    print(f"Warning: {unmapped} rows could not be mapped. Unique values: {unique_vals}")

manzanas["COLOR"] = manzanas["VULN_EN"].map(COLORS)

# Reproject
if manzanas.crs is None:
    manzanas = manzanas.set_crs("EPSG:4326")
manzanas = manzanas.to_crs(TARGET_CRS)

# =========================
# LOAD DISTRICTS SHAPEFILE
# =========================
districts = gpd.read_file(SHAPEFILE_PATH)
districts.columns = [c.strip().upper() for c in districts.columns]

if "ADM2_ES" not in districts.columns or "ADM3_ES" not in districts.columns:
    raise ValueError("Shapefile must contain columns ADM2_ES and ADM3_ES.")

districts = districts.set_geometry("GEOMETRY")

districts = districts[
    districts["ADM2_ES"].astype(str).str.upper() == "LIMA"
].copy()

districts = districts.to_crs(TARGET_CRS)

# =========================
# MAP BOUNDS
# =========================
xmin, ymin, xmax, ymax = districts.total_bounds
pad_x = (xmax - xmin) * 0.03
pad_y = (ymax - ymin) * 0.03
map_bounds = (xmin - pad_x, ymin - pad_y, xmax + pad_x, ymax + pad_y)

# =========================
# PLOT STYLE
# =========================
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "savefig.facecolor": "white",
    "font.size":        10,
    "axes.titlesize":   11,
    "axes.labelsize":   10,
    "font.family":      "sans-serif"
})

# =========================
# PLOT
# =========================
fig, ax = plt.subplots(1, 1, figsize=(8.8, 8.8), dpi=300)
fig.patch.set_facecolor("white")

# District boundaries (background + borders)
districts.plot(
    ax=ax,
    color="#F8F9F9",   # very light grey base
    edgecolor="#7F7F7F",
    linewidth=0.6,
    zorder=1
)

# Manzanas coloured by vulnerability (draw all at once per category for speed)
for cat in VULN_ORDER:
    if COLORS[cat] is None:    # ← saltar manzanas sin vulnerabilidad
        continue
    subset = manzanas[manzanas["VULN_EN"] == cat]
    if len(subset) == 0:
        continue
    subset.plot(
        ax=ax,
        color=COLORS[cat],
        edgecolor="none",   # no block outlines — too dense at city scale
        linewidth=0,
        alpha=0.85,
        zorder=2
    )

# District borders on top for readability
districts.boundary.plot(
    ax=ax,
    edgecolor="#555555",
    linewidth=0.7,
    zorder=3
)

style_axes(ax, map_bounds)

if SHOW_DISTRICT_LABELS:
    add_district_labels(ax, districts, fontsize=5.2, color="#333333", alpha=0.90)

add_north_arrow(ax)
add_scale_bar(ax, length_km=10)

ax.set_title(
    "Block-Level Seismic Risk in Lima",
    fontsize=11,
    fontweight="normal",
    color="#6A6A6A",
    pad=7
)

# =========================
# LEGEND
# =========================
legend_handles = [
    Line2D([0], [0], marker='s', color='w', label=cat,
           markerfacecolor=COLORS[cat], markersize=10,
           markeredgecolor="#AAAAAA", markeredgewidth=0.4)
    for cat in VULN_ORDER
    if COLORS[cat] is not None
]

legend = ax.legend(
    handles=legend_handles,
    title="Seismic Risk",
    loc="lower left",
    bbox_to_anchor=(1.02, 0.02),
    borderaxespad=0.0,
    frameon=True,
    framealpha=0.95,
    fontsize=8,
    title_fontsize=8.5
)
legend.get_frame().set_edgecolor("#B0B0B0")
legend.get_frame().set_linewidth(0.6)

plt.subplots_adjust(left=0.08, right=0.82, top=0.93, bottom=0.10)

plt.savefig(f"{OUTPUT_PREFIX}.png", dpi=300, bbox_inches="tight", facecolor="white")
plt.savefig(f"{OUTPUT_PREFIX}.pdf", dpi=300, bbox_inches="tight", facecolor="white")
plt.show()


#2. RISK BACKGROUND - DISASTROUS NSGA-III

import warnings
warnings.filterwarnings("ignore")

import ast
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe

# =========================
# USER PARAMETERS
# =========================
SHAPEFILE_MANZANAS_PATH = "/content/drive/Shareddrives/Tesis Final /Códigos/Soledad[AppliedScience]/manzanas_caracterizadas_lima.shp"
SHAPEFILE_PATH          = "/content/drive/Shareddrives/Tesis Final /Códigos/Soledad[AppliedScience]/peru_shapes/per_admbnda_adm3_ign_20200714.shp"
SHELTERS_EXCEL_PATH     = "/content/drive/Shareddrives/Tesis Final /Códigos/Soledad[AppliedScience]/shelters_lima.xlsx"
PARETO_CSV_PATH         = "/content/drive/Shareddrives/Tesis Final /Códigos/Soledad[AppliedScience]/Codigo[31-03-2026]/pareto_front_disastrous.csv"
TARGET_CRS              = "EPSG:32718"
OUTPUT_PREFIX           = "figure_block_risk_shelters_lima"
SHOW_DISTRICT_LABELS    = True

# Índice de la solución del frente de Pareto a visualizar (0 = primera solución)
PARETO_SOLUTION_IDX = 16

# =========================
# CATEGORY MAPPING (ES → EN)
# =========================
VULN_ES_TO_EN = {
    "SIN RIESGO": "None",
    "BAJO":       "Low",
    "MEDIO":      "Medium",
    "ALTO":       "High",
    "MUY ALTO":   "Very High",
}

VULN_ORDER = ["None", "Low", "Medium", "High", "Very High"]

COLORS = {
    "None":      None,
    "Low":       "#FDEBD0",
    "Medium":    "#F5CBA7",
    "High":      "#EB984E",
    "Very High": "#CB4335",
}

# =========================
# HELPERS
# =========================
def km_formatter(x, pos):
    return f"{x/1000:.0f}"

def add_north_arrow(ax):
    ax.annotate(
        "N",
        xy=(0.94, 0.90), xytext=(0.94, 0.80),
        xycoords="axes fraction", textcoords="axes fraction",
        ha="center", va="center", fontsize=12, fontweight="bold", color="black",
        arrowprops=dict(facecolor="black", edgecolor="black", width=2, headwidth=10)
    )

def add_scale_bar(ax, length_km=10):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    bar_length = length_km * 1000
    x_start = x0 + 0.06 * (x1 - x0)
    y_start = y0 + 0.05 * (y1 - y0)
    tick_h   = 0.008 * (y1 - y0)
    ax.plot([x_start, x_start + bar_length], [y_start, y_start],
            color="black", lw=2.0, zorder=10)
    ax.plot([x_start, x_start], [y_start - tick_h, y_start + tick_h],
            color="black", lw=2.0, zorder=10)
    ax.plot([x_start + bar_length]*2, [y_start - tick_h, y_start + tick_h],
            color="black", lw=2.0, zorder=10)
    ax.text(x_start + bar_length / 2, y_start + 1.5 * tick_h,
            f"{length_km} km", ha="center", va="bottom", fontsize=9, color="#333333")

def style_axes(ax, bounds):
    xmin, ymin, xmax, ymax = bounds
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal")
    ax.grid(True, linestyle="--", linewidth=0.30, color="#DADADA", alpha=0.55)
    ax.xaxis.set_major_formatter(FuncFormatter(km_formatter))
    ax.yaxis.set_major_formatter(FuncFormatter(km_formatter))
    ax.set_xlabel("UTM Easting (km) — EPSG:32718", fontsize=10, color="#666666")
    ax.set_ylabel("UTM Northing (km) — EPSG:32718", fontsize=10, color="#666666")
    ax.tick_params(axis="both", colors="#666666", labelsize=9.5)
    for spine in ax.spines.values():
        spine.set_linewidth(0.55); spine.set_color("#A8A8A8")

def add_district_labels(ax, districts_gdf, fontsize=5.2, color="#666666", alpha=0.85):
    for _, row in districts_gdf.iterrows():
        if pd.notna(row["ADM3_ES"]):
            pt = row["GEOMETRY"].representative_point()
            txt = ax.text(
                pt.x, pt.y, str(row["ADM3_ES"]),
                fontsize=fontsize, color=color, alpha=alpha,
                ha="center", va="center", zorder=6
            )
            txt.set_path_effects([
                pe.withStroke(linewidth=1.2, foreground="white", alpha=0.9)
            ])

# =========================
# LOAD MANZANAS SHAPEFILE
# =========================
manzanas = gpd.read_file(SHAPEFILE_MANZANAS_PATH)
manzanas.columns = [c.strip() for c in manzanas.columns]

vuln_col = next((c for c in manzanas.columns if c.upper() == "NIV_RIESGO"), None)
if vuln_col is None:
    raise ValueError("Column 'NIV_RIESGO' not found in manzanas shapefile.")

manzanas["VULN_EN"] = (
    manzanas[vuln_col]
    .astype(str).str.strip().str.upper()
    .map(VULN_ES_TO_EN)
)

unmapped = manzanas["VULN_EN"].isna().sum()
if unmapped > 0:
    print(f"Warning: {unmapped} rows could not be mapped. "
          f"Unique values: {manzanas[vuln_col].unique()}")

if manzanas.crs is None:
    manzanas = manzanas.set_crs("EPSG:4326")
manzanas = manzanas.to_crs(TARGET_CRS)

# =========================
# LOAD SHELTERS (candidatos)
# =========================
xls      = pd.ExcelFile(SHELTERS_EXCEL_PATH)
sheet    = "Shelters" if "Shelters" in xls.sheet_names else xls.sheet_names[0]
df_shelters = pd.read_excel(SHELTERS_EXCEL_PATH, sheet_name=sheet)
df_shelters.columns = df_shelters.columns.str.strip().str.upper()

required = ["ID_ALBERGUE", "LATITUD", "LONGITUD"]
missing  = [c for c in required if c not in df_shelters.columns]
if missing:
    raise ValueError(f"Missing columns in Excel: {missing}")

df_shelters = df_shelters[required].dropna().copy()
df_shelters["ID_ALBERGUE"] = df_shelters["ID_ALBERGUE"].astype(int)
df_shelters = df_shelters.set_index("ID_ALBERGUE")

gdf_candidates = gpd.GeoDataFrame(
    df_shelters,
    geometry=gpd.points_from_xy(df_shelters["LONGITUD"], df_shelters["LATITUD"]),
    crs="EPSG:4326"
).to_crs(TARGET_CRS)

# =========================
# LOAD PARETO FRONT → seleccionar solución
# =========================
df_pareto = pd.read_csv(PARETO_CSV_PATH)
df_pareto.columns = df_pareto.columns.str.strip()

if PARETO_SOLUTION_IDX >= len(df_pareto):
    raise ValueError(
        f"PARETO_SOLUTION_IDX={PARETO_SOLUTION_IDX} out of range "
        f"({len(df_pareto)} solutions available)."
    )

solution    = df_pareto.iloc[PARETO_SOLUTION_IDX]
shelter_ids = ast.literal_eval(solution["Shelter_Indices"])
print(f"Solution {PARETO_SOLUTION_IDX}: "
      f"Distance={solution['Distance']:.4f}, "
      f"Population={solution['Population']:.4f}, "
      f"Safety={solution['Safety']:.4f}, "
      f"Shelters selected={len(shelter_ids)}")

gdf_selected = gdf_candidates.loc[gdf_candidates.index.isin(shelter_ids)].copy()

# =========================
# LOAD DISTRICTS SHAPEFILE
# =========================
districts = gpd.read_file(SHAPEFILE_PATH)
districts.columns = [c.strip().upper() for c in districts.columns]

if "ADM2_ES" not in districts.columns or "ADM3_ES" not in districts.columns:
    raise ValueError("Shapefile must contain columns ADM2_ES and ADM3_ES.")

districts = districts.set_geometry("GEOMETRY")
districts = districts[districts["ADM2_ES"].astype(str).str.upper() == "LIMA"].copy()
districts = districts.to_crs(TARGET_CRS)

# =========================
# MAP BOUNDS
# =========================
xmin, ymin, xmax, ymax = districts.total_bounds
pad_x = (xmax - xmin) * 0.03
pad_y = (ymax - ymin) * 0.03
map_bounds = (xmin - pad_x, ymin - pad_y, xmax + pad_x, ymax + pad_y)

# =========================
# PLOT STYLE
# =========================
plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white", "font.size": 10,
    "axes.titlesize": 11, "axes.labelsize": 10, "font.family": "sans-serif"
})

# =========================
# PLOT
# =========================
fig, ax = plt.subplots(1, 1, figsize=(8.8, 8.8), dpi=300)
fig.patch.set_facecolor("white")

# Fondo distritos
districts.plot(ax=ax, color="#F8F9F9", edgecolor="#7F7F7F", linewidth=0.6, zorder=1)

# Manzanas por categoría de riesgo
for cat in VULN_ORDER:
    if COLORS[cat] is None:
        continue
    subset = manzanas[manzanas["VULN_EN"] == cat]
    if len(subset) == 0:
        continue
    subset.plot(ax=ax, color=COLORS[cat], edgecolor="none",
                linewidth=0, alpha=0.85, zorder=2)

# Bordes de distritos encima
districts.boundary.plot(ax=ax, edgecolor="#555555", linewidth=0.7, zorder=3)

# ── Albergues seleccionados (rojo, cuadrado, borde negro) ──
gdf_selected.plot(
    ax=ax,
    color="red",
    markersize=6,
    alpha=1.0,
    edgecolor="none",
    zorder=6
)

style_axes(ax, map_bounds)

if SHOW_DISTRICT_LABELS:
    add_district_labels(ax, districts, fontsize=5.2, color="#333333", alpha=0.90)

add_north_arrow(ax)
add_scale_bar(ax, length_km=10)

ax.set_title(
    f"NSGA III - Shelter Selection - Disastrous",
    fontsize=11, fontweight="normal", color="#6A6A6A", pad=7
)

# =========================
# LEYENDA 1: Seismic Risk (abajo derecha, fuera del mapa)
# =========================
risk_handles = [
    Line2D([0], [0], marker='s', color='w', label=cat,
           markerfacecolor=COLORS[cat], markersize=10,
           markeredgecolor="#AAAAAA", markeredgewidth=0.4)
    for cat in VULN_ORDER
    if COLORS[cat] is not None
]

legend1 = ax.legend(
    handles=risk_handles,
    title="Seismic Risk",
    loc="lower left",
    bbox_to_anchor=(1.02, 0.02),
    borderaxespad=0.0,
    frameon=True, framealpha=0.95,
    fontsize=8, title_fontsize=8.5
)
legend1.get_frame().set_edgecolor("#B0B0B0")
legend1.get_frame().set_linewidth(0.6)

# =========================
# LEYENDA 2: Shelters + District Boundaries (arriba derecha, fuera del mapa)
# =========================
shelter_handles = [
    Line2D([0], [0], marker='o', color='w',
           label=f"NSGA-III Selected",
           markerfacecolor="red", markersize=6,
           markeredgecolor="none"),
    Line2D([0], [0], color="#555555", linewidth=0.7,
           label="District Boundaries"),
]

legend2 = ax.legend(
    handles=shelter_handles,
    loc="upper left",
    bbox_to_anchor=(1.02, 0.98),
    borderaxespad=0.0,
    frameon=True, framealpha=0.95,
    fontsize=8, title_fontsize=8.5
)
legend2.get_frame().set_edgecolor("#B0B0B0")
legend2.get_frame().set_linewidth(0.6)

# Re-agregar legend1 (ax.legend() reemplaza la anterior)
ax.add_artist(legend1)

plt.subplots_adjust(left=0.08, right=0.82, top=0.93, bottom=0.10)

plt.savefig(f"{OUTPUT_PREFIX}_sol{PARETO_SOLUTION_IDX}.png",
            dpi=300, bbox_inches="tight", facecolor="white")
plt.savefig(f"{OUTPUT_PREFIX}_sol{PARETO_SOLUTION_IDX}.pdf",
            dpi=300, bbox_inches="tight", facecolor="white")
plt.show()


#3. RISK BACKGROUND – MUNICIPALITY

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe

# =========================
# USER PARAMETERS
# =========================
SHAPEFILE_MANZANAS_PATH = "/content/drive/Shareddrives/Tesis Final /Códigos/Soledad[AppliedScience]/manzanas_caracterizadas_lima.shp"
SHAPEFILE_PATH          = "/content/drive/Shareddrives/Tesis Final /Códigos/Soledad[AppliedScience]/peru_shapes/per_admbnda_adm3_ign_20200714.shp"
SHELTERS_EXCEL_PATH     = "/content/drive/Shareddrives/Tesis Final /Códigos/Soledad[AppliedScience]/shelters_lima.xlsx"
TARGET_CRS              = "EPSG:32718"
OUTPUT_PREFIX           = "figure_block_risk_muni_shelters_lima"
SHOW_DISTRICT_LABELS    = True

# =========================
# CATEGORY MAPPING (ES → EN)
# =========================
VULN_ES_TO_EN = {
    "SIN RIESGO": "None",
    "BAJO":       "Low",
    "MEDIO":      "Medium",
    "ALTO":       "High",
    "MUY ALTO":   "Very High",
}

VULN_ORDER = ["None", "Low", "Medium", "High", "Very High"]

COLORS = {
    "None":      None,
    "Low":       "#FDEBD0",
    "Medium":    "#F5CBA7",
    "High":      "#EB984E",
    "Very High": "#CB4335",
}

# =========================
# HELPERS
# =========================
def km_formatter(x, pos):
    return f"{x/1000:.0f}"

def add_north_arrow(ax):
    ax.annotate(
        "N",
        xy=(0.94, 0.90), xytext=(0.94, 0.80),
        xycoords="axes fraction", textcoords="axes fraction",
        ha="center", va="center", fontsize=12, fontweight="bold", color="black",
        arrowprops=dict(facecolor="black", edgecolor="black", width=2, headwidth=10)
    )

def add_scale_bar(ax, length_km=10):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    bar_length = length_km * 1000
    x_start = x0 + 0.06 * (x1 - x0)
    y_start = y0 + 0.05 * (y1 - y0)
    tick_h   = 0.008 * (y1 - y0)
    ax.plot([x_start, x_start + bar_length], [y_start, y_start],
            color="black", lw=2.0, zorder=10)
    ax.plot([x_start, x_start], [y_start - tick_h, y_start + tick_h],
            color="black", lw=2.0, zorder=10)
    ax.plot([x_start + bar_length]*2, [y_start - tick_h, y_start + tick_h],
            color="black", lw=2.0, zorder=10)
    ax.text(x_start + bar_length / 2, y_start + 1.5 * tick_h,
            f"{length_km} km", ha="center", va="bottom", fontsize=9, color="#333333")

def style_axes(ax, bounds):
    xmin, ymin, xmax, ymax = bounds
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal")
    ax.grid(True, linestyle="--", linewidth=0.30, color="#DADADA", alpha=0.55)
    ax.xaxis.set_major_formatter(FuncFormatter(km_formatter))
    ax.yaxis.set_major_formatter(FuncFormatter(km_formatter))
    ax.set_xlabel("UTM Easting (km) — EPSG:32718", fontsize=10, color="#666666")
    ax.set_ylabel("UTM Northing (km) — EPSG:32718", fontsize=10, color="#666666")
    ax.tick_params(axis="both", colors="#666666", labelsize=9.5)
    for spine in ax.spines.values():
        spine.set_linewidth(0.55); spine.set_color("#A8A8A8")

def add_district_labels(ax, districts_gdf, fontsize=5.2, color="#666666", alpha=0.85):
    for _, row in districts_gdf.iterrows():
        if pd.notna(row["ADM3_ES"]):
            pt = row["GEOMETRY"].representative_point()
            txt = ax.text(
                pt.x, pt.y, str(row["ADM3_ES"]),
                fontsize=fontsize, color=color, alpha=alpha,
                ha="center", va="center", zorder=6
            )
            txt.set_path_effects([
                pe.withStroke(linewidth=1.2, foreground="white", alpha=0.9)
            ])

# =========================
# LOAD MANZANAS SHAPEFILE
# =========================
manzanas = gpd.read_file(SHAPEFILE_MANZANAS_PATH)
manzanas.columns = [c.strip() for c in manzanas.columns]

vuln_col = next((c for c in manzanas.columns if c.upper() == "NIV_RIESGO"), None)
if vuln_col is None:
    raise ValueError("Column 'NIV_RIESGO' not found in manzanas shapefile.")

manzanas["VULN_EN"] = (
    manzanas[vuln_col]
    .astype(str).str.strip().str.upper()
    .map(VULN_ES_TO_EN)
)

unmapped = manzanas["VULN_EN"].isna().sum()
if unmapped > 0:
    print(f"Warning: {unmapped} rows could not be mapped. "
          f"Unique values: {manzanas[vuln_col].unique()}")

if manzanas.crs is None:
    manzanas = manzanas.set_crs("EPSG:4326")
manzanas = manzanas.to_crs(TARGET_CRS)

# =========================
# LOAD SHELTERS (candidatos + municipalidad)
# =========================
xls      = pd.ExcelFile(SHELTERS_EXCEL_PATH)
sheet    = "Shelters" if "Shelters" in xls.sheet_names else xls.sheet_names[0]
df_shelters = pd.read_excel(SHELTERS_EXCEL_PATH, sheet_name=sheet)
df_shelters.columns = df_shelters.columns.str.strip().str.upper()

required = ["ID_ALBERGUE", "LATITUD", "LONGITUD", "ALBERGUE_MUNI"]
missing  = [c for c in required if c not in df_shelters.columns]
if missing:
    raise ValueError(f"Missing columns in Excel: {missing}")

df_shelters = df_shelters[required].dropna(subset=["LATITUD", "LONGITUD"]).copy()
df_shelters["ID_ALBERGUE"]   = df_shelters["ID_ALBERGUE"].astype(int)
df_shelters["ALBERGUE_MUNI"] = df_shelters["ALBERGUE_MUNI"].astype(int)
df_shelters = df_shelters.set_index("ID_ALBERGUE")

# Todos los candidatos
gdf_candidates = gpd.GeoDataFrame(
    df_shelters,
    geometry=gpd.points_from_xy(df_shelters["LONGITUD"], df_shelters["LATITUD"]),
    crs="EPSG:4326"
).to_crs(TARGET_CRS)

# ── Seleccionados por la Municipalidad (ALBERGUE_MUNI == 1) ──
gdf_muni = gdf_candidates[gdf_candidates["ALBERGUE_MUNI"] == 1].copy()

print(f"Total candidate shelters : {len(gdf_candidates)}")
print(f"Municipality selected    : {len(gdf_muni)}")

# =========================
# LOAD DISTRICTS SHAPEFILE
# =========================
districts = gpd.read_file(SHAPEFILE_PATH)
districts.columns = [c.strip().upper() for c in districts.columns]

if "ADM2_ES" not in districts.columns or "ADM3_ES" not in districts.columns:
    raise ValueError("Shapefile must contain columns ADM2_ES and ADM3_ES.")

districts = districts.set_geometry("GEOMETRY")
districts = districts[districts["ADM2_ES"].astype(str).str.upper() == "LIMA"].copy()
districts = districts.to_crs(TARGET_CRS)

# =========================
# MAP BOUNDS
# =========================
xmin, ymin, xmax, ymax = districts.total_bounds
pad_x = (xmax - xmin) * 0.03
pad_y = (ymax - ymin) * 0.03
map_bounds = (xmin - pad_x, ymin - pad_y, xmax + pad_x, ymax + pad_y)

# =========================
# PLOT STYLE
# =========================
plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white", "font.size": 10,
    "axes.titlesize": 11, "axes.labelsize": 10, "font.family": "sans-serif"
})

# =========================
# PLOT
# =========================
fig, ax = plt.subplots(1, 1, figsize=(8.8, 8.8), dpi=300)
fig.patch.set_facecolor("white")

# Fondo distritos
districts.plot(ax=ax, color="#F8F9F9", edgecolor="#7F7F7F", linewidth=0.6, zorder=1)

# Manzanas por categoría de riesgo
for cat in VULN_ORDER:
    if COLORS[cat] is None:
        continue
    subset = manzanas[manzanas["VULN_EN"] == cat]
    if len(subset) == 0:
        continue
    subset.plot(ax=ax, color=COLORS[cat], edgecolor="none",
                linewidth=0, alpha=0.85, zorder=2)

# Bordes de distritos encima
districts.boundary.plot(ax=ax, edgecolor="#555555", linewidth=0.7, zorder=3)

# ── Albergues seleccionados por la Municipalidad (rojo, círculo) ──
gdf_muni.plot(
    ax=ax,
    color="black",
    markersize=6,
    alpha=1.0,
    edgecolor="none",
    zorder=6
)

style_axes(ax, map_bounds)

if SHOW_DISTRICT_LABELS:
    add_district_labels(ax, districts, fontsize=5.2, color="#333333", alpha=0.90)

add_north_arrow(ax)
add_scale_bar(ax, length_km=10)

ax.set_title(
    "Municipality - Shelter Selection",
    fontsize=11, fontweight="normal", color="#6A6A6A", pad=7
)

# =========================
# LEYENDA 1: Seismic Risk (abajo derecha, fuera del mapa)
# =========================
risk_handles = [
    Line2D([0], [0], marker='s', color='w', label=cat,
           markerfacecolor=COLORS[cat], markersize=10,
           markeredgecolor="#AAAAAA", markeredgewidth=0.4)
    for cat in VULN_ORDER
    if COLORS[cat] is not None
]

legend1 = ax.legend(
    handles=risk_handles,
    title="Seismic Risk",
    loc="lower left",
    bbox_to_anchor=(1.02, 0.02),
    borderaxespad=0.0,
    frameon=True, framealpha=0.95,
    fontsize=8, title_fontsize=8.5
)
legend1.get_frame().set_edgecolor("#B0B0B0")
legend1.get_frame().set_linewidth(0.6)

# =========================
# LEYENDA 2: Shelters + District Boundaries (arriba derecha, fuera del mapa)
# =========================
shelter_handles = [
    Line2D([0], [0], marker='o', color='w',
           label=f"Municipality Selected",
           markerfacecolor="black", markersize=6,
           markeredgecolor="none"),
    Line2D([0], [0], color="#555555", linewidth=0.7,
           label="District Boundaries"),
]

legend2 = ax.legend(
    handles=shelter_handles,
    loc="upper left",
    bbox_to_anchor=(1.02, 0.98),
    borderaxespad=0.0,
    frameon=True, framealpha=0.95,
    fontsize=8, title_fontsize=8.5
)
legend2.get_frame().set_edgecolor("#B0B0B0")
legend2.get_frame().set_linewidth(0.6)

# Re-agregar legend1
ax.add_artist(legend1)

plt.subplots_adjust(left=0.08, right=0.82, top=0.93, bottom=0.10)

plt.savefig(f"{OUTPUT_PREFIX}.png", dpi=300, bbox_inches="tight", facecolor="white")
plt.savefig(f"{OUTPUT_PREFIX}.pdf", dpi=300, bbox_inches="tight", facecolor="white")
plt.show()







