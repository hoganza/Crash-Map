import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import io

st.set_page_config(layout="wide")
st.title("🚗 Crash Map Generator")

uploaded_file = st.file_uploader("Upload your Excel file (.xlsx)", type="xlsx")

# Color helper
def get_color(severity):
    if severity == "PDO":
        return "green"
    elif severity == "INJ":
        return "orange"
    elif severity == "FAT":
        return "red"
    return "gray"

# 🔁 Format-Aware Data Loader
def load_crash_data(file):
    df_raw = pd.read_excel(file, header=None)

    # Check if this is Segment 5 format
    if "I-25 Segment 5 Accident History" in str(df_raw.iloc[0, 0]):
        # Skip the title row and use the second row as header
        df = pd.read_excel(file, header=1, skiprows=[0])

        # Rename relevant columns for consistency
        df = df.rename(columns={
            "Injury/Property Damage": "Severity",
            "Mile Post": "Milepost",
            "Brief Discription": "Description"
        })

        # 🔍 Debug output
        st.write("Segment 5 columns:", df.columns.tolist())

        # Ensure required columns exist
        if "Date" not in df.columns or "Severity" not in df.columns or "Direction" not in df.columns:
            st.error("Missing one of: 'Date', 'Severity', or 'Direction'. Please check the uploaded file.")
            return pd.DataFrame()

        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')

        # Map severities
        severity_map = {
            "Property Damage": "PDO",
            "Injury": "INJ",
            "Both": "INJ",
            "Fatality": "FAT"
        }
        df["Severity"] = df["Severity"].map(severity_map).fillna("PDO")

        # Placeholder location (can be replaced with extracted lat/lon later)
        df["Latitude"] = 40.3
        df["Longitude"] = -104.98
        df["Veh1 Dir"] = df["Direction"].astype(str).str.strip().str.upper()

    else:
        # Assume original format
        df = pd.read_excel(file)

    return df

if uploaded_file:
    df = load_crash_data(uploaded_file)

    if df.empty:
        st.warning("No valid data to display.")
    else:
        required_columns = {"Latitude", "Longitude", "Date", "Severity", "Veh1 Dir"}
        if not required_columns.issubset(df.columns):
            st.error(f"Missing required columns: {required_columns - set(df.columns)}")
        else:
            df = df.dropna(subset=["Latitude", "Longitude", "Date", "Severity"])
            df["Date"] = pd.to_datetime(df["Date"])
            df["Veh1 Dir"] = df["Veh1 Dir"].astype(str).str.strip().str.upper()
            df["Weight"] = df["Severity"].map({"FAT": 3, "INJ": 2, "PDO": 1})

            # Direction logic
            north_dirs = {"N", "NE", "NW", "NB"}
            south_dirs = {"S", "SE", "SW", "SB"}
            df["Is_Northbound"] = df["Veh1 Dir"].isin(north_dirs)
            df["Is_Southbound"] = df["Veh1 Dir"].isin(south_dirs)

            # Map center
            center = [df["Latitude"].mean(), df["Longitude"].mean()]

            # Create maps
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

            def make_heatmap(data):
                m = folium.Map(location=center, zoom_start=11)
                heat_data = [[row["Latitude"], row["Longitude"], row["Weight"]] for _, row in data.iterrows()]
                HeatMap(heat_data, radius=10, blur=15).add_to(m)
                return m

            # Show maps
            st.subheader("Severity Map")
            severity_map = make_severity_map(df)
            st_folium(severity_map, width=1200)

            st.subheader("Heatmap")
            heatmap = make_heatmap(df)
            st_folium(heatmap, width=1200)
