import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import tempfile, zipfile

st.set_page_config(layout="wide")
st.title("🚗 Crash Severity & Heatmap Viewer")

# === File Uploads ===
uploaded_file = st.file_uploader("Upload Segment 5 Accident Excel file", type=["xlsx"])
milepoints_zip = st.file_uploader("Upload CDOT Milepoints Shapefile (.zip)", type=["zip"])

if uploaded_file and milepoints_zip:
    # === Load Crash Data ===
    df = pd.read_excel(uploaded_file, skiprows=1)
    df = df[['Date', 'Direction', 'Mile Post', 'Injury/Property Damage']]
    df.columns = ['Date', 'Direction', 'MilePost', 'Severity']
    df = df.dropna(subset=['MilePost', 'Severity'])
    df['MilePost'] = pd.to_numeric(df['MilePost'], errors='coerce')
    df = df.dropna(subset=['MilePost'])
    df['Severity'] = df['Severity'].str.lower().str.strip()
    df['Direction'] = df['Direction'].str.upper().str.strip()

    # === Extract and Load Milepoints Shapefile ===
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(milepoints_zip, "r") as zip_ref:
            zip_ref.extractall(tmpdir)
        mp = gpd.read_file(tmpdir)

    # Automatically find likely column names
    route_col = next((c for c in mp.columns if 'route' in c.lower()), None)
    state_col = next((c for c in mp.columns if 'state' in c.lower()), None)
    mile_col = next((c for c in mp.columns if 'mile' in c.lower()), None)

    if not all([route_col, state_col, mile_col]):
        st.error("❌ Could not detect required columns in shapefile: 'route', 'state', 'milepost'")
        st.stop()

    # Filter for I-25 in Colorado
    mp = mp[(mp[route_col].str.upper() == 'I 25') & (mp[state_col].str.upper() == 'CO')]
    mp = mp.to_crs(epsg=4326)

    # Match mileposts to coordinates
    df['Latitude'] = None
    df['Longitude'] = None

    for i, row in df.iterrows():
        subset = mp.loc[(mp[mile_col] - row['MilePost']).abs().sort_values().index]
        if not subset.empty:
            geom = subset.iloc[0].geometry
            df.at[i, 'Latitude'] = geom.y
            df.at[i, 'Longitude'] = geom.x

    df = df.dropna(subset=['Latitude', 'Longitude'])

    # === Color Mapping ===
    severity_colors = {
        'property damage': 'green',
        'property damage only': 'green',
        'injury': 'yellow',
        'fatality': 'red',
        'both': 'orange'
    }

    # === Map Tabs ===
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
        nb_df = df[df['Direction'] == 'NB']
        m3 = folium.Map(location=[nb_df['Latitude'].mean(), nb_df['Longitude'].mean()], zoom_start=12)
        HeatMap(data=nb_df[['Latitude', 'Longitude']].values).add_to(m3)
        st_folium(m3, width=700)

    with tab4:
        sb_df = df[df['Direction'] == 'SB']
        m4 = folium.Map(location=[sb_df['Latitude'].mean(), sb_df['Longitude'].mean()], zoom_start=12)
        HeatMap(data=sb_df[['Latitude', 'Longitude']].values).add_to(m4)
        st_folium(m4, width=700)

else:
    st.info("Please upload both the Excel crash file and the CDOT milepoints ZIP shapefile.")
