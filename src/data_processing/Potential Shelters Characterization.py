import pandas as pd
import geopandas as gpd

# 1. EXTRACTION OF CENSUS BLOCKS (Shapefile)

gdf_districts = gpd.read_file('MANZANA.shp')

gdf_Lima = gdf_districts.copy()
gdf_Lima = gdf_Lima[(gdf_Lima.DEPARTAMEN == 'LIMA') & (gdf_Lima.PROVINCIA == 'LIMA')]

# 2. IDENTIFICATION AND EXTRACTIOM OF POTENTIAL SHELTER LOCATIONS
#---2.1. Recreational Centers

df_recreacion = pd.read_excel('Equipamiento de recreación pública (PLANMET 2040).xlsx')

df_recreacion = df_recreacion.rename(columns={
    'Shape__Area': 'Shape_Area',
    'Shape__Length': 'Shape_Length'
})

df_recreacion['ID_MANZANA'] = df_recreacion['ID_MANZANA'].astype(str)

gdf_recreacion = df_recreacion.merge(gdf_Lima, left_on='ID_MANZANA', right_on='IDMANZANA', how='inner') # MERGE SHAPEFILE DATA
print('Recreational centers with available shapefiles:', gdf_recreacion.shape[0])

gdf_result = df_recreacion.merge(gdf_Lima, left_on='ID_MANZANA', right_on='IDMANZANA', how='outer', indicator=True) # NO FOUND
no_match_recreacion = gdf_result[gdf_result['_merge'] == 'left_only']
no_match_recreacion_rastreable = no_match_recreacion.dropna(subset=['NOM_EQ'])
print('Recreational centers WITHOUT a shapefile but still traceable:', no_match_recreacion_rastreable.shape[0])

#---2.2. Sports Centers

df_deportivo = pd.read_excel('Equipamiento deportivo (PLANMET 2040).xlsx')
df_deportivo = df_deportivo.drop(columns=['NOM_UA'])
df_deportivo['ID_MANZANA'] = df_deportivo['ID_MANZANA'].astype(str)df_deportivo['ID_MANZANA'] = df_deportivo['ID_MANZANA'].astype(str)

gdf_deportivo = df_deportivo.merge(gdf_Lima, left_on='ID_MANZANA', right_on='IDMANZANA', how='inner')
print('Sports centers with available shapefiles:', gdf_deportivo.shape[0])

gdf_result2 = df_deportivo.merge(gdf_Lima, left_on='ID_MANZANA', right_on='IDMANZANA', how='outer', indicator=True)
no_match_deportivo = gdf_result2[gdf_result2['_merge'] == 'left_only']
no_match_deportivo_rastreable = no_match_deportivo.dropna(subset=['NOM_EQ'])
print('Sports centers WITHOUT a shapefile but still traceable:', no_match_deportivo_rastreable.shape[0])

# 3. GROUPING OF POTENTIAL SHELTERS: RECREATIONAL + SPORTS

gdf_combined = pd.concat([gdf_recreacion, gdf_deportivo], axis=0, ignore_index=True)
gdf_combined = gdf_combined.drop_duplicates(subset='ID_MANZANA', keep='first')
print("Total potential shelters from recreational and sports facilities:", gdf_combined.shape[0])

gdf_combined = gpd.GeoDataFrame(gdf_combined, geometry='geometry') # Export the potential shelters dataset as a shapefile

gdf_combined = gdf_combined.rename(columns={
    'Shape_Length': 'Shape_Len',
})

gdf_combined.to_file('albergues_potenciales_lima.shp', driver='ESRI Shapefile')

#---3.1. Removal of Non-Informative Columns
gdf_combined = gdf_combined.drop(columns=['OBJECTID', 'COD_EQ', 'IDLOTE', 'IDMZNAR', 'COD_SECT', 'AREA_M2', 'IDMANZANA', 'DEPARTAMEN', 'PROVINCIA', 'DISTRITO', 'NOMCCCPP', 'IDCCPP'])

#---3.2. Longitude and Latitude Integration
gdf_combined_coor = gdf_combined.copy()
gdf_combined_coor['centroid'] = gdf_combined_coor.geometry.centroid # Compute centroids if geometries are not points

# Extract latitude and longitude from centroids
gdf_combined_coor['latitud'] = gdf_combined_coor['centroid'].y
gdf_combined_coor['longitud'] = gdf_combined_coor['centroid'].x

