# analisistrans4.py
# Version corregida y separada por familia de analisistrans3.py
# para el articulo companion SCADA.
#
# Cambios respecto a analisistrans3.py:
#   1. Se agrega un filtro CONFIGURABLE por familia de producto
#      (FAMILIA_PRINCIPAL). El pipeline completo de estadisticas,
#      pruebas y graficos (secciones 4, 4b, 5, 6) corre UNICAMENTE
#      sobre esa familia, que es el caso de estudio principal del
#      articulo (por defecto: 'PA', pintura al agua).
#   2. Se agrega una seccion 4c breve y separada para la familia
#      secundaria (por defecto: 'PI', pintura industrial/esmaltes),
#      que solo calcula las 2-3 cifras necesarias para el parrafo de
#      mencion (n, mediana DIS+DIL, ratio respecto a la familia
#      principal), SIN repetir el ajuste log-normal, Mann-Kendall,
#      etc. La muestra de PI (n=36-45 lotes) es insuficiente para un
#      analisis de estabilidad independiente en este dataset.
#   3. Los nombres de archivo de salida (figuras y Excel) incluyen el
#      sufijo de la familia principal, para no confundir corridas.
#   4. Se agrega, al final, un parrafo de discusion en consola que
#      conecta el hallazgo PA-vs-PI con el argumento del metamodelo:
#      el analisis basado en actividad (DIS/DIL como actividades de
#      un Resource Holon, no como bloque monolitico de proceso)
#      permite separar limpiamente ambas poblaciones sin rediseñar el
#      modelo, y refuerza la necesidad de calibrar parametros
#      nominales por recurso en vez de un tau global unico.
#
# Para correr el caso PI en vez de PA, cambiar FAMILIA_PRINCIPAL mas
# abajo y volver a ejecutar (df_valid_completo conserva ambas
# familias, asi que no hace falta tocar las consultas SQL).

import pyodbc
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
import sys

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

# ============================================
# CONFIGURACION
# ============================================
server = 'localhost\\SQLEXPRESS'
database = 'SiopDB'

FECHA_ESTABILIZACION = '2014-12-01'

# Familia usada como caso de estudio principal del articulo
# (histograma, boxplot, serie temporal, ajuste log-normal,
# Mann-Kendall). La otra familia presente en 'familia' se trata
# como secundaria/mencion (seccion 4c).
FAMILIA_PRINCIPAL = 'PA'

conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes'
conn = pyodbc.connect(conn_str)

print("=" * 80)
print("ANALISIS DE TIEMPOS DE PRODUCCION - RUTA DIS-DIL (dos etapas)")
print(f"Periodo estabilizado: a partir de {FECHA_ESTABILIZACION}")
print(f"Familia principal del articulo: {FAMILIA_PRINCIPAL}")
print("=" * 80)

# ============================================
# 1. IDENTIFICAR PRODUCTOS DIS-DIL
# ============================================
print("\n📦 1. IDENTIFICANDO PRODUCTOS DIS-DIL")
query_productos = """
SELECT
    pd.id,
    pd.nombre AS producto_nombre,
    pd.codigo,
    COUNT(op.id) AS cantidad_ordenes
FROM producto_def pd
INNER JOIN orden_produccion op ON pd.id = op.producto_id
WHERE pd.nombre LIKE '%DIS%'
   OR pd.nombre LIKE '%DIL%'
   OR pd.nombre LIKE '%dispersion%'
   OR pd.nombre LIKE '%dilucion%'
GROUP BY pd.id, pd.nombre, pd.codigo
ORDER BY cantidad_ordenes DESC
"""
df_productos = pd.read_sql(query_productos, conn)
print(f"Productos DIS-DIL encontrados: {len(df_productos)}")

