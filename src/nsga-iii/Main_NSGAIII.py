
#-----------------------
#Part 1: All Scenarios
#-----------------------

"""
Generates the Pareto front CSV for ALL earthquake levels.
Output: pareto_front_mild.csv, pareto_front_moderate.csv, etc.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.metrics.pairwise import haversine_distances
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.optimize import minimize
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.core.problem import Problem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
CONFIG = {
    "n_gen":    500,   # generations per level (increase to 300–500 for better quality)
    "pop_size": 200,   # individuals per generation
    "earthquake_risk_levels": {
        "mild":        {"intensity": 0.5, "max_shelter_proportion": 0.0441},  # ~129
        "moderate":    {"intensity": 0.7, "max_shelter_proportion": 0.089},   # ~364
        "severe":      {"intensity": 1.0, "max_shelter_proportion": 0.0822},  # ~481
        "very strong": {"intensity": 1.2, "max_shelter_proportion": 0.0849},  # ~596
        "disastrous":  {"intensity": 1.5, "max_shelter_proportion": 0.0687},  # ~603
    },
    "poblacion_total": 10178814,
}

SHELTERS_PATH = "shelters_lima.xlsx"
OUTPUT_DIR    = ""   # output folder; "" = same directory


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic weights per level (same as the original code)
# ─────────────────────────────────────────────────────────────────────────────
def dynamic_weights(level):
    base = {
        "mild":        (0.7, 0.2, 0.1),
        "moderate":    (0.4, 0.45, 0.15),
        "severe":      (0.1, 0.7, 0.2),
        "very strong": (0.1, 0.4, 0.5),
        "disastrous":  (0.1, 0.1, 0.8),
    }
    return base[level]


# ─────────────────────────────────────────────────────────────────────────────
# Optimization problem
# ─────────────────────────────────────────────────────────────────────────────
class ShelterOptimizationProblem(Problem):
    def __init__(self, gdf, n_selected, weights, intensity):
        # Para sismos fuertes, excluir albergues en zonas de alto riesgo
        if intensity >= 1.0:
            gdf = gdf[
                (gdf['RIES_NORM'] < 0.1) & (gdf['VULNE_NORM'] < 0.1)
            ].reset_index(drop=True)
            print(f"    Albergues tras filtro de riesgo: {len(gdf)}")

        super().__init__(
            n_var=len(gdf), n_obj=3, n_constr=2,
            xl=0, xu=len(gdf) - 1, type_var=int,
        )
        self.gdf        = gdf
        self.n_selected = n_selected
        self.w1, self.w2, self.w3 = weights
        self.k = 0.1 + (intensity - 0.5) * 0.9 / 1.0

        coords = np.radians(gdf[['LATITUD', 'LONGITUD']].values)

        print(f"    Precomputing distance matrix ({len(gdf)}×{len(gdf)})... ",
              end="", flush=True)
        self.dist_matrix = haversine_distances(coords) * 6371
        print("OK")

        vul  = gdf['VULNE_NORM'].values
        risk = gdf['RIES_NORM'].values
        manz = gdf['MANZANAS_norm'].values
        self.obj3_per_shelter = (
            (1 - vul)  * (1 - np.exp(-self.k * manz))
            + (1 - risk) * (1 - np.exp(-self.k * manz))
        )

        n = n_selected
        self.max_distance   = np.max(self.dist_matrix) * (n * (n - 1) / 2)
        self.max_population = gdf['M_POB17'].nlargest(n_selected).sum()
        self.max_vul_risk   = self.obj3_per_shelter.max() * n_selected

        high_risk = gdf[(gdf['RIES_NORM'] >= 0.5) & (gdf['VULNE_NORM'] >= 0.5)]
        if len(high_risk) > 0:
            hr_coords = np.radians(high_risk[['LATITUD', 'LONGITUD']].values)
            self.hr_dist = haversine_distances(coords, hr_coords) * 6371
        else:
            self.hr_dist = None

        self.aforo   = gdf['AFORO'].values
        self.pob_dem = gdf['POB_DEMAN'].values
        self.pop     = gdf['M_POB17'].values

    def _evaluate(self, x, out, *args, **kwargs):
        n_ind = x.shape[0]
        F = np.zeros((n_ind, 3))
        G = np.zeros((n_ind, 2))

        for i, scores in enumerate(x):
            idx = np.argsort(scores)[-self.n_selected:]

            sub        = self.dist_matrix[np.ix_(idx, idx)]
            F[i, 0]   = -(sub.sum() / 2 / self.max_distance) * self.w1
            F[i, 1]   = -(self.pop[idx].sum() / self.max_population) * self.w2
            F[i, 2]   = -(self.obj3_per_shelter[idx].sum() / self.max_vul_risk) * self.w3
            G[i, 0]   = max(0, self.pob_dem[idx].sum() - self.aforo[idx].sum())
            G[i, 1]   = (
                1.0 if (self.hr_dist is not None and np.any(self.hr_dist[idx] < 0.5))
                else 0.0
            )

        out["F"] = F
        out["G"] = G


# ─────────────────────────────────────────────────────────────────────────────
# Loading and normalization
# ─────────────────────────────────────────────────────────────────────────────
def load_and_normalize(filepath):
    df = pd.read_excel(filepath)
    df.columns = df.columns.str.strip().str.upper()
    df = df[[
        "LATITUD", "LONGITUD", "AFORO", "AREA", "MANZANAS",
        "M_POB17", "RIES_NORM", "VULNE_NORM", "DIST_HOSP",
        "POB_DEMAN", "ALBERGUE_MUNI",
    ]].dropna().reset_index(drop=True)

    for col, new in [
        ('AREA',      'AREA_norm'),
        ('M_POB17',   'M_POB17_norm'),
        ('RIES_NORM', 'RIES_NORM_norm'),
        ('VULNE_NORM','VULNE_NORM_norm'),
        ('MANZANAS',  'MANZANAS_norm'),
    ]:
        lo, hi = df[col].min(), df[col].max()
        df[new] = (df[col] - lo) / (hi - lo) if hi != lo else 0.0

    return gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.LONGITUD, df.LATITUD), crs="EPSG:4326"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Saving the CSV
# ─────────────────────────────────────────────────────────────────────────────
def save_pareto_front(result, n_selected, filename):
    rows = []
    for objectives, decision_vars in zip(result.F, result.X):
        shelter_indices = np.argsort(decision_vars)[-n_selected:].tolist()
        rows.append({
            "Distance":        float(-objectives[0]),
            "Population":      float(-objectives[1]),
            "Safety":          float(-objectives[2]),
            "Shelter_Indices": shelter_indices,
        })
    df = pd.DataFrame(rows, columns=["Distance", "Population", "Safety", "Shelter_Indices"])
    df.to_csv(filename, index=False)
    print(f"  ✓ CSV saved: {filename}  ({len(df)} solutions, {n_selected} shelters/solution)")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Optimization of one level
# ─────────────────────────────────────────────────────────────────────────────
def run_level(gdf, level, params):
    intensity  = params["intensity"]
    proportion = params["max_shelter_proportion"]
    n_selected = int(len(gdf) * proportion * intensity)
    weights    = dynamic_weights(level)

    print(f"\n{'='*60}")
    print(f"  Level     : {level.upper()}")
    print(f"  Intensity : {intensity}  |  Proportion: {proportion}")
    print(f"  n_selected: {n_selected} shelters")
    print(f"  Weights   : distance={weights[0]}, population={weights[1]}, safety={weights[2]}")
    print(f"{'='*60}")

    problem  = ShelterOptimizationProblem(gdf, n_selected, weights, intensity)
    ref_dirs = get_reference_directions("das-dennis", 3, n_partitions=12)
    algorithm = NSGA3(
        pop_size=CONFIG["pop_size"],
        ref_dirs=ref_dirs,
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        eliminate_duplicates=True,
    )

    result = minimize(
        problem, algorithm,
        termination=('n_gen', CONFIG["n_gen"]),
        seed=42,
        verbose=True,
    )

    if result is None or result.F is None:
        print(f"  ✗ No valid solutions found for {level}.")
        return None

    import os
    filename = os.path.join(OUTPUT_DIR, f"pareto_front_{level.replace(' ', '_')}.csv")
    save_pareto_front(result, n_selected, filename)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("Loading data...")
    gdf   = load_and_normalize(SHELTERS_PATH)
    total = len(gdf)
    print(f"  Total shelters in dataset: {total}\n")

    # Mostrar resumen de n_selected por nivel antes de empezar
    print("Summary of shelters to be selected by level:")
    for level, params in CONFIG["earthquake_risk_levels"].items():
        n = int(total * params["max_shelter_proportion"] * params["intensity"])
        print(f"  {level:12s} → {n:4d} shelters")

    resultados = {}
    for level, params in CONFIG["earthquake_risk_levels"].items():
        try:
            result = run_level(gdf, level, params)
            resultados[level] = "OK" if result is not None else "SIN SOLUCIÓN"
        except Exception as e:
            print(f"  ✗ Error in {level}: {e}")
            resultados[level] = f"ERROR: {e}"

    # Resumen final
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    for level, estado in resultados.items():
        print(f"  {level:12s} → {estado}")


if __name__ == "__main__":
    main()


#-------------------------
#Part 2: Professional Map
#-------------------------

import ast
import argparse
import warnings
import re
import unicodedata

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Rectangle, ConnectionPatch
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from scipy.ndimage import gaussian_filter

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
SHELTERS_PATH       = "shelters_lima.xlsx"
SHAPEFILE_PATH      = "peru_shapes/per_admbnda_adm3_ign_20200714.shp"
TARGET_CRS          = "EPSG:32718"
SELECTION_CRITERION = "balanced"

ZOOM_BOUNDS = (267_000, 8_648_000, 300_000, 8_676_000)

COLOR_SELECTED  = "red"
COLOR_EDGE_SEL  = "#7F0000"
COLOR_CANDIDATE = "#9E9E9E"

# Radius of the KDE halo around each shelter (in UTM meters)
# Equivalent to the radius=15 parameter (pixels) in Plotly's density_mapbox
# Increase it for larger blobs, decrease it for tighter ones
KDE_RADIUS_M = 1_500   # ~1.5 km

LEVEL_CONFIG = {
    "mild":        {"csv": "pareto_front_mild.csv",        "label": "Mild (intensity 0.5)"},
    "moderate":    {"csv": "pareto_front_moderate.csv",    "label": "Moderate (intensity 0.7)"},
    "severe":      {"csv": "pareto_front_severe.csv",      "label": "Severe (intensity 1.0)"},
    "very_strong": {"csv": "pareto_front_very_strong.csv", "label": "Very Strong (intensity 1.2)"},
    "disastrous":  {"csv": "pareto_front_disastrous.csv",  "label": "Disastrous (intensity 1.5)"},
}

# ─────────────────────────────────────────────────────────────────────────────
# CARTOGRAPHIC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def normalize_name(text):
    text = str(text).strip().upper()
    text = "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text)

def km_formatter(x, pos):
    return f"{x/1000:.0f}"

def add_north_arrow(ax):
    ax.annotate("N",
        xy=(0.955, 0.910), xytext=(0.955, 0.840),
        xycoords="axes fraction", textcoords="axes fraction",
        ha="center", va="center",
        fontsize=11, fontweight="bold", color="black",
        arrowprops=dict(facecolor="black", edgecolor="black",
                        width=2.5, headwidth=10, headlength=8))

def add_scale_bar(ax, length_km=10, fontsize=9):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    bar = length_km * 1000
    xs  = x0 + 0.05 * (x1 - x0)
    ys  = y0 + 0.04 * (y1 - y0)
    th  = 0.007 * (y1 - y0)
    kw  = dict(color="black", lw=2.0, zorder=10, solid_capstyle="butt")
    ax.plot([xs, xs+bar], [ys, ys], **kw)
    ax.plot([xs, xs],         [ys-th, ys+th], **kw)
    ax.plot([xs+bar, xs+bar], [ys-th, ys+th], **kw)
    ax.text(xs+bar/2, ys+1.6*th, f"{length_km} km",
            ha="center", va="bottom", fontsize=fontsize,
            color="#333333", zorder=10)

def style_axes(ax, bounds, xlabel=True, ylabel=True, labelsize=9):
    xmin, ymin, xmax, ymax = bounds
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", linewidth=0.28, color="#DADADA", alpha=0.55)
    ax.xaxis.set_major_formatter(FuncFormatter(km_formatter))
    ax.yaxis.set_major_formatter(FuncFormatter(km_formatter))
    if xlabel:
        ax.set_xlabel("UTM Easting (km) — EPSG:32718", fontsize=labelsize, color="#555555")
    if ylabel:
        ax.set_ylabel("UTM Northing (km) — EPSG:32718", fontsize=labelsize, color="#555555")
    ax.tick_params(axis="both", colors="#666666", labelsize=labelsize)
    for spine in ax.spines.values():
        spine.set_linewidth(0.6)
        spine.set_color("#A8A8A8")

def add_district_labels(ax, gdf, fontsize=5.4, color="#222222", alpha=0.9):
    for _, row in gdf.iterrows():
        if pd.notna(row.get("ADM3_ES")):
            pt = row.geometry.representative_point()
            txt = ax.text(
                pt.x, pt.y, str(row["ADM3_ES"]),
                fontsize=fontsize, color=color, alpha=alpha,
                ha="center", va="center", zorder=7,
                clip_on=True,
                path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])
            txt.set_clip_box(ax.bbox)

# ─────────────────────────────────────────────────────────────────────────────
# LOCALIZED KDE — exact replica of Plotly's density_mapbox
#
# Method: 2D histogram weighted by RIES_NORM + Gaussian filter with a
# fixed radius in meters. Color appears only around shelters,
# the rest remains NaN → transparent (white background).
# ─────────────────────────────────────────────────────────────────────────────
def compute_kde_grid(shelters_gdf, districts, resolution=400, radius_m=KDE_RADIUS_M):
    xs   = shelters_gdf.geometry.x.values
    ys   = shelters_gdf.geometry.y.values
    vals = shelters_gdf["RIES_NORM"].values.astype(float)

    xmin, ymin, xmax, ymax = districts.total_bounds

    # Histograma 2D ponderado por RIES_NORM
    Zi, ye, xe = np.histogram2d(
        ys, xs,
        bins=resolution,
        range=[[ymin, ymax], [xmin, xmax]],
        weights=vals,
    )

    # Tamaño de píxel en metros
    pixel_m = (xmax - xmin) / resolution
    # Sigma en píxeles equivalente al radio en metros
    sigma_px = radius_m / pixel_m
    Zi = gaussian_filter(Zi.astype(float), sigma=sigma_px)

    # Máscara estricta: solo donde hay señal real (> 2% del máximo)
    # → todo lo demás es NaN (transparente, fondo blanco)
    threshold = Zi.max() * 0.02
    Zi_masked = np.where(Zi >= threshold, Zi, np.nan)

    # Máscara al polígono de Lima
    lima_union = districts.unary_union
    xi_centers = (xe[:-1] + xe[1:]) / 2
    yi_centers = (ye[:-1] + ye[1:]) / 2
    Xi, Yi = np.meshgrid(xi_centers, yi_centers)

    try:
        from shapely.vectorized import contains as shp_contains
        mask = shp_contains(lima_union, Xi.ravel(), Yi.ravel()).reshape(Xi.shape)
    except ImportError:
        from shapely.geometry import Point
        mask = np.array([lima_union.contains(Point(x, y))
                         for x, y in zip(Xi.ravel(), Yi.ravel())]
                        ).reshape(Xi.shape)

    Zi_masked = np.where(mask, Zi_masked, np.nan)
    extent    = [xmin, xmax, ymin, ymax]
    return Zi_masked, extent


def draw_kde(ax, Zi_masked, extent, alpha=0.6):
    cmap = plt.get_cmap("Reds").copy()
    cmap.set_bad(alpha=0)      # NaN → transparente (fondo blanco)
    cmap.set_under(alpha=0)
    ax.imshow(Zi_masked, extent=extent, origin="lower",
              cmap=cmap, alpha=alpha, zorder=2,
              interpolation="bilinear", aspect="auto")

# ─────────────────────────────────────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
def load_base_data():
    df = pd.read_excel(SHELTERS_PATH)
    df.columns = df.columns.str.strip().str.upper()
    df = df[["LATITUD","LONGITUD","AFORO","M_POB17",
             "RIES_NORM","VULNE_NORM"]].dropna().reset_index(drop=True)
    shelters_gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["LONGITUD"], df["LATITUD"]),
        crs="EPSG:4326").to_crs(TARGET_CRS)
    districts = gpd.read_file(SHAPEFILE_PATH)
    districts = districts[
        districts["ADM2_ES"].astype(str).str.upper() == "LIMA"
    ].copy().to_crs(TARGET_CRS)
    return shelters_gdf, districts

def load_pareto_csv(path):
    df = pd.read_csv(path)
    df["Shelter_Indices"] = df["Shelter_Indices"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
    return df

def pick_solution(pareto_df, criterion):
    if criterion == "best_safety":
        idx = pareto_df["Safety"].idxmax()
    elif criterion == "best_population":
        idx = pareto_df["Population"].idxmax()
    elif criterion == "best_distance":
        idx = pareto_df["Distance"].idxmax()
    else:
        cols = ["Distance","Population","Safety"]
        norm = (pareto_df[cols] - pareto_df[cols].min()) / (
               pareto_df[cols].max() - pareto_df[cols].min())
        idx  = np.linalg.norm(1 - norm.values, axis=1).argmin()
    row = pareto_df.iloc[idx]
    print(f"  Row {idx}: Dist={row['Distance']:.4f} "
          f"Pop={row['Population']:.4f} Safe={row['Safety']:.4f} "
          f"N={len(row['Shelter_Indices'])} shelters")
    return row["Shelter_Indices"]

# ─────────────────────────────────────────────────────────────────────────────
# DRAW LAYERS
# ─────────────────────────────────────────────────────────────────────────────
def draw_layers(ax, districts, cand_gdf, sel_gdf,
                Zi_masked, kde_extent,
                s_cand=1.5, s_sel=20, lw_edge=0.4):
    districts.plot(ax=ax, color="white", edgecolor="#CCCCCC",
                   linewidth=0.4, zorder=1)
    draw_kde(ax, Zi_masked, kde_extent, alpha=0.6)
    districts.plot(ax=ax, color="none", edgecolor="#555555",
                   linewidth=0.65, zorder=4)
    ax.scatter(cand_gdf.geometry.x, cand_gdf.geometry.y,
               s=s_cand, color=COLOR_CANDIDATE, alpha=0.45,
               linewidths=0, zorder=5)
    ax.scatter(sel_gdf.geometry.x, sel_gdf.geometry.y,
               s=s_sel, color=COLOR_SELECTED,
               edgecolors=COLOR_EDGE_SEL, linewidths=lw_edge,
               alpha=0.92, zorder=6)

# ─────────────────────────────────────────────────────────────────────────────
# FULL MAP
# ─────────────────────────────────────────────────────────────────────────────
def make_map(shelters_gdf, districts, selected_idx, level, cfg):
    sel_set  = set(selected_idx)
    cand_gdf = shelters_gdf.loc[[i for i in shelters_gdf.index if i not in sel_set]]
    sel_gdf  = shelters_gdf.iloc[selected_idx]

    xmin, ymin, xmax, ymax = districts.total_bounds
    px = (xmax-xmin)*0.03;  py = (ymax-ymin)*0.03
    bounds = (xmin-px, ymin-py, xmax+px, ymax+py)

    plt.rcParams.update({
        "figure.facecolor":"white","axes.facecolor":"white",
        "savefig.facecolor":"white","font.family":"sans-serif","font.size":10})

    print("  Computing localized KDE...", end="", flush=True)
    Zi_masked, kde_extent = compute_kde_grid(shelters_gdf, districts, resolution=400)
    print(f" OK  (radius={KDE_RADIUS_M}m, signal in "
          f"{100*np.sum(~np.isnan(Zi_masked))/Zi_masked.size:.1f}% of the map)")

    fig = plt.figure(figsize=(13, 10.5), dpi=300)
    fig.patch.set_facecolor("white")

    ax = fig.add_axes([0.04, 0.07, 0.60, 0.87])
    draw_layers(ax, districts, cand_gdf, sel_gdf,
                Zi_masked, kde_extent, s_cand=1.5, s_sel=20)
    style_axes(ax, bounds, labelsize=9)
    add_district_labels(ax, districts, fontsize=5.5)
    add_north_arrow(ax)
    add_scale_bar(ax, length_km=10)
    ax.set_title(
        f"NSGA-III Shelter Selection — {cfg['label']}  |  Criterion: {SELECTION_CRITERION}",
        fontsize=10.5, fontweight="normal", color="#333333", pad=7)

    zx0, zy0, zx1, zy1 = ZOOM_BOUNDS
    ax.add_patch(Rectangle((zx0, zy0), zx1-zx0, zy1-zy0,
        linewidth=1.8, edgecolor="#111111",
        facecolor="none", linestyle="--", zorder=8))

    # Legend
    h_cand = Line2D([0],[0], marker="o", color="w",
                    markerfacecolor=COLOR_CANDIDATE, markeredgecolor="#777777",
                    markersize=5.5, label="Candidate Shelters")
    h_sel  = Line2D([0],[0], marker="o", color="w",
                    markerfacecolor=COLOR_SELECTED, markeredgecolor=COLOR_EDGE_SEL,
                    markersize=8, label="NSGA-III Selected")

    ax_leg = fig.add_axes([0.66, 0.84, 0.32, 0.13])
    ax_leg.axis("off")
    leg = ax_leg.legend(handles=[h_cand, h_sel],
        title="Shelters", loc="upper left", bbox_to_anchor=(0,1),
        frameon=True, framealpha=0.97, fontsize=9, title_fontsize=9.5)
    leg.get_frame().set_edgecolor("#B0B0B0")
    leg.get_frame().set_linewidth(0.7)

    # Colorbar
    ax_cbar = fig.add_axes([0.67, 0.065, 0.22, 0.020])
    sm = ScalarMappable(cmap=plt.get_cmap("Reds"), norm=Normalize(0, 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=ax_cbar, orientation="horizontal")
    cbar.set_label("Seismic risk density (RIES_NORM)",
                   fontsize=8, color="#444444", labelpad=3)
    cbar.ax.tick_params(labelsize=7.5)
    cbar.set_ticks([0, 0.5, 1])
    cbar.set_ticklabels(["Low", "Med.", "High"])
    ax_cbar.spines[:].set_linewidth(0.5)

    # Zoom
    ax_zoom = fig.add_axes([0.66, 0.18, 0.32, 0.62])
    draw_layers(ax_zoom, districts, cand_gdf, sel_gdf,
                Zi_masked, kde_extent, s_cand=2.0, s_sel=14, lw_edge=0.35)
    style_axes(ax_zoom, ZOOM_BOUNDS, labelsize=10)
    # Borde del zoom igual que las líneas conectoras
    for spine in ax_zoom.spines.values():
        spine.set_linewidth(1.4)
        spine.set_color("#222222")
    ax_zoom.set_xlabel("UTM Easting (km)", fontsize=10, color="#555555")
    ax_zoom.set_ylabel("UTM Northing (km)", fontsize=10, color="#555555")
    add_district_labels(ax_zoom, districts, fontsize=6.5, color="#111111", alpha=0.95)
    ax_zoom.set_title("Urban center detail", fontsize=11,
                      color="#222222", pad=5, style="italic", fontweight="semibold")
    add_scale_bar(ax_zoom, length_km=5, fontsize=9)

    # ── Connector lines rectangle → zoom ─────────────────────────────────────
    # Connects the top-right and bottom-right corners of the rectangle
    # with the left corners of the zoom panel (ConnectionPatch handles
    # the coordinate transformation between the map and zoom systems)
    for (xa, ya), (xb, yb) in [
        ((zx1, zy1), (0, 1)),   # top-right corner → top-left (zoom)
        ((zx1, zy0), (0, 0)),   # bottom-right corner → bottom-left (zoom)
    ]:
        con = ConnectionPatch(
            xyA=(xa, ya), coordsA="data", axesA=ax,
            xyB=(xb, yb), coordsB="axes fraction", axesB=ax_zoom,
            color="#222222", linewidth=1.4, linestyle="-",
            zorder=10, clip_on=False,
        )
        fig.add_artist(con)

    fname = f"map_nsga3_{level}"
    fig.savefig(f"{fname}.png", dpi=300, facecolor="white")
    fig.savefig(f"{fname}.pdf",          facecolor="white")
    plt.close(fig)
    print(f"  Saved: {fname}.png / {fname}.pdf")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=list(LEVEL_CONFIG.keys()),
                        default=None,
                        help="Nivel a graficar. Sin argumento → todos.")
    args = parser.parse_args(args=[])  # compatible con Colab

    print("Loading base data...")
    shelters_gdf, districts = load_base_data()
    print(f"  {len(shelters_gdf)} shelters  |  {len(districts)} districts")

    levels = [args.level] if args.level else list(LEVEL_CONFIG.keys())

    for level in levels:
        cfg = LEVEL_CONFIG[level]
        print(f"\n{'='*55}\n  {cfg['label'].upper()}\n{'='*55}")

        try:
            pareto_df = load_pareto_csv(cfg["csv"])
        except FileNotFoundError:
            print(f"  File not found: {cfg['csv']} — skipping.")
            continue

        print(f"  {len(pareto_df)} solutions in the Pareto front.")
        selected_idx = pick_solution(pareto_df, SELECTION_CRITERION)

        plot_shelters = shelters_gdf.copy()
        if max(selected_idx) >= len(plot_shelters):
            print("  Applying filter RIES_NORM/VULNE_NORM < 0.1...")
            plot_shelters = plot_shelters[
                (plot_shelters["RIES_NORM"] < 0.1) &
                (plot_shelters["VULNE_NORM"] < 0.1)
            ].reset_index(drop=True)
            print(f"  {len(plot_shelters)} shelters after filtering.")

        make_map(plot_shelters, districts, selected_idx, level, cfg)

    print("\nListo.")

if __name__ == "__main__":
    main()