# 4. CHARACTERIZATION OF POTENTIAL SHELTERS BASED ON THEIR ASOCIATED CENSUS BLOCK
#---4.1. Feature Aggregation
df_manzanas_carac = pd.read_excel('BD_ManzanasCarac.xlsx')
df_manzanas_carac = df_manzanas_carac.rename(columns={'COB_AP17': 'COB_AGUA','COB_EE17': 'COB_ELEC'})
df_manzanas_carac['ID_MANZANA'] = df_manzanas_carac['ID_MANZANA'].astype(str)

gdf_albergues_carac = df_manzanas_carac.merge(gdf_combined_coor, left_on='ID_MANZANA', right_on='ID_MANZANA', how='inner')
print('Characterized potential shelters:', gdf_albergues_carac.shape[0])

gdf_albergues_carac['GEOMETRY'] = gdf_albergues_carac.geometry
gdf_albergues_carac = gdf_albergues_carac.drop(columns=['geometry'])

# The column NOMBDIST_VULN is not relevant (it contains only one value: 'LIMA'), so it is removed
gdf_albergues_carac = gdf_albergues_carac.drop(columns=['NOMBDIST_VULN'])

# Remove the 'centroid' column since only one geometry column is allowed
gdf_albergues_carac = gdf_albergues_carac.drop(columns=['centroid'])

# Export the potential shelters dataset as a shapefile
gdf_albergues_carac = gpd.GeoDataFrame(gdf_albergues_carac, geometry='GEOMETRY')
gdf_albergues_carac.to_file('albergues_caracterizados_lima.shp', driver='ESRI Shapefile')

#---4.2. Aggregation by Interdistrict Zones: Potential Shelters
from unidecode import unidecode

def custom_unidecode(text):
    text = text.upper()
    return ''.join([char if char=='Ñ' else unidecode(char) for char in text])

Distrito = [ "Ancón", "Carabayllo", "Comas", "Independencia", "Los Olivos", 
        "Puente Piedra", "San Martín de Porres", "Santa Rosa",
        "Ate","Chaclacayo" ,"Cieneguilla", "El Agustino","La Molina", 
        "Lurigancho", "San Juan de Lurigancho", "San Luis","Santa Anita",
        "Barranco", "Chorrillos", "Lurín", "Pachacámac", "Pucusana","Punta Hermosa", 
        "Punta Negra", "San Bartolo", "San Juan de Miraflores","Santa María del Mar", 
        "Villa El Salvador", "Villa María del Triunfo",
        "LIMA", "Breña", "Jesús María", "Lince", 
        "La Victoria", "Rímac", "San Borja",
        "Magdalena del Mar", "Miraflores", "Pueblo Libre", 
        "San Isidro", "Santiago de Surco","San Miguel", "Surquillo"]

Zona = ["Lima Norte", "Lima Norte", "Lima Norte", "Lima Norte", 
        "Lima Norte", "Lima Norte", "Lima Norte", "Lima Norte",
        "Lima Este", "Lima Este","Lima Este","Lima Este" , "Lima Este", 
        "Lima Este", "Lima Este", "Lima Este","Lima Este",
        "Lima Sur", "Lima Sur", "Lima Sur", "Lima Sur", 
        "Lima Sur", "Lima Sur", "Lima Sur", "Lima Sur", 
        "Lima Sur", "Lima Sur","Lima Sur","Lima Sur",
        "Lima Centro", "Lima Centro", "Lima Centro", "Lima Centro", 
        "Lima Centro", "Lima Centro", "Lima Centro",
        "Lima Centro", "Lima Centro", "Lima Centro", 
        "Lima Centro", "Lima Centro", "Lima Centro","Lima Centro"]

dist_uni = []
for dist in Distrito:
    dist_uni.append(custom_unidecode(dist))

zonifica = {i:j for i,j in zip(dist_uni,Zona)}
zonifica['SURQUILLO']='Lima Centro'

def zoni(dist):
    return zonifica[dist]

gdf_albergues_carac['ZONA'] = gdf_albergues_carac['NOMBDIST'].apply(zoni)

zona_dist = gdf_albergues_carac.groupby('ZONA')

#---4.3. Aggregation by Interdistrict Zones: Census Blocks
df_manzanas_carac['ID_MANZANA'] = df_manzanas_carac['ID_MANZANA'].astype(str)

gdf_manzanas_carac = df_manzanas_carac.merge(gdf_Lima, left_on='ID_MANZANA', right_on='IDMANZANA', how='inner')

print('Characterized census blocks in Lima:', gdf_manzanas_carac.shape[0])

gdf_manzanas_carac['ZONA'] = gdf_manzanas_carac['DISTRITO'].apply(zoni)
zona_mzn = gdf_manzanas_carac.groupby('ZONA')