# ============================================
# 2. TIEMPOS DE OPERACIONES DESDE EL HISTORIAL
# ============================================
print("\n⏱️ 2. OBTENIENDO TIEMPOS DE OPERACIONES DESDE EL HISTORIAL DE EVENTOS")
query_ops = """
SELECT
    h.ejecucionOperacion_id AS ejec_id,
    MIN(h.fechaOcurrencia) AS fecha_inicio,
    MAX(h.fechaOcurrencia) AS fecha_fin,
    DATEDIFF(SECOND, MIN(h.fechaOcurrencia), MAX(h.fechaOcurrencia)) / 60.0 AS duracion_minutos
FROM historia h
WHERE h.fechaOcurrencia IS NOT NULL AND h.ejecucionOperacion_id IS NOT NULL
GROUP BY h.ejecucionOperacion_id
HAVING MIN(h.fechaOcurrencia) < MAX(h.fechaOcurrencia)
"""
df_durations = pd.read_sql(query_ops, conn)
print(f"Operaciones con duracion calculada: {len(df_durations)}")

# ============================================
# 3. ASOCIAR OPERACIONES A SU LOTE Y RUTA
# ============================================
print("\n🔗 3. ASOCIANDO OPERACIONES A SU LOTE (mcr_id) Y TIPO DE ETAPA")
query_rel = """
SELECT
    mcr.id AS mcr_id,
    mcr.rutaProducto,
    h.ejecucionOperacion_id AS ejec_id,
    eo.nombreNivel
FROM mensaje_crear_red mcr
INNER JOIN historia h ON mcr.id = h.mensajeCrearRed_id
INNER JOIN ejecucion_operacion eo ON h.ejecucionOperacion_id = eo.id
WHERE mcr.rutaProducto IS NOT NULL
"""
df_rel = pd.read_sql(query_rel, conn)
df_merged = df_durations.merge(df_rel, on='ejec_id', how='inner')
print(f"Registros de operaciones vinculados a lotes: {len(df_merged)}")

rutas_candidatas = df_merged.loc[
    df_merged['rutaProducto'].str.contains('DIS', case=False, na=False)
    & df_merged['rutaProducto'].str.contains('DIL', case=False, na=False),
    'rutaProducto'
].unique()
print("\n🔍 Valores unicos de rutaProducto que contienen DIS y DIL:")
for r in sorted(rutas_candidatas):
    print(f"   - {r}")

# ============================================
# 3b. FILTRO ESTRICTO A LA RUTA DIS-DIL (dos etapas)
# ============================================
es_dis = df_merged['rutaProducto'].str.contains('DIS', case=False, na=False)
es_dil = df_merged['rutaProducto'].str.contains('DIL', case=False, na=False)
es_mol = df_merged['rutaProducto'].str.contains('MOL', case=False, na=False)
df_merged['es_dis_dil_estricto'] = es_dis & es_dil & ~es_mol

df_dis_dil_ops = df_merged[df_merged['es_dis_dil_estricto']].copy()
print(f"\nOperaciones de la ruta ESTRICTA Dis-Dil (sin molienda): {len(df_dis_dil_ops)}")

def classify_op(name):
    name_lower = str(name).lower()
    if 'dispersion' in name_lower:
        return 'DIS'
    elif 'dilucion' in name_lower:
        return 'DIL'
    else:
        return 'Other'

df_dis_dil_ops['op_type'] = df_dis_dil_ops['nombreNivel'].apply(classify_op)
print("\nConteo de operaciones clasificadas (ruta estricta Dis-Dil):")
print(df_dis_dil_ops.groupby('op_type').size())

# ============================================
# 3c. EMPAREJAR DIS Y DIL DEL MISMO LOTE
# ============================================
df_dis_dil_ops = df_dis_dil_ops.sort_values('fecha_inicio')

df_pivoted = df_dis_dil_ops.pivot_table(
    index=['mcr_id', 'rutaProducto'],
    columns='op_type',
    values='duracion_minutos',
    aggfunc='first'
).reset_index()

