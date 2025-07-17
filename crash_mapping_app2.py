import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.title("🚗 Crash Severity & Heatmap Viewer")
st.markdown("Upload your Segment 5 Accident Excel file to generate maps.")

# Upload file
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file:
    # Load the Excel data
    df = pd.read_excel(uploaded_file, skiprows=1)
    df = df[['Date', 'Direction', 'Mile Post', 'Injury/Property Damage']]
    df.columns = ['Date', 'Direction', 'MilePost', 'Severity']

    # Clean data
    df = df.dropna(subset=['MilePost', 'Severity'])
    df['MilePost'] = pd.to_numeric(df['MilePost'], errors='coerce')
    df = df.dropna(subset=['MilePost'])
    df['Severity'] = df['Severity'].str.lower().str.strip()
    df['Direction'] = df['Direction'].str.upper().str.strip()

    # Convert MilePost to lat/lon (approximation for I-25 Segment 5)
    mile_min, mile_max = 243, 250
    lat_min, lat_max = 40.336, 40.185
    lon_min, lon_max = -104.993, -104.981

    df['Latitude'] = lat_max + (lat_min - lat_max) * (mile_max - df['MilePost']) / (mile_max - mile_min)
    df['Longitude'] = lon_max + (lon_min - lon_max) * (mile_max - df['MilePost']) / (mile_max - mile_min)

    # Map Severity to Colors
    severity_colors = {
        'property damage': 'blue',
        'injury': 'orange',
        'fatality': 'red',
        'both': 'purple'
    }

    # Create map tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📍 Severity Map", "🔥 Heat Map", "⬆️ Northbound", "⬇️ Southbound"])

    with tab1:
        m1 = folium.Map(location=[df['Latitude'].mean(), df['Longitude'].mean()], zoom_start=12)
        for _, row in df.iterrows():
            color = severity_colors.get(row['Severity'], 'gray')
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=6,
                popup=f"{row['Severity'].title()} - MP {row['MilePost']}",
                color=color,
                fill=True,
                fill_color=color
            ).add_to(m1)
        st_folium(m1, width=700)

    with tab2:
        m2 = folium.Map(location=[df['Latitude'].mean(), df['Longitude'].mean()], zoom_start=12)
        HeatMap(data=df[['Latitude', 'Longitude']].values).add_to(m2)
        st_folium(m2, width=700)

    with tab3:
        m3 = folium.Map(location=[df['Latitude'].mean(), df['Longitude'].mean()], zoom_start=12)
        nb_df = df[df['Direction'] == 'NB']
        HeatMap(data=nb_df[['Latitude', 'Longitude']].values).add_to(m3)
        st_folium(m3, width=700)

    with tab4:
        m4 = folium.Map(location=[df['Latitude'].mean(), df['Longitude'].mean()], zoom_start=12)
        sb_df = df[df['Direction'] == 'SB']
        HeatMap(data=sb_df[['Latitude', 'Longitude']].values).add_to(m4)
        st_folium(m4, width=700)

else:
    st.warning("👆 Please upload a file to begin.")