#5. CHARACTERIZATION OF POTENTIAL SHELTERS USING NEARBY CENSUS BLOCKS

#Import of Characterized Census Blocks Database
gdf_mzn_carac = gpd.read_file('manzanas_caracterizadas_lima.shp')

#Import of Characterized Shelters Database
gdf_albergues = gpd.read_file('albergues_caracterizados_lima.shp')

gdf_albergues = gdf_albergues.rename(columns={'NIV_VULNE': 'A_VULNE','NIV_RIESGO': 'A_RIESGO','TOT_POB17':'A_POB17','COB_AGUA':'A_COBAGUA','COB_ELEC':'A_COBELEC','Shape_Area':'AREA','Shape_Len':'PERIMETRO'})

gdf_albergues = gdf_albergues.drop(columns=['DESC_VULNE', 'DESC_RIESG','TOT_POB20','DENS_POB17','DENS_POB20','TIPO_EE17','CODDPTO','CODPROV','CODDIST','CODZONA','SUFZONA','CODMZNA','SUFMZNA','CODCCPP','Shape_STAr','Shape_STLe'])

#Potential Shelter Filtering
mascara = ((gdf_albergues['A_VULNE'] == 'BAJA') | (gdf_albergues['A_VULNE'] == 'MEDIA') | (gdf_albergues['A_VULNE'] == 'SIN VULNE')) & ((gdf_albergues['A_RIESGO'] == 'MEDIO') | (gdf_albergues['A_RIESGO'] == 'SIN RIESGO')) 

gdf_albergues_filtro = gdf_albergues[mascara].copy()
print("Number of public recreational and sports shelters with low vulnerability:", gdf_albergues_filtro.shape[0])

gdf_albergues_filtro_1 = gdf_albergues_filtro[['TIPO_EQ','SUBTIPO_EQ','NOM_EQ','NOMBDIST','latitud','longitud','AREA']].copy()
nombre = (gdf_albergues_filtro_1.TIPO_EQ.fillna('') + ' - ' + 
          gdf_albergues_filtro_1.SUBTIPO_EQ.fillna('') + ' - ' + 
          gdf_albergues_filtro_1.NOM_EQ.fillna(''))

gdf_albergues_filtro_1.insert(0, 'Albergue', nombre)
gdf_albergues_filtro_1 = gdf_albergues_filtro_1.drop(['TIPO_EQ','SUBTIPO_EQ','NOM_EQ'],axis=1)
gdf_albergues_filtro_1 = gdf_albergues_filtro_1.rename(columns={'Albergue': 'ALBERGUE','NOMBDIST':'DISTRITO','latitud':'LATITUD','longitud':'LONGITUD'})

gdf_albergues_filtro_2 = gdf_albergues_filtro[['NOM_EQ','NOMBDIST','latitud','longitud','AREA']].copy()
gdf_albergues_filtro_2 = gdf_albergues_filtro_2.rename(columns={'NOM_EQ': 'ALBERGUE','NOMBDIST':'DISTRITO','latitud':'LATITUD','longitud':'LONGITUD'})

#Union of Potential Shelters and Municipal Shelters
df_albergues_muni = pd.read_excel("ALBERGUES TEMPORALES MUNICIPALIDAD_v2.xlsx")

Distrito = [ "Ancón", "Carabayllo", "Comas", "Independencia", "Los Olivos", 
        "Puente Piedra", "San Martín de Porres", "Santa Rosa",
        "Ate","Chaclacayo" ,"Cieneguilla", "El Agustino","La Molina", 
        "Lurigancho-Chosica", "San Juan de Lurigancho", "San Luis","Santa Anita",
        "Barranco", "Chorrillos", "Lurín", "Pachacamac", "Pucusana","Punta Hermosa", 
        "Punta Negra", "San Bartolo", "San Juan de Miraflores","Santa María del Mar", 
        "Villa el Salvador", "Villa María del Triunfo",
        "Cercado de Lima", "Breña", "Jesús María", "Lince", 
        "La Victoria", "Rimac", "San Borja",
        "Magdalena del Mar", "Miraflores", "Pueblo Libre", 
        "San Isidro", "Santiago de Surco","San Miguel", "Surquillo"]

dist_unicode = ['ANCON', 'CARABAYLLO', 'COMAS', 'INDEPENDENCIA', 'LOS OLIVOS', 'PUENTE PIEDRA', 'SAN MARTIN DE PORRES',
             'SANTA ROSA', 'ATE', 'CHACLACAYO', 'CIENEGUILLA', 'EL AGUSTINO', 'LA MOLINA', 'LURIGANCHO', 'SAN JUAN DE LURIGANCHO',
             'SAN LUIS', 'SANTA ANITA', 'BARRANCO', 'CHORRILLOS', 'LURIN', 'PACHACAMAC', 'PUCUSANA', 'PUNTA HERMOSA', 'PUNTA NEGRA',
             'SAN BARTOLO', 'SAN JUAN DE MIRAFLORES', 'SANTA MARIA DEL MAR', 'VILLA EL SALVADOR', 'VILLA MARIA DEL TRIUNFO',
             'LIMA', 'BREÑA', 'JESUS MARIA', 'LINCE', 'LA VICTORIA', 'RIMAC', 'SAN BORJA', 'MAGDALENA DEL MAR', 'MIRAFLORES', 
             'PUEBLO LIBRE', 'SAN ISIDRO', 'SANTIAGO DE SURCO', 'SAN MIGUEL', 'SURQUILLO']

dist_mayusc = {i:j for i,j in zip(Distrito,dist_unicode)}

def d_mayusc(dist):
    return dist_mayusc[dist]

nuevos_dist = []
for d in df_albergues_muni.DISTRITO.tolist():
    nuevos_dist.append(d_mayusc(d))

df_albergues_muni = df_albergues_muni.drop(['CÓDIGO','DISTRITO','DIRECCIÓN'],axis=1)
df_albergues_muni.insert(1, 'DISTRITO', nuevos_dist)

# Perform the merge with an indicator to track the origin of each row
albergues_merged = pd.merge(gdf_albergues_filtro_2, df_albergues_muni, on=['ALBERGUE', 'DISTRITO'], how='outer', indicator=True)

right = albergues_merged[albergues_merged['_merge'] == 'right_only']
both = albergues_merged[albergues_merged['_merge'] == 'both']
left = albergues_merged[albergues_merged['_merge'] == 'left_only']

# MUNICIPAL shelters without a match
right = right.drop(['LATITUD_x','LONGITUD_x','_merge','AREA_x'],axis=1)
right = right.rename(columns={'LATITUD_y':'LATITUD','LONGITUD_y':'LONGITUD','AREA_y':'AREA'})

# Shelters WITH a match
both = both.drop(['LATITUD_y','LONGITUD_y','_merge','AREA_y'],axis=1)
both = both.rename(columns={'LATITUD_x':'LATITUD','LONGITUD_x':'LONGITUD','AREA_x':'AREA'})

# POTENTIAL shelters without a match
left = left.drop(['LATITUD_y','LONGITUD_y','_merge','AREA_y'],axis=1)
left = left.rename(columns={'LATITUD_x':'LATITUD','LONGITUD_x':'LONGITUD','AREA_x':'AREA'})

albergue_nombre_left = pd.merge(gdf_albergues_filtro_1, left, on=['LATITUD', 'LONGITUD'], how='inner')

albergue_nombre_left = albergue_nombre_left.drop(['ALBERGUE_y','DISTRITO_y','AREA_y'],axis=1)
albergue_nombre_left = albergue_nombre_left.rename(columns={'ALBERGUE_x':'ALBERGUE','DISTRITO_x':'DISTRITO','AREA_x':'AREA'})

albergue_completo = pd.concat([right, both, albergue_nombre_left], axis=0)

valores = [f"A_{str(i).zfill(4)}" for i in range(1, 5856)]

albergue_completo.insert(0, 'ID_ALBERGUE', valores)

#---5.1. Characterization by Census Blocks: Seismic Vulnerability
import math

def calcular_rango(lat_central, lon_central, radio_km=1.5):
    # Convertir el radio de km a radianes
    radio_tierra_km = 6371.01  # Radio promedio de la Tierra en km
    radio_radianes = radio_km / radio_tierra_km

    # Convertir latitud y longitud central a radianes
    lat_central_rad = math.radians(lat_central)
    lon_central_rad = math.radians(lon_central)

    # Calcular los límites de latitud
    lat_min = lat_central_rad - radio_radianes
    lat_max = lat_central_rad + radio_radianes

    # Calcular los límites de longitud
    lon_min = lon_central_rad - math.asin(math.sin(radio_radianes) / math.cos(lat_central_rad))
    lon_max = lon_central_rad + math.asin(math.sin(radio_radianes) / math.cos(lat_central_rad))

    # Convertir los límites de vuelta a grados
    lat_min = math.degrees(lat_min)
    lat_max = math.degrees(lat_max)
    lon_min = math.degrees(lon_min)
    lon_max = math.degrees(lon_max)

    return lat_min, lat_max, lon_min, lon_max

