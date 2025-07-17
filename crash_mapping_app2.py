import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.title("🚗 Crash Severity & Heatmap Viewer")

# 1️⃣ Upload Excel file
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
# 2️⃣ Upload CDOT milepoints shapefile (ZIP containing .shp, .dbf, etc.)
milepoints_file = st.file_uploader("Upload CDOT milepoints shapefile (ZIP)", type=["zip"])

if uploaded_file and milepoints_file:
    # Load crash data
    df = pd.read_excel(uploaded_file, skiprows=1)
    df = df[['Date', 'Direction', 'Mile Post', 'Injury/Property Damage']]
    df.columns = ['Date', 'Direction', 'MilePost', 'Severity']
    df.dropna(subset=['MilePost', 'Severity'], inplace=True)
    df['MilePost'] = pd.to_numeric(df['MilePost'], errors='coerce')
    df['Severity'] = df['Severity'].str.lower().str.strip()
    df['Direction'] = df['Direction'].str.upper().str.strip()

    # Load milepoints layer
    import tempfile, zipfile, os
    tmp = tempfile.TemporaryDirectory()
    with zipfile.ZipFile(milepoints_file, 'r') as z:
        z.extractall(tmp.name)
    mp = gpd.read_file(tmp.name)
    # Filter to I‑25 in Colorado
    mp = mp[(mp['route'] == 'I 25') & (mp['state'] == 'CO')]

    # For each crash, find nearest milepoint & use its coordinates
    mp = mp.set_geometry('geometry').to_crs(epsg=4326)
    df['lon'] = None
    df['lat'] = None
    idx_s = mp.sindex
    for i, row in df.iterrows():
        # find nearest by milepost integer
        candidates = mp.iloc[(mp['milepost'] - row['MilePost']).abs().argsort()[:5]]
        nearest = candidates.geometry.distance(gpd.points_from_xy([row['MilePost']]*len(candidates), [0]*len(candidates)))  # dummy geometry
        pick = candidates.iloc[0]  # best guess by numeric
        df.at[i, 'lon'] = pick.geometry.x
        df.at[i, 'lat'] = pick.geometry.y

    # Color mapping for severity
    colors = {'property damage only': 'green', 'injury': 'yellow', 'fatality': 'red'}

    # Create four map tabs
    tabs = st.tabs(["📍 Severity Map", "🔥 Heat Map", "⬆️ Northbound", "⬇️ Southbound"])
    for tab, title in zip(tabs, ["sev", "all", "nb", "sb"]):
        with tab:
            m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=12)
            if title == "sev":
                for _, r in df.iterrows():
                    folium.CircleMarker(
                        location=[r['lat'], r['lon']],
                        radius=6,
                        color=colors.get(r['Severity'], 'gray'),
                        fill=True,
                        fill_color=colors.get(r['Severity'], 'gray'),
                        popup=f"{r['Severity'].title()} – MP {r['MilePost']}"
                    ).add_to(m)
            else:
                subset = df if title == "all" else df[df['Direction'] == ('NB' if title=='nb' else 'SB')]
                HeatMap(data=subset[['lat','lon']].values, radius=15).add_to(m)
            st_folium(m, width=700)
else:
    st.warning("👆 Please upload both the crash Excel file and the milepoints shapefile.")
