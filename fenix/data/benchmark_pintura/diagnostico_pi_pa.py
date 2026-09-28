# diagnostico_pa_pi.py
#
# Insertar este bloque en analisistrans3.py justo despues de construir
# df_valid (seccion 3d, filtro de estabilizacion) y antes de la
# seccion 4 (analisis estadistico). Requiere que 'rutaProducto' este
# disponible en df_valid (ya lo esta, viene del pivote).
#
# Objetivo: verificar si la duracion DIS/DIL/DIS+DIL difiere entre
# pintura al agua (PA_*) y pintura industrial (PI_*), para decidir si
# el supuesto "la duracion no depende del volumen si se usa el equipo
# adecuado" tambien vale entre familias PA/PI, o si hace falta
# reportar parametros nominales separados por familia.

print("\n" + "=" * 80)
print("📊 DIAGNOSTICO: PINTURA AL AGUA (PA) vs. INDUSTRIAL (PI)")
print("=" * 80)

df_valid['familia'] = df_valid['rutaProducto'].str.extract(r'^(PA|PI)_', expand=False)
print("\nConteo de lotes por familia (ruta Dis-Dil, periodo estabilizado):")
print(df_valid['familia'].value_counts(dropna=False))

# Estadisticas descriptivas por familia (sin outliers, mismo filtro
# p99 aplicado globalmente para no introducir un criterio distinto)
df_sin_outliers_familia = df_sin_outliers.copy()
df_sin_outliers_familia['familia'] = df_valid.loc[df_sin_outliers_familia.index, 'rutaProducto']\
    .str.extract(r'^(PA|PI)_', expand=False)

for fam in ['PA', 'PI']:
    sub = df_sin_outliers_familia[df_sin_outliers_familia['familia'] == fam]
    print(f"\n--- Familia {fam} (n={len(sub)}) ---")
    print(sub[['DIS', 'DIL', 'DIS+DIL']].agg(['mean', 'median', 'std']).round(2).to_string())

# Test de Mann-Whitney U: PA vs PI, para cada etapa
print("\nMann-Whitney U, PA vs PI (sin outliers):")
for col in ['DIS', 'DIL', 'DIS+DIL']:
    pa = df_sin_outliers_familia.loc[df_sin_outliers_familia['familia'] == 'PA', col]
    pi = df_sin_outliers_familia.loc[df_sin_outliers_familia['familia'] == 'PI', col]
    if len(pa) > 0 and len(pi) > 0:
        u_stat, u_p = stats.mannwhitneyu(pa, pi, alternative='two-sided')
        print(f"  {col}: U = {u_stat:.1f}, p-value = {u_p:.4g}  "
              f"(mediana PA={pa.median():.1f}, mediana PI={pi.median():.1f})")
    else:
        print(f"  {col}: datos insuficientes en una de las familias")