lat_central = -12.0464  # Latitud de Lima, Perú
lon_central = -77.0428  # Longitud de Lima, Perú
rango = calcular_rango(lat_central, lon_central)
print(f"Latitude range: {rango[0]:.6f} to {rango[1]:.6f}")
print(f"Longitude range: {rango[2]:.6f} to {rango[3]:.6f}")

import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from math import radians, sin, cos, sqrt, atan2 

def haversine(lon1, lat1, lon2, lat2):
    # Convertir grados a radianes
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Fórmula del semiverseno
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    # Radio de la Tierra en kilómetros
    r = 6371.01
    return c * r

def calcular_vulnerabilidad(gdf_mzn_carac, albergues_gdf, radio_km=1.5):
    
    for idx, albergue in albergues_gdf.iterrows():
        albergue_lat = albergue.LATITUD
        albergue_lon = albergue.LONGITUD
        
        # Calcular el rango de latitud y longitud
        lat_min, lat_max, lon_min, lon_max = calcular_rango(albergue_lat, albergue_lon, radio_km)

        # Aplicar la máscara
        mascara = (gdf_mzn_carac['latitud'] >= lat_min) & (gdf_mzn_carac['latitud'] <= lat_max) & \
                  (gdf_mzn_carac['longitud'] >= lon_min) & (gdf_mzn_carac['longitud'] <= lon_max)
        gdf_mzn_carac_mascara = gdf_mzn_carac[mascara].copy()
        # Seleccionar las manzanas con Vulnerabilidad Muy Alta para calcular su distancia
        gdf_mzn_dist = gdf_mzn_carac_mascara[gdf_mzn_carac_mascara['NIV_VULNE']=='MUY ALTA'].copy()

        # Calcular la distancia a todos las manzanas
        distancias = gdf_mzn_dist.apply(lambda manzana: haversine(albergue_lon, albergue_lat, manzana.longitud, manzana.latitud), axis=1)
        
        # Asignar la cantidad de manzanas
        albergues_gdf.at[idx, 'Manzanas'] = gdf_mzn_carac_mascara.shape[0]
        albergues_gdf.at[idx, 'M_VULNE_MUY_ALTA'] = gdf_mzn_carac_mascara[gdf_mzn_carac_mascara['NIV_VULNE']=='MUY ALTA'].shape[0]
        albergues_gdf.at[idx, 'M_VULNE_DIST'] = distancias.sum()
        #Promedio
        if distancias.empty:
            promedio = 0
        else:
            promedio = distancias.mean()
        albergues_gdf.at[idx, 'M_VULNE_DIST_PROM'] = promedio

    return albergues_gdf

albergues_vulne = albergue_completo.copy()
albergues_vulne = calcular_vulnerabilidad(gdf_mzn_carac,albergues_vulne,1)

#---5.2. Characterization by Census Blocks: Seismic Risk
def calcular_riesgo(gdf_mzn_carac, albergues_gdf, radio_km=1.5):
    
    for idx, albergue in albergues_gdf.iterrows():
        albergue_lat = albergue.LATITUD
        albergue_lon = albergue.LONGITUD
        
        # Calcular el rango de latitud y longitud
        lat_min, lat_max, lon_min, lon_max = calcular_rango(albergue_lat, albergue_lon, radio_km)

        # Aplicar la máscara
        mascara = (gdf_mzn_carac['latitud'] >= lat_min) & (gdf_mzn_carac['latitud'] <= lat_max) & \
                  (gdf_mzn_carac['longitud'] >= lon_min) & (gdf_mzn_carac['longitud'] <= lon_max)
        gdf_mzn_carac_mascara = gdf_mzn_carac[mascara].copy()
        # Seleccionar las manzanas con Vulnerabilidad Muy Alta para calcular su distancia
        gdf_mzn_dist = gdf_mzn_carac_mascara[gdf_mzn_carac_mascara['NIV_RIESGO']=='MUY ALTO'].copy()

        # Calcular la distancia a todos las manzanas
        distancias = gdf_mzn_dist.apply(lambda manzana: haversine(albergue_lon, albergue_lat, manzana.longitud, manzana.latitud), axis=1)
        
        # Asignar la cantidad de manzanas
        albergues_gdf.at[idx, 'M_RIESGO_MUY_ALTO'] = gdf_mzn_dist.shape[0]
        albergues_gdf.at[idx, 'M_RIESGO_DIST'] = distancias.sum()
        if distancias.empty:
            promedio = 0
        else:
            promedio = distancias.mean()
        albergues_gdf.at[idx, 'M_RIESGO_DIST_PROM'] = promedio

    return albergues_gdf