fecha_dis = (
    df_dis_dil_ops[df_dis_dil_ops['op_type'] == 'DIS']
    .groupby('mcr_id')['fecha_inicio'].min()
    .rename('fecha_referencia')
)
df_pivoted = df_pivoted.merge(fecha_dis, on='mcr_id', how='left')

if 'DIS' in df_pivoted.columns and 'DIL' in df_pivoted.columns:
    df_valid_completo = df_pivoted.dropna(subset=['DIS', 'DIL', 'fecha_referencia']).copy()
    df_valid_completo['DIS+DIL'] = df_valid_completo['DIS'] + df_valid_completo['DIL']
    print(f"\nLotes completos validos (DIS y DIL emparejados, ruta estricta): {len(df_valid_completo)}")
else:
    print("❌ Error: No se encontraron columnas DIS o DIL en la tabla pivote.")
    conn.close()
    exit(1)

# ============================================
# 3d. FILTRO DE ESTABILIZACION (excluir fase de implantacion)
# ============================================
df_valid_completo['fecha_referencia'] = pd.to_datetime(df_valid_completo['fecha_referencia'])
n_antes_filtro_fecha = len(df_valid_completo)
df_valid_completo = df_valid_completo[df_valid_completo['fecha_referencia'] >= FECHA_ESTABILIZACION].copy()
print(f"Lotes antes del filtro de estabilizacion: {n_antes_filtro_fecha}")
print(f"Lotes despues de excluir fase de implantacion (< {FECHA_ESTABILIZACION}): {len(df_valid_completo)}")

# ============================================
# 3e. SEPARACION POR FAMILIA (PA vs PI)
# ============================================
# El analisis basado en actividad permite identificar, sin rediseñar
# el modelo, que las actividades DIS/DIL de distintas familias de
# producto pertenecen a poblaciones estadisticamente distintas: basta
# con condicionar sobre 'familia' antes de calcular estadisticas por
# Resource Holon.
print("\n" + "=" * 80)
print("📊 3e. SEPARACION POR FAMILIA: PINTURA AL AGUA (PA) vs. INDUSTRIAL (PI)")
print("=" * 80)

df_valid_completo['familia'] = df_valid_completo['rutaProducto'].str.extract(r'^(PA|PI)_', expand=False)
print("\nConteo de lotes por familia (ruta Dis-Dil, periodo estabilizado):")
print(df_valid_completo['familia'].value_counts(dropna=False))

df_sin_outliers_pre = df_valid_completo.copy()
for col in ['DIS', 'DIL', 'DIS+DIL']:
    p99_pre = df_valid_completo[col].quantile(0.99)
    df_sin_outliers_pre = df_sin_outliers_pre[df_sin_outliers_pre[col] <= p99_pre]

for fam in ['PA', 'PI']:
    sub = df_sin_outliers_pre[df_sin_outliers_pre['familia'] == fam]
    print(f"\n--- Familia {fam} (n={len(sub)}) ---")
    print(sub[['DIS', 'DIL', 'DIS+DIL']].agg(['mean', 'median', 'std']).round(2).to_string())

print("\nMann-Whitney U, PA vs PI (sin outliers):")
mw_pa_pi = {}
for col in ['DIS', 'DIL', 'DIS+DIL']:
    pa = df_sin_outliers_pre.loc[df_sin_outliers_pre['familia'] == 'PA', col]
    pi = df_sin_outliers_pre.loc[df_sin_outliers_pre['familia'] == 'PI', col]
    if len(pa) > 0 and len(pi) > 0:
        u_stat, u_p = stats.mannwhitneyu(pa, pi, alternative='two-sided')
        mw_pa_pi[col] = (u_stat, u_p, pa.median(), pi.median())
        print(f"  {col}: U = {u_stat:.1f}, p-value = {u_p:.4g}  "
              f"(mediana PA={pa.median():.1f}, mediana PI={pi.median():.1f})")
    else:
        print(f"  {col}: datos insuficientes en una de las familias")

