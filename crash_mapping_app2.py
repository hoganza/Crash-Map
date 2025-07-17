import pandas as pd
import folium
from folium.plugins import HeatMap

# === Load Excel Data ===
file_path = "Segment 5 Accident Data.xlsx"  # Update this if needed
df = pd.read_excel(file_path, skiprows=1)

# === Select and Rename Relevant Columns ===
df = df[['Date', 'Direction', 'Mile Post', 'Injury/Property Damage']]
df.columns = ['Date', 'Direction', 'MilePost', 'Severity']

# === Clean Data ===
df = df.dropna(subset=['MilePost', 'Severity'])
df['MilePost'] = pd.to_numeric(df['MilePost'], errors='coerce')
df = df.dropna(subset=['MilePost'])
df['Severity'] = df['Severity'].str.lower().str.strip()
df['Direction'] = df['Direction'].str.upper().str.strip()

# === Approximate Latitude and Longitude from MilePost ===
# I-25: Johnstown (MP 250, ~40.185, -104.981) to Mead (MP 243, ~40.336, -104.993)
mile_min, mile_max = 243, 250
lat_min, lat_max = 40.336, 40.185
lon_min, lon_max = -104.993, -104.981

df['Latitude'] = lat_max + (lat_min - lat_max) * (mile_max - df['MilePost']) / (mile_max - mile_min)
df['Longitude'] = lon_max + (lon_min - lon_max) * (mile_max - df['MilePost']) / (mile_max - mile_min)

# === Define Severity Colors ===
severity_colors = {
    'property damage': 'blue',
    'injury': 'orange',
    'fatality': 'red',
    'both': 'purple'
}

# === Create Maps ===
center = [df['Latitude'].mean(), df['Longitude'].mean()]
severity_map = folium.Map(location=center, zoom_start=12)
heat_map = folium.Map(location=center, zoom_start=12)
nb_map = folium.Map(location=center, zoom_start=12)
sb_map = folium.Map(location=center, zoom_start=12)

# === Add Severity Markers ===
for _, row in df.iterrows():
    color = severity_colors.get(row['Severity'], 'gray')
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=6,
        popup=f"{row['Severity'].title()} - MP {row['MilePost']}",
        color=color,
        fill=True,
        fill_color=color
    ).add_to(severity_map)

# === Heat Maps ===
HeatMap(data=df[['Latitude', 'Longitude']].values).add_to(heat_map)

nb_df = df[df['Direction'] == 'NB']
sb_df = df[df['Direction'] == 'SB']

HeatMap(data=nb_df[['Latitude', 'Longitude']].values).add_to(nb_map)
HeatMap(data=sb_df[['Latitude', 'Longitude']].values).add_to(sb_map)

# === Save Maps ===
severity_map.save("severity_map.html")
heat_map.save("heat_map.html")
nb_map.save("nb_heatmap.html")
sb_map.save("sb_heatmap.html")

print("Maps saved successfully.")