albergues_riesgo = albergues_vulne.copy()
albergues_riesgo = calcular_riesgo(gdf_mzn_carac,albergues_riesgo,1)

#---5.3. Characterization by Census Blocks: Population
def calcular_poblacion(gdf_mzn_carac, albergues_gdf, radio_km=1.5):
    
    for idx, albergue in albergues_gdf.iterrows():
        albergue_lat = albergue.LATITUD
        albergue_lon = albergue.LONGITUD
        
        # Calcular el rango de latitud y longitud
        lat_min, lat_max, lon_min, lon_max = calcular_rango(albergue_lat, albergue_lon, radio_km)

        # Aplicar la máscara
        mascara = (gdf_mzn_carac['latitud'] >= lat_min) & (gdf_mzn_carac['latitud'] <= lat_max) & \
                  (gdf_mzn_carac['longitud'] >= lon_min) & (gdf_mzn_carac['longitud'] <= lon_max)
        gdf_mzn_carac_mascara = gdf_mzn_carac[mascara].copy()
        
        # Asignar la cantidad de manzanas
        albergues_gdf.at[idx, 'M_POB17'] = gdf_mzn_carac_mascara.TOT_POB17.sum()

    return albergues_gdf

albergues_pob = albergues_riesgo.copy()
albergues_pob = calcular_poblacion(gdf_mzn_carac,albergues_pob,1)

#---5.4. Characterization by Census Blocks: Water Coverage
def calcular_cobertura_agua(gdf_mzn_carac, albergues_gdf, radio_km=1.5):
    
    for idx, albergue in albergues_gdf.iterrows():
        albergue_lat = albergue.LATITUD
        albergue_lon = albergue.LONGITUD
        
        # Calcular el rango de latitud y longitud
        lat_min, lat_max, lon_min, lon_max = calcular_rango(albergue_lat, albergue_lon, radio_km)

        # Aplicar la máscara
        mascara = (gdf_mzn_carac['latitud'] >= lat_min) & (gdf_mzn_carac['latitud'] <= lat_max) & \
                  (gdf_mzn_carac['longitud'] >= lon_min) & (gdf_mzn_carac['longitud'] <= lon_max)
        gdf_mzn_carac_mascara = gdf_mzn_carac[mascara].copy()
        
        # Asignar la cantidad de manzanas
        albergues_gdf.at[idx, 'M_COB_AGUA_CON'] = gdf_mzn_carac_mascara[gdf_mzn_carac_mascara['COB_AGUA']=='CON COBERTURA'].shape[0]
        albergues_gdf.at[idx, 'M_COB_AGUA_SIN'] = gdf_mzn_carac_mascara[gdf_mzn_carac_mascara['COB_AGUA']=='SIN COBERTURA'].shape[0]
        albergues_gdf.at[idx, 'M_COB_AGUA_NODATA'] = gdf_mzn_carac_mascara[gdf_mzn_carac_mascara['COB_AGUA']=='NO DATA'].shape[0]

    return albergues_gdf

albergues_agua = albergues_pob.copy()
albergues_agua = calcular_cobertura_agua(gdf_mzn_carac,albergues_agua,1)

#---5.5. Characterization by Census Blocks: Electricity Coverage

def calcular_cobertura_agua(gdf_mzn_carac, albergues_gdf, radio_km=1.5):
    
    for idx, albergue in albergues_gdf.iterrows():
        albergue_lat = albergue.LATITUD
        albergue_lon = albergue.LONGITUD
        
        # Calcular el rango de latitud y longitud
        lat_min, lat_max, lon_min, lon_max = calcular_rango(albergue_lat, albergue_lon, radio_km)

        # Aplicar la máscara
        mascara = (gdf_mzn_carac['latitud'] >= lat_min) & (gdf_mzn_carac['latitud'] <= lat_max) & \
                  (gdf_mzn_carac['longitud'] >= lon_min) & (gdf_mzn_carac['longitud'] <= lon_max)
        gdf_mzn_carac_mascara = gdf_mzn_carac[mascara].copy()
        
        # Asignar la cantidad de manzanas
        albergues_gdf.at[idx, 'M_COB_ELEC_CON'] = gdf_mzn_carac_mascara[gdf_mzn_carac_mascara['COB_ELEC']=='CON COBERTURA'].shape[0]
        albergues_gdf.at[idx, 'M_COB_ELEC_SIN'] = gdf_mzn_carac_mascara[gdf_mzn_carac_mascara['COB_ELEC']=='SIN COBERTURA'].shape[0]
        albergues_gdf.at[idx, 'M_COB_ELEC_NODATA'] = gdf_mzn_carac_mascara[gdf_mzn_carac_mascara['COB_ELEC']=='NO DATA'].shape[0]

    return albergues_gdf