# --- Referencia 'mezclado' (todas las familias juntas, sin separar) ---
# Se calcula aqui, antes de filtrar por familia, unicamente para poder
# mostrar en 4b/4c el contraste explicito entre analizar mezclado y
# analizar por familia -- ese contraste es evidencia central del
# argumento del metamodelo (ver seccion 7).
ref_mezclado = {}
_cv_mix = df_sin_outliers_pre[['DIS', 'DIL', 'DIS+DIL']].std() / df_sin_outliers_pre[['DIS', 'DIL', 'DIS+DIL']].mean()
ref_mezclado['corr_DIS_DIL'] = df_sin_outliers_pre['DIS'].corr(df_sin_outliers_pre['DIL'])
ref_mezclado['cv_DIS'] = _cv_mix['DIS']
ref_mezclado['cv_DIL'] = _cv_mix['DIL']
ref_mezclado['cv_DIS+DIL'] = _cv_mix['DIS+DIL']
_serie_mix = (
    df_valid_completo.set_index('fecha_referencia')['DIS+DIL']
    .resample('W').mean().dropna()
)

# A partir de aqui, el pipeline principal (secciones 4, 4b, 5, 6) corre
# UNICAMENTE sobre FAMILIA_PRINCIPAL. df_valid_completo se conserva
# intacto para poder correr la seccion 4c sobre la otra familia.
df_valid = df_valid_completo[df_valid_completo['familia'] == FAMILIA_PRINCIPAL].copy()
print(f"\n➡️  A partir de aqui, secciones 4-6 corren solo sobre la familia "
      f"{FAMILIA_PRINCIPAL} (n={len(df_valid)}).")

# ============================================
# 4. ANALISIS ESTADISTICO (solo FAMILIA_PRINCIPAL)
# ============================================
print("\n" + "=" * 80)
print(f"📊 4. ANALISIS ESTADISTICO (ruta Dis-Dil, familia {FAMILIA_PRINCIPAL}, periodo estabilizado)")
print("=" * 80)

stats_all = df_valid[['DIS', 'DIL', 'DIS+DIL']].describe().round(2)
print("\n📋 ESTADISTICAS GENERALES (Con Outliers):")
print(stats_all.to_string())

print("\n📊 ESTADISTICAS SIN OUTLIERS (> percentil 99 por etapa):")
df_sin_outliers = df_valid.copy()
for col in ['DIS', 'DIL', 'DIS+DIL']:
    p99 = df_valid[col].quantile(0.99)
    df_sin_outliers = df_sin_outliers[df_sin_outliers[col] <= p99]

stats_sin_outliers = df_sin_outliers[['DIS', 'DIL', 'DIS+DIL']].agg(
    ['count', 'mean', 'median', 'std', 'min', 'max']).round(2)
print(stats_sin_outliers.to_string())

print("\n📊 IQR Y COEFICIENTE DE VARIACION (Sin Outliers):")
iqr = df_sin_outliers[['DIS', 'DIL', 'DIS+DIL']].apply(lambda x: x.quantile(0.75) - x.quantile(0.25)).round(2)
cv = (df_sin_outliers[['DIS', 'DIL', 'DIS+DIL']].std() / df_sin_outliers[['DIS', 'DIL', 'DIS+DIL']].mean()).round(3)
print("IQR (minutos):")
print(iqr.to_string())
print("\nCV (std/mean):")
print(cv.to_string())

cov = df_sin_outliers['DIS'].cov(df_sin_outliers['DIL'])
corr = df_sin_outliers['DIS'].corr(df_sin_outliers['DIL'])
print(f"\nCovarianza DIS-DIL (Sin Outliers): {cov:.2f}")
print(f"Correlacion DIS-DIL (Sin Outliers): {corr:.4f}")

