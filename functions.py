import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static

def load_shelters():
    return pd.read_excel("shelters_lima.xlsx")
    #return pd.read_excel("albergues_select_nsga.xlsx")

def build_popup(row):
    return f"""
    <table style="width:230px; border-collapse: collapse; font-size:12px">
        <tr style="border-bottom:1px solid #ddd">
            <th align="left" style="padding:4px">District</th>
            <td style="padding:4px">{row['DISTRITO']}</td>
        </tr>
        <tr style="border-bottom:1px solid #ddd">
            <th align="left" style="padding:4px">Shelter</th>
            <td style="padding:4px">{row['ALBERGUE']}</td>
        </tr>
        <tr style="border-bottom:1px solid #ddd">
            <th align="left" style="padding:4px">Capacity</th>
            <td style="padding:4px">{row['AFORO']}</td>
        </tr>
        <tr style="border-bottom:1px solid #ddd">
            <th align="left" style="padding:4px">Vulnerable population covered</th>
            <td style="padding:4px">{row['POB_DEMAN']}</td>
        </tr>
        <tr>
            <th align="left" style="padding:4px">Selected by</th>
            <td style="padding:4px">{'Municipality' if row['ALBERGUE_MUNI'] == 1 else 'NSGA-III'}</td>
        </tr>
    </table>
    """


def show_map(selected_shelters):
    m = folium.Map(location=[-12.0464, -77.0428], zoom_start=10)
    
    municipality = folium.FeatureGroup(name='Municipality of Lima')
    nsga = folium.FeatureGroup(name='Algorithm Selection')

    for _, albergue in selected_shelters.iterrows():
        popup_text = build_popup(albergue)

        if albergue['ALBERGUE_MUNI'] == 1:
            # Puntos Municipalidad
            folium.CircleMarker(
                location=[albergue['LATITUD'], albergue['LONGITUD']],
                radius=5,
                color='green',
                fill=True,
                fill_color='green',
                fill_opacity=0.7,
                popup=popup_text
            ).add_to(municipality)
        else:
            # Puntos NSGA-II
            folium.CircleMarker(
                location=[albergue['LATITUD'], albergue['LONGITUD']],
                radius=3,
                color='blue',
                fill=True,
                fill_color='blue',
                fill_opacity=0.7,
                popup=popup_text
            ).add_to(nsga)

    municipality.add_to(m)
    nsga.add_to(m)
    folium.LayerControl(position='topright').add_to(m)
    folium_static(m)