albergues_elec = albergues_agua.copy()
albergues_elec = calcular_cobertura_agua(gdf_mzn_carac,albergues_elec,1)

#---5.6. Characterization by Census Blocks: Potentially Vulnerable and At-Risk Population

def calcular_poblacion_demandada(gdf_mzn_carac, albergues_gdf, radio_km=1.5):
    
    for idx, albergue in albergues_gdf.iterrows():
        albergue_lat = albergue.LATITUD
        albergue_lon = albergue.LONGITUD
        
        # Calcular el rango de latitud y longitud
        lat_min, lat_max, lon_min, lon_max = calcular_rango(albergue_lat, albergue_lon, radio_km)

        # Aplicar la máscara
        mascara = (gdf_mzn_carac['latitud'] >= lat_min) & (gdf_mzn_carac['latitud'] <= lat_max) & \
                  (gdf_mzn_carac['longitud'] >= lon_min) & (gdf_mzn_carac['longitud'] <= lon_max)
        gdf_mzn_carac_mascara = gdf_mzn_carac[mascara].copy()
        # Seleccionar las manzanas con Vulnerabilidad Muy Alta para calcular su distancia
        gdf_mzn_potencial = gdf_mzn_carac_mascara[(gdf_mzn_carac_mascara['NIV_RIESGO']=='MUY ALTO') & (gdf_mzn_carac_mascara['NIV_VULNE']=='MUY ALTA')].copy()
        
        # Asignar la cantidad de manzanas
        albergues_gdf.at[idx, 'POB_DEMAN'] = gdf_mzn_potencial.TOT_POB17.sum()

    return albergues_gdf

albergues_pob_deman = albergues_elec.copy()
albergues_pob_deman = calcular_poblacion_demandada(gdf_mzn_carac,albergues_pob_deman,1)

#---5.7. Characterization by Census Blocks: Capacity
albergues_aforo = albergues_pob_deman.copy()
albergues_aforo['AREA'] = albergues_aforo['AREA'].replace({',': ''}, regex=True).astype(float)
albergues_aforo['AFORO'] = round(albergues_aforo.AREA/3.5,0)

#---5.8. Characterization by Census Blocks: Coverage Percentage
albergues_cobertura = albergues_aforo.copy()
albergues_cobertura['COBERTURA'] = albergues_cobertura.POB_DEMAN/albergues_cobertura.AFORO

#---5.9. Characterization by Census Blocks: Distance to the Nearest Health Center
gdf_salud = gpd.read_file('centros_salud_caracterizados_lima.shp')

import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from math import radians, sin, cos, sqrt, atan2

import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from math import radians, sin, cos, sqrt, atan2

def haversine(lon1, lat1, lon2, lat2):
    # Convertir grados a radianes
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Fórmula del semiverseno
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    # Radio de la Tierra en kilómetros
    r = 6371.01
    return c * r

def calcular_distancia_hospital_mas_cercano(albergues_gdf, hospitales_gdf):
    # Crear nuevas columnas 'Dist_Hos' y 'IND_HOSP' para almacenar la distancia y el índice del hospital más cercano
    albergues_gdf['Dist_Hos'] = np.nan
    albergues_gdf['IND_HOSP'] = np.nan

    for idx, albergue in albergues_gdf.iterrows():
        albergue_lat = albergue.LATITUD
        albergue_lon = albergue.LONGITUD
        
        # Calcular la distancia a todos los hospitales y almacenar las distancias junto con sus índices
        distancias = hospitales_gdf.apply(
            lambda hospital: haversine(albergue_lon, albergue_lat, hospital.longitud, hospital.latitud), 
            axis=1
        )
        
        # Encontrar el índice del hospital con la distancia mínima
        idx_hospital_min = distancias.idxmin()
        distancia_minima = distancias.min()
        
        # Asignar la menor distancia y el índice del hospital correspondiente
        albergues_gdf.at[idx, 'Dist_Hos'] = distancia_minima
        albergues_gdf.at[idx, 'IND_HOSP'] = idx_hospital_min

    return albergues_gdf

albergues_dist_hosp = albergues_cobertura.copy()
albergues_dist_hosp = calcular_distancia_hospital_mas_cercano(albergues_dist_hosp,gdf_salud)