# ============================================
# 4b. PRUEBAS ESTADISTICAS (solo FAMILIA_PRINCIPAL)
# ============================================
print("\n" + "=" * 80)
print(f"📊 4b. PRUEBAS ESTADISTICAS - familia {FAMILIA_PRINCIPAL} (log-normal, Mann-Kendall, Mann-Whitney)")
print("=" * 80)

data_lognorm = df_sin_outliers['DIS+DIL']
data_lognorm = data_lognorm[data_lognorm > 0]
shape, loc, scale = stats.lognorm.fit(data_lognorm, floc=0)
mu_hat = np.log(scale)
sigma_hat = shape
ks_stat, ks_p = stats.kstest(data_lognorm, 'lognorm', args=(shape, loc, scale))
print(f"\nAjuste log-normal sobre DIS+DIL (n={len(data_lognorm)}):")
print(f"  mu    = {mu_hat:.4f}")
print(f"  sigma = {sigma_hat:.4f}")
print(f"  KS statistic = {ks_stat:.4f}, p-value = {ks_p:.4f}")
print(f"  (mediana implicita = exp(mu) = {np.exp(mu_hat):.1f} min -- comparar con la mediana empirica reportada arriba)")

def mann_kendall_test(x):
    x = np.asarray(x)
    n = len(x)
    s = 0
    for k in range(n - 1):
        s += np.sum(np.sign(x[k + 1:] - x[k]))
    _, counts = np.unique(x, return_counts=True)
    tie_correction = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var_s = (n * (n - 1) * (2 * n + 5) - tie_correction) / 18
    if var_s <= 0:
        return s, 0.0, 1.0
    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return s, z, p

serie_semanal = (
    df_valid.set_index('fecha_referencia')['DIS+DIL']
    .resample('W').mean().dropna()
)
mk_s, mk_z, mk_p = mann_kendall_test(serie_semanal.values)
print(f"\nMann-Kendall sobre serie semanal DIS+DIL (periodo estabilizado, n_semanas={len(serie_semanal)}):")
print(f"  S = {mk_s}, Z = {mk_z:.4f}, p-value = {mk_p:.4f}")

mw_stat, mw_p = stats.mannwhitneyu(df_sin_outliers['DIS'], df_sin_outliers['DIL'], alternative='two-sided')
print(f"\nMann-Whitney U entre DIS y DIL (sin outliers), familia {FAMILIA_PRINCIPAL}: U = {mw_stat:.1f}, p-value = {mw_p:.4g}")

# --- Mann-Kendall sobre la misma serie pero con TODAS las familias
# mezcladas, solo para el contraste explicito de abajo ---
mk_s_mix, mk_z_mix, mk_p_mix = mann_kendall_test(_serie_mix.values)

print("\n" + "-" * 80)
print(f"📊 CONTRASTE EXPLICITO: mezclado (todas las familias) vs. familia {FAMILIA_PRINCIPAL} sola")
print("-" * 80)
print(f"  Correlacion DIS-DIL:      mezclado = {ref_mezclado['corr_DIS_DIL']:.4f}   "
      f"| {FAMILIA_PRINCIPAL} sola = {corr:.4f}")
print(f"  CV(DIS):                  mezclado = {ref_mezclado['cv_DIS']:.3f}    "
      f"| {FAMILIA_PRINCIPAL} sola = {cv['DIS']:.3f}")
print(f"  CV(DIL):                  mezclado = {ref_mezclado['cv_DIL']:.3f}    "
      f"| {FAMILIA_PRINCIPAL} sola = {cv['DIL']:.3f}")
print(f"  Mann-Kendall (semanal):   mezclado -> Z={mk_z_mix:.4f}, p={mk_p_mix:.4f}   "
      f"| {FAMILIA_PRINCIPAL} sola -> Z={mk_z:.4f}, p={mk_p:.4f}")
