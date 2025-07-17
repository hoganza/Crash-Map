import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("🚗 Crash Map Generator")

uploaded_file = st.file_uploader("Upload your Excel file (.xlsx)", type="xlsx")

# ----------------------------------------
# 🚩 Severity-to-Color Mapping
def get_color(severity):
    if severity == "PDO":
        return "green"
    elif severity == "INJ":
        return "orange"
    elif severity == "FAT":
        return "red"
    return "gray"

# ----------------------------------------
# 📍 Mile Post to Lat/Lon Estimator
def estimate_lat_lon_from_milepost(mp):
    try:
        mp = float(mp)
    except:
        return (None, None)

    # Anchor points along I-25 Segment 5 (approximate)
    mp_start, lat_start, lon_start = 241.0, 39.500, -104.990
    mp_end, lat_end, lon_end = 250.0, 39.650, -104.980

    ratio = (mp - mp_start) / (mp_end - mp_start)
    lat = lat_start + ratio * (lat_end - lat_start)
    lon = lon_start + ratio * (lon_end - lon_start)
    return lat, lon

# ----------------------------------------
# 📄 Load Segment 5 Excel Crash Data
@st.cache_data
def load_segment_5_data(excel_file):
    df_raw = pd.read_excel(excel_file, sheet_name="Summary", header=None)
    df_raw.columns = df_raw.iloc[0]
    df = df_raw[1:].reset_index(drop=True)

    df = df.rename(columns={
        "Date": "Date",
        "Direction": "Veh1 Dir",
        "Injury/Property Damage": "Severity"
    })

    df = df.dropna(axis=1, how='all')

    # Generate lat/lon from mile post
    df["Mile Post"] = pd.to_numeric(df["Mile Post"], errors='coerce')
    df[["Latitude", "Longitude"]] = df["Mile Post"].apply(
        lambda mp: pd.Series(estimate_lat_lon_from_milepost(mp))
    )

    df = df.dropna(subset=["Date", "Severity", "Latitude", "Longitude"])
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df["Veh1 Dir"] = df["Veh1 Dir"].astype(str).str.strip().str.upper()

    df["Weight"] = df["Severity"].map({
        "FAT": 3, "INJ": 2, "PDO": 1,
        "Property Damage": 1, "Injury": 2, "Both": 2
    })

    return df

# ----------------------------------------
# 📦 Upload & Load Data
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df = df.dropna(subset=["Latitude", "Longitude", "Date", "Severity"])
        df["Date"] = pd.to_datetime(df["Date"])
        df["Veh1 Dir"] = df["Veh1 Dir"].astype(str).str.strip().str.upper()
        df["Weight"] = df["Severity"].map({"FAT": 3, "INJ": 2, "PDO": 1})
    except:
        df = load_segment_5_data(uploaded_file)

    # Determine directions
    north_dirs = {"N", "NE", "NW", "NB"}
    south_dirs = {"S", "SE", "SW", "SB"}
    df["Is_Northbound"] = df["Veh1 Dir"].isin(north_dirs)
    df["Is_Southbound"] = df["Veh1 Dir"].isin(south_dirs)

    center = [df["Latitude"].mean(), df["Longitude"].mean()]

    # ----------------------------------------
    # 📍 Marker Map
    def make_severity_map(data):
        m = folium.Map(location=center, zoom_start=11)
        for _, row in data.iterrows():
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=6,
                color=get_color(row["Severity"]),
                fill=True,
                fill_opacity=0.8,
                popup=f"{row['Date'].date()} | {row['Severity']} | Dir: {row['Veh1 Dir']}"
            ).add_to(m)
        return m

    # 🔥 Heatmap
    def make_heatmap(data):
        m = folium.Map(location=center, zoom_start=11)
        heat_data = [[row["Latitude"], row["Longitude"], row["Weight"]] for _, row in data.iterrows()]
        HeatMap(heat_data, radius=10, blur=15).add_to(m)
        return m

    # ----------------------------------------
    # 📊 Streamlit Visualizations

    st.subheader("🔴 Severity Map (color-coded)")
    st_folium(make_severity_map(df), width=700, height=500)

    st.subheader("🔥 Full Heatmap")
    st_folium(make_heatmap(df), width=700, height=500)

    st.subheader("⬆️ Northbound Map (Markers)")
    north_df = df[df["Is_Northbound"]].dropna(subset=["Latitude", "Longitude"])
    if not north_df.empty:
        st_folium(make_severity_map(north_df), width=700, height=500)
        st.subheader("🔥 Northbound Heatmap")
        st_folium(make_heatmap(north_df), width=700, height=500)
    else:
        st.info("No Northbound crashes found.")

    st.subheader("⬇️ Southbound Map (Markers)")
    south_df = df[df["Is_Southbound"]].dropna(subset=["Latitude", "Longitude"])
    if not south_df.empty:
        st_folium(make_severity_map(south_df), width=700, height=500)
        st.subheader("🔥 Southbound Heatmap")
        st_folium(make_heatmap(south_df), width=700, height=500)
    else:
        st.info("No Southbound crashes found.")