albergues_dist_hosp1 = albergues_dist_hosp[:2000].copy()
albergues_dist_hosp2 = albergues_dist_hosp[2000:4000].copy()
albergues_dist_hosp3 = albergues_dist_hosp[4000:5856].copy()

albergues_dist_hosp1 = calcular_distancia_hospital_mas_cercano(albergues_dist_hosp1,gdf_salud)
albergues_dist_hosp2 = albergues_cobertura.copy()
albergues_dist_hosp2 = calcular_distancia_hospital_mas_cercano(albergues_dist_hosp2[322:330],gdf_salud)
albergues_dist_hosp3 = albergues_cobertura.copy()
albergues_dist_hosp3 = calcular_distancia_hospital_mas_cercano(albergues_dist_hosp3[:2000],gdf_salud)

#---5.10. Characterization by Census Blocks: Maximization of Distance to Health Centers
albergues_dist_hosp['MAX_DIST_H'] = 1/albergues_dist_hosp['Dist_Hos']
albergues_dist_hosp=albergues_dist_hosp.reset_index()

#---5.11. Characterization by Census Blocks: Distance to the Nearest Census Block with Water Coverage
def calcular_dist_cob_agua(gdf_mzn_carac, albergues_gdf, radio_km=1.5):
    
    for idx, albergue in albergues_gdf.iterrows():
        albergue_lat = albergue.LATITUD
        albergue_lon = albergue.LONGITUD
        
        # Calcular el rango de latitud y longitud
        lat_min, lat_max, lon_min, lon_max = calcular_rango(albergue_lat, albergue_lon, radio_km)

        # Aplicar la máscara
        mascara = (gdf_mzn_carac['latitud'] >= lat_min) & (gdf_mzn_carac['latitud'] <= lat_max) & \
                  (gdf_mzn_carac['longitud'] >= lon_min) & (gdf_mzn_carac['longitud'] <= lon_max)
        gdf_mzn_carac_mascara = gdf_mzn_carac[mascara].copy()
        # Seleccionar las manzanas con Vulnerabilidad Muy Alta para calcular su distancia
        gdf_mzn_dist = gdf_mzn_carac_mascara[gdf_mzn_carac_mascara['COB_AGUA']=='CON COBERTURA'].copy()

        # Calcular la distancia a todos las manzanas
        distancias = gdf_mzn_dist.apply(lambda manzana: haversine(albergue_lon, albergue_lat, manzana.longitud, manzana.latitud), axis=1)
        
        # Asignar la cantidad de manzanas
        if distancias.empty:
            albergues_gdf.at[idx, 'DIST_COB_A'] = 1 #Restricción de DIST_COB_A > 0.5
            albergues_gdf.at[idx, 'DIST_COB_A_max'] = 1 #Restricción de DIST_COB_A > 0.5
        else:
            albergues_gdf.at[idx, 'DIST_COB_A'] = distancias.min()
            albergues_gdf.at[idx, 'DIST_COB_A_max'] = distancias.max()

    return albergues_gdf

albergues_dist_cob_agua = calcular_dist_cob_agua(gdf_mzn_carac,albergues_dist_cob_agua,1)
print('Shelters without a water source within 500 meters:',albergues_dist_cob_agua[(albergues_dist_cob_agua['DIST_COB_A']>0.5)].shape[0])

#6. DOWNLOAD FINAL DATABASE

albergues_elec.to_excel('Albergues_completo_caracterizado.xlsx', index=False)

#Additional: Data for Objective Functions
df_albergue = pd.read_excel('Albergues_completo_caracterizado.xlsx')
df_albergue['VULNE_NORM'] = (df_albergue['M_VULNE_DIST'] - df_albergue['M_VULNE_DIST'].min()) / (df_albergue['M_VULNE_DIST'].max() - df_albergue['M_VULNE_DIST'].min())
df_albergue['RIES_NORM'] = (df_albergue['M_RIESGO_DIST'] - df_albergue['M_RIESGO_DIST'].min()) / (df_albergue['M_RIESGO_DIST'].max() - df_albergue['M_RIESGO_DIST'].min())

import numpy as np
df_albergue['IND_VULNE'] = (1 - df_albergue['VULNE_NORM']) * (1 - np.exp(-0.5 * df_albergue['Manzanas']))
df_albergue['IND_RIESGO'] = (1 - df_albergue['RIES_NORM']) * (1 - np.exp(-0.5 * df_albergue['Manzanas']))

df_albergue.to_excel('Albergues_completo_caracterizado_v2.xlsx', index=False)
