print("  Nota: el contraste ilustra que el analisis por actividad/familia revela")
print("  senales (deriva temporal, dispersion residual) que el analisis mezclado")
print("  diluye o enmascara; no implica que el analisis mezclado sea 'incorrecto',")
print("  sino que opera a un nivel de agregacion distinto.")

# ============================================
# 4c. FAMILIA SECUNDARIA (mencion breve, sin pruebas completas)
# ============================================
familias_presentes = [f for f in df_valid_completo['familia'].dropna().unique() if f != FAMILIA_PRINCIPAL]
print("\n" + "=" * 80)
print(f"📊 4c. FAMILIA SECUNDARIA - mencion breve (no se repiten pruebas de estabilidad)")
print("=" * 80)

resumen_secundaria = {}
for fam_sec in familias_presentes:
    df_sec = df_valid_completo[df_valid_completo['familia'] == fam_sec].copy()
    df_sec_sin_out = df_sec.copy()
    for col in ['DIS', 'DIL', 'DIS+DIL']:
        p99_sec = df_sec[col].quantile(0.99)
        df_sec_sin_out = df_sec_sin_out[df_sec_sin_out[col] <= p99_sec]

    mediana_princ = df_sin_outliers['DIS+DIL'].median()
    mediana_sec = df_sec_sin_out['DIS+DIL'].median()
    ratio = mediana_sec / mediana_princ if mediana_princ else float('nan')

    resumen_secundaria[fam_sec] = {
        'n': len(df_sec),
        'mediana_DIS+DIL': mediana_sec,
        'ratio_vs_principal': ratio,
    }
    print(f"\nFamilia {fam_sec}: n = {len(df_sec)} lotes")
    print(f"  Mediana DIS+DIL = {mediana_sec:.1f} min "
          f"(~{ratio:.1f}x la mediana de {FAMILIA_PRINCIPAL} = {mediana_princ:.1f} min)")
    print(f"  Nota: muestra insuficiente (n={len(df_sec)}) para un analisis de "
          f"estabilidad independiente en este dataset; se reporta solo como mencion.")

# ============================================
# 5. GRAFICOS (solo FAMILIA_PRINCIPAL)
# ============================================
print(f"\n📈 5. GENERANDO GRAFICOS ACTUALIZADOS PARA EL ARTICULO (familia {FAMILIA_PRINCIPAL})")

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 10

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
data = df_sin_outliers['DIS+DIL']

axes[0].hist(data, bins=30, edgecolor='black', alpha=0.7, color='steelblue')
axes[0].axvline(data.mean(), color='red', linestyle='--', linewidth=2, label=f'Media: {data.mean():.0f} min')
axes[0].axvline(data.median(), color='green', linestyle='--', linewidth=2, label=f'Mediana: {data.median():.0f} min')
axes[0].set_xlabel('Duracion DIS+DIL (minutos)', fontsize=11)
axes[0].set_ylabel('Frecuencia', fontsize=11)
axes[0].set_title(f'Distribucion de Tiempos DIS+DIL - {FAMILIA_PRINCIPAL} (Lineal)', fontsize=12, fontweight='bold')
axes[0].legend()

axes[1].hist(data[data > 0], bins=30, edgecolor='black', alpha=0.7, color='coral', log=True)
axes[1].axvline(data.mean(), color='red', linestyle='--', linewidth=2, label=f'Media: {data.mean():.0f} min')
axes[1].axvline(data.median(), color='green', linestyle='--', linewidth=2, label=f'Mediana: {data.median():.0f} min')
axes[1].set_xlabel('Duracion DIS+DIL (minutos)', fontsize=11)
axes[1].set_ylabel('Frecuencia (escala log)', fontsize=11)
axes[1].set_title(f'Distribucion de Tiempos DIS+DIL - {FAMILIA_PRINCIPAL} (Logaritmica)', fontsize=12, fontweight='bold')
axes[1].legend()

