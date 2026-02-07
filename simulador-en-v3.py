import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
#from deap import base, creator, tools, algorithms
import plotly.express as px
import ast

from functions import show_map, load_shelters

#Seleccionar los albergues
def filtrar_albergues_por_ids(pareto_df, albergues_df, idx,
                              shelter_col='Shelter_Indices',
                              id_col='ID_ALBERGUE'):
    # Obtener string con los IDs
    seleccion = pareto_df.loc[idx, shelter_col]

    # String → array NumPy de IDs
    seleccion = np.fromstring(seleccion.strip('[]'), sep=',', dtype=int)

    # Filtrar dataframe completo (NO se retorna el booleano)
    return albergues_df[albergues_df[id_col].isin(seleccion)].copy()

# Streamlit Interface
st.title("Shelter Location Simulator")

# Dropdown to select danger level
levels = ["Mild", "Moderate", "Severe", "Very Strong","Disastrous"]
selected_level = st.sidebar.selectbox("Select the danger level", levels)

if selected_level == "Mild":  
    pareto_df = pd.read_csv('pareto_front_leve_full.csv')
    
elif selected_level == "Moderate":
    pareto_df = pd.read_csv('pareto_front_moderado_full.csv')
    
elif selected_level == "Severe":
    pareto_df = pd.read_csv('pareto_front_fuerte_full.csv')
    
elif selected_level == "Very Strong":
    pareto_df = pd.read_csv('pareto_front_muy fuerte_full.csv')

elif selected_level == "Disastrous":
    pareto_df = pd.read_csv('pareto_front_desastroso_full.csv')

albergues_df = load_shelters()

pareto_df['Shelter_Indices'] = pareto_df['Shelter_Indices'].apply(ast.literal_eval)
pareto_df = pareto_df.reset_index()

shelter_data = filtrar_albergues(pareto_df,albergues_df,0)

# Dropdown to select the district
districts = ["All districts"] + sorted(shelter_data['DISTRITO'].unique())
selected_district = st.sidebar.selectbox("Select a district", districts)

# Sidebar: Pareto Front
st.sidebar.header("Pareto Front")

# Selection variable
selected_id = st.sidebar.selectbox("Select a solution", pareto_df['index'])

shelter_data = filtrar_albergues(pareto_df,albergues_df,selected_id)


# Add a color column to highlight the selected solution
pareto_df['Color'] = pareto_df['index'].apply(lambda x: 'Selected' if x == selected_id else 'Not selected')

translated_df = pareto_df.rename(columns={
            'Objective_1 (Distance)': 'Distance between shelters',
            'Objective_2 (Population Coverage)': 'Seismic vulnerability and risk',
            'Objective_3 (Risk/Vulnerability Coverage)': 'Demanded population'
        })

# Create the 3D Pareto Front plot
fig = px.scatter_3d(
        translated_df,
            x='Distance between shelters',
            y='Seismic vulnerability and risk',
            z='Demanded population',
            color='Color',
            color_discrete_map={'Selected': 'red', 'Not selected': 'blue', 'Municipality of Lima': 'black'},
            custom_data=['index'],
            text='index',
            height=500,
            labels={
                'Distance between shelters': 'f1(Distance)',
                'Seismic vulnerability and risk': 'f2(Vulnerability)',
                'Demanded population': 'f3(Coverage)'
            }
        )

fig.update_layout(
            scene=dict(
                xaxis_title='f1(Distance)',
                yaxis_title='f2(Vulnerability)',
                zaxis_title='f3(Coverage)'
            ),
            showlegend=False
        )

fig.update_traces(
    hovertemplate="<br>".join([
        "Solution: %{customdata[0]}",  # Show Index on hover
        "Distance between shelters: %{x}",
        "Seismic vulnerability and risk: %{y}",
        "Demanded population: %{z}"  
    ])
)

st.sidebar.plotly_chart(fig)

st.sidebar.markdown("""
        **f1**: Distance between shelters  
        **f2**: Seismic vulnerability and risk  
        **f3**: Demanded population
        """)

# Get the selected solution
selected_solution = pareto_df[pareto_df['index'] == selected_id]

# Filter shelters based on selected solution
selected_shelters = shelter_data.copy()

# Display the map with the selected shelters
st.subheader("Map of Selected Shelters")

if selected_district != "All districts":
    selected_shelters = selected_shelters[selected_shelters['DISTRITO'] == selected_district]

# Count of shelters
#st.write(f"Number of shelters: {selected_shelters.shape[0]}")
st.write(f"Number of shelters: {shelter_data.shape[0]}")

#average_distance_water = selected_shelters['DIST_AGUA'].mean() 
#average_distance_hospital = selected_shelters['DIST_HOSP'].mean()
#total_population = selected_shelters['POB_DEMAN'].sum()
#total_districts = selected_shelters['DISTRITO'].nunique()

avg_water = shelter_data['DIST_AGUA'].mean()
avg_hospital = shelter_data['DIST_HOSP'].mean()
total_pop = shelter_data['POB_DEMAN'].sum()
total_dist = shelter_data['DISTRITO'].nunique()


# Create a DataFrame to display statistics
stats_df = pd.DataFrame({
            "Statistic": [
                "Average distance to hospitals (km)",
                "Average distance to water (km)",
                "Vulnerable population",
                "Number of districts with shelters (out of 43)"
            ],
            "Value": [
                f"{avg_hospital:.2f} km" if avg_hospital >= 0 else "-",
                f"{avg_water:.2f} km" if avg_water >= 0 else "-",
                f"{total_pop:,} people" if total_pop >= 0 else "-",
                f"{total_dist}" if total_dist >= 0 else "-"
            ]
        })

st.dataframe(stats_df, hide_index=True, use_container_width=True)

st.markdown("""
        - 🔵 **Blue points**: Shelters selected by the algorithm.
        - 🟢 **Green points**: Shelters selected by both the algorithm and the Municipality of Lima.
        """)

show_map(selected_shelters)

district_summary = (
    shelter_data
    .groupby('DISTRITO')
    .size()
    .reset_index(name='Number of shelters')
)

st.dataframe(district_summary, hide_index=True, use_container_width=True)
