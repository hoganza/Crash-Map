import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("🚗 Crash Severity & Heatmap Viewer")

# === File Uploads ===
uploaded_file = st.file_uploader("Upload Segment 5 Accident Excel file", type=["xlsx"])
milepoints_geojson = st.file_uploader("Upload Milepoints GeoJSON file", type=["geojson"])

if uploaded_file and milepoints_geojson:
    # === Load Crash Data ===
    df = pd.read_excel(uploaded_file, skiprows=1)
    df = df[['Date', 'Direction', 'Mile Post', 'Injury/Property Damage']]
    df.columns = ['Date', 'Direction', 'MilePost', 'Severity']
    df = df.dropna(subset=['MilePost', 'Severity'])
    df['MilePost'] = pd.to_numeric(df['MilePost'], errors='coerce')
    df = df.dropna(subset=['MilePost'])
    df['Severity'] = df['Severity'].str.lower().str.strip()
    df['Direction'] = df['Direction'].str.upper().str.strip()

    # === Load GeoJSON file and filter to I-25 (025A) only ===
    gdf = gpd.read_file(milepoints_geojson)
    gdf = gdf[(gdf.geometry.type == "Point") & (gdf["ROUTE"] == "025A")]
    gdf['RoundedMile'] = gdf['REF_PT'].round().astype(int)

    # Round crash mileposts
    df['RoundedMile'] = df['MilePost'].round().astype(int)

    # Fix for non-unique milepoints
    lookup = gdf.drop_duplicates('RoundedMile').set_index('RoundedMile')
    df['Latitude'] = df['RoundedMile'].map(lookup['geometry'].apply(lambda g: g.y))
    df['Longitude'] = df['RoundedMile'].map(lookup['geometry'].apply(lambda g: g.x))

    # Drop unmatched
    df = df.dropna(subset=['Latitude', 'Longitude'])

    if df.empty:
        st.error("❌ No crash locations matched any 025A milepoints. Please check milepost ranges.")
        st.stop()

    st.success(f"✅ {len(df)} crash locations mapped on I-25 (025A).")

    # === Severity Color Mapping ===
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
    st.info("📂 Please upload both the Excel crash file and the Milepoints GeoJSON file.")