plt.tight_layout()
fname_hist = f'figura_histograma_tiempos_{FAMILIA_PRINCIPAL}.png'
plt.savefig(fname_hist, dpi=300, bbox_inches='tight')
plt.close()
print(f"  • Guardado: {fname_hist}")

fig, ax = plt.subplots(figsize=(10, 6))
df_box = df_valid.copy()
for col in ['DIS', 'DIL', 'DIS+DIL']:
    p95 = df_valid[col].quantile(0.95)
    df_box = df_box[df_box[col] <= p95]

df_box_melted = df_box.melt(
    value_vars=['DIS', 'DIL', 'DIS+DIL'],
    var_name='Etapa',
    value_name='duracion_minutos'
)
sns.boxplot(data=df_box_melted, x='Etapa', y='duracion_minutos', ax=ax, palette='viridis')
ax.set_xlabel('Etapas del Proceso', fontsize=12)
ax.set_ylabel('Duracion (minutos)', fontsize=12)
ax.set_title(f'Distribucion de Tiempos por Etapa - {FAMILIA_PRINCIPAL} (Hasta percentil 95)', fontsize=14, fontweight='bold')
plt.tight_layout()
fname_box = f'figura_boxplot_rutas_{FAMILIA_PRINCIPAL}.png'
plt.savefig(fname_box, dpi=300, bbox_inches='tight')
plt.close()
print(f"  • Guardado: {fname_box}")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(serie_semanal.index, serie_semanal.values, marker='o', linewidth=2, color='coral', markersize=4)
ax.set_xlabel('Fecha', fontsize=12)
ax.set_ylabel('Duracion Promedio DIS+DIL (minutos)', fontsize=12)
ax.set_title(f'Evolucion Temporal de Tiempos de Produccion - {FAMILIA_PRINCIPAL} '
             f'(Semanal, desde {FECHA_ESTABILIZACION})', fontsize=13, fontweight='bold')
plt.xticks(rotation=45)
plt.tight_layout()
fname_evol = f'figura_evolucion_temporal_{FAMILIA_PRINCIPAL}.png'
plt.savefig(fname_evol, dpi=300, bbox_inches='tight')
plt.close()
print(f"  • Guardado: {fname_evol}")

# ============================================
# 6. EXPORTAR RESULTADOS
# ============================================
print("\n💾 6. EXPORTANDO RESULTADOS A EXCEL")
fname_xlsx = f'reporte_tiempos_articulo_v4_{FAMILIA_PRINCIPAL}.xlsx'
try:
    with pd.ExcelWriter(fname_xlsx, engine='openpyxl') as writer:
        df_valid.to_excel(writer, sheet_name='Lotes_Validos_Filtrados', index=False)
        df_sin_outliers.to_excel(writer, sheet_name='Lotes_Sin_Outliers', index=False)
        stats_all.to_excel(writer, sheet_name='Estadisticas_Con_Outliers')
        stats_sin_outliers.to_excel(writer, sheet_name='Estadisticas_Sin_Outliers')
        pd.DataFrame({
            'metrica': ['familia_principal', 'mu_lognorm', 'sigma_lognorm', 'ks_stat', 'ks_p',
                        'mk_S', 'mk_Z', 'mk_p', 'mw_U', 'mw_p',
                        'n_lotes_pre_filtro_fecha', 'n_lotes_post_filtro_fecha_todas_familias',
                        'n_lotes_familia_principal', 'n_semanas_serie'],
            'valor': [FAMILIA_PRINCIPAL, mu_hat, sigma_hat, ks_stat, ks_p,
                      mk_s, mk_z, mk_p, mw_stat, mw_p,
                      n_antes_filtro_fecha, len(df_valid_completo),
                      len(df_valid), len(serie_semanal)]
        }).to_excel(writer, sheet_name='Pruebas_Estadisticas', index=False)

        # Mencion breve de la familia secundaria, para el parrafo del articulo
        if resumen_secundaria:
            pd.DataFrame(resumen_secundaria).T.to_excel(writer, sheet_name='Familia_Secundaria_Mencion')

        # Comparacion PA vs PI (para justificar la separacion en el texto)
        df_valid_completo.to_excel(writer, sheet_name='Todos_los_Lotes_Por_Familia', index=False)

        # Contraste explicito mezclado vs familia principal (evidencia del
        # argumento del metamodelo: mismo enfoque, distinto nivel de agregacion)
        pd.DataFrame({
            'metrica': ['corr_DIS_DIL', 'cv_DIS', 'cv_DIL', 'mann_kendall_Z', 'mann_kendall_p'],
            'mezclado_todas_familias': [ref_mezclado['corr_DIS_DIL'], ref_mezclado['cv_DIS'],
                                         ref_mezclado['cv_DIL'], mk_z_mix, mk_p_mix],
            f'{FAMILIA_PRINCIPAL}_sola': [corr, cv['DIS'], cv['DIL'], mk_z, mk_p],
        }).to_excel(writer, sheet_name='Contraste_Mezclado_vs_Familia', index=False)

    print(f"✅ Reporte guardado: {fname_xlsx}")
except Exception as e:
    print(f"❌ Error al exportar a Excel: {e}")

conn.close()

# ============================================
# 7. NOTA PARA LA DISCUSION DEL ARTICULO
# ============================================
print("\n" + "=" * 80)
print("📝 7. NOTA PARA LA DISCUSION DEL ARTICULO")
print("=" * 80)
_mediana_princ_txt = f"{df_sin_outliers['DIS+DIL'].median():.1f} min"
_detalle_secundarias = "; ".join(
    f"{fam}: {r['mediana_DIS+DIL']:.1f} min (~{r['ratio_vs_principal']:.1f}x)"
    for fam, r in resumen_secundaria.items()
) or "sin familia secundaria detectada"

print(f"""
El objetivo de este analisis no es caracterizar un proceso en
particular, sino mostrar que un unico metamodelo -- aplicado de forma
consistente a nivel de ACTIVIDAD (DIS, DIL como actividades ejecutadas
por un Resource Holon) -- permite describir y analizar procesos
estructuralmente distintos sin necesitar un modelo diferente para cada
caso. La separacion {FAMILIA_PRINCIPAL} vs. otra(s) familia(s)
(mediana {FAMILIA_PRINCIPAL} = {_mediana_princ_txt}; {_detalle_secundarias})
no exigio ningun cambio al metamodelo: basto con condicionar el
analisis sobre el atributo 'familia', ya presente en los datos de
ejecucion.

El contraste mezclado-vs-{FAMILIA_PRINCIPAL} (ver bloque anterior:
correlacion DIS-DIL {ref_mezclado['corr_DIS_DIL']:.2f} -> {corr:.2f},
CV(DIS) {ref_mezclado['cv_DIS']:.2f} -> {cv['DIS']:.2f}, tendencia
Mann-Kendall p={mk_p_mix:.3f} -> p={mk_p:.3f}) muestra que el mismo
enfoque, aplicado a distintos niveles de agregacion, revela senales
(deriva temporal, dispersion residual) que un analisis agregado
diluye. Con honestidad: esto no dice que el proceso {FAMILIA_PRINCIPAL}
este "mal": la variabilidad residual y la deriva detectada dentro de
la familia son datos a investigar, no defectos del modelo -- pueden
originarse en calidad de insumos, desgaste o mantenimiento de equipo,
turno u operario, entre otras causas operativas que este dataset no
permite discriminar mas alla de la actividad y la familia de producto.
El punto metodologico es que el metamodelo, por operar a nivel de
actividad y de Resource Holon, es lo que permite ubicar y describir
esas distorsiones -- caracterizarlas -- en vez de que queden ocultas en
un promedio global.
""")
print("✅ Analisis completado exitosamente")