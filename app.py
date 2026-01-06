import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium import plugins
import requests
import polyline
from datetime import datetime, timedelta
import numpy as np
import math

st.set_page_config(layout="wide", page_title="Logistics Simulation")

if "VALHALLA_URL" in st.secrets:
    base_url = st.secrets["VALHALLA_URL"].rstrip('/')
    if not base_url.endswith("/route"):
        VALHALLA_URL = f"{base_url}/route"
    else:
        VALHALLA_URL = base_url
else:
    VALHALLA_URL = "http://localhost:8002/route"

PORT_LOCATIONS = {
    'SEMARANG': {'lat': -6.950669, 'lon': 110.424167}, 
    'SMG': {'lat': -6.950669, 'lon': 110.424167},
    'JAKARTA': {'lat': -6.101831, 'lon': 106.883389},
    'JKT': {'lat': -6.101831, 'lon': 106.883389},
    'SURABAYA': {'lat': -7.197985, 'lon': 112.733791},
    'SBY': {'lat': -7.197985, 'lon': 112.733791},
    'SAMARINDA': {'lat': -0.575588, 'lon': 117.206760},
    'SDA': {'lat': -0.575588, 'lon': 117.206760},
    'MEDAN': {'lat': 3.718306, 'lon': 98.665792},
    'MAKASSAR': {'lat': -5.118228, 'lon': 119.421711},
    'MKS': {'lat': -5.118228, 'lon': 119.421711},
    'BALIKPAPAN': {'lat': -1.265386, 'lon': 116.831200},
    'BPN': {'lat': -1.265386, 'lon': 116.831200},
    'PONTIANAK': {'lat': -0.022662, 'lon': 109.333010},
    'PNK': {'lat': -0.022662, 'lon': 109.333010},
    'JAYAPURA': {'lat': -2.533036, 'lon': 140.713653},
    'JYP': {'lat': -2.533036, 'lon': 140.713653},
    'KENDARI': {'lat': -3.966901, 'lon': 122.288614},
    'KDR': {'lat': -3.966901, 'lon': 122.288614},
    'PALEMBANG': {'lat': -2.976074, 'lon': 104.775431},
    'PLM': {'lat': -2.976074, 'lon': 104.775431},
    'PANJANG': {'lat': -5.467882, 'lon': 105.316885},
    'LPG': {'lat': -5.467882, 'lon': 105.316885},
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def interpolate_points(path_coords, interval_km=0.2):
    dense_path = []
    if not path_coords: return []
    
    dense_path.append(path_coords[0])
    
    for i in range(1, len(path_coords)):
        start = path_coords[i-1]
        end = path_coords[i]
        
        dist = haversine(start[0], start[1], end[0], end[1])
        
        if dist > interval_km:
            num_points = int(dist / interval_km)
            for j in range(1, num_points + 1):
                fraction = j / (num_points + 1)
                new_lat = start[0] + (end[0] - start[0]) * fraction
                new_lon = start[1] + (end[1] - start[1]) * fraction
                dense_path.append([new_lat, new_lon])
        
        dense_path.append(end)
        
    return dense_path

@st.cache_data(show_spinner=False)
def get_route_shape(points):
    backup_shape = [[p['lat'], p['lon']] for p in points]

    payload = {"locations": points, "costing": "auto", "units": "km"}
    
    headers = {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
        "User-Agent": "StreamlitApp"
    }
    
    try:
        response = requests.post(VALHALLA_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                full_shape = []
                for leg in data['trip']['legs']:
                    full_shape.extend(polyline.decode(leg['shape'], precision=6))
                
                return full_shape
            except Exception as json_err:
                print(f"⚠️ JSON Error (Using Backup): {json_err}")
                return backup_shape
        else:
            print(f"⚠️ API Error Status {response.status_code}: {response.text[:200]}")
            return backup_shape
            
    except Exception as e:
        print(f"⚠️ Connection Error (Using Backup): {e}")
        return backup_shape

def create_smooth_geojson(path_coords, color, label, speed_kmh=80):
    if not path_coords:
        return []

    dense_coords = interpolate_points(path_coords, interval_km=0.5) 
    
    features = []
    current_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    
    for i in range(1, len(dense_coords)):
        prev_pt = dense_coords[i-1]
        curr_pt = dense_coords[i]
        
        dist = haversine(prev_pt[0], prev_pt[1], curr_pt[0], curr_pt[1])
        
        duration_seconds = (dist / speed_kmh) * 3600
        
        time_str = current_time.isoformat()
        
        current_time += timedelta(seconds=duration_seconds)
        
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [curr_pt[1], curr_pt[0]], # Lon, Lat
            },
            'properties': {
                'times': [time_str], 
                'style': {
                    'color': color,
                    'weight': 0, 
                    'fillOpacity': 1,
                },
                'icon': 'circle',
                'iconstyle': {
                    'fillColor': color,
                    'fillOpacity': 1,
                    'stroke': 'false', 
                    'radius': 8        
                },
                'popup': label,
            }
        }
        features.append(feature)
        
    return features

def format_rp(val):
    if pd.isna(val): return "Rp 0"
    return f"Rp {val:,.0f}"

st.title("ROUNDTRIP VISUALIZATION")

with st.sidebar:
    st.header("1. Input Data")
    uploaded_file = st.file_uploader("", type=['xlsx'])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = [c.strip().upper() for c in df.columns]
    
    if 'STATUS' in df.columns: df = df[df['STATUS'] == 'MATCHED']
    
    st.sidebar.header("2. Pilih Trip")

    if 'CABANG' in df.columns:
        cabang_options = sorted(df['CABANG'].dropna().unique())
        selected_cabang = st.sidebar.selectbox("Pilih Cabang / Port:", cabang_options)
        
        df_filtered = df[df['CABANG'] == selected_cabang]
    else:
        st.sidebar.warning("Kolom 'CABANG' tidak ditemukan.")
        selected_cabang = None
        df_filtered = df

    if not df_filtered.empty:
        col_kec_dest = 'DEST_KEC'
        col_kec_org = 'ORG_KEC'

        def create_sopt_label(row):
            sopt_id = str(row.get('DEST_ID', 'N/A'))
            kec_dest = str(row.get(col_kec_dest, '-'))
            kec_org = str(row.get(col_kec_org, '-'))
            return f"{sopt_id} ({kec_dest} -> {kec_org})"

        df_filtered['SOPT_Label'] = df_filtered.apply(create_sopt_label, axis=1)

        selected_sopt_label = st.sidebar.selectbox(
            "Pilih SOPT (Dest -> Orig):", 
            df_filtered['SOPT_Label'].unique()
        )
        
        row = df_filtered[df_filtered['SOPT_Label'] == selected_sopt_label].iloc[0]

        dest = {'lat': row['DEST_LAT'], 'lon': row['DEST_LON']}
        org = {'lat': row['ORG_LAT'], 'lon': row['ORG_LON']}
        cabang = str(row['CABANG']).upper().strip()
        port_info = PORT_LOCATIONS.get(cabang, PORT_LOCATIONS.get('JAKARTA'))
        port = {'lat': port_info['lat'], 'lon': port_info['lon']}

        with st.spinner('Calculating Path...'):
            points_base = [port, dest, port, org, port]
            shape_base = get_route_shape(points_base)
            
            points_triang = [port, dest, org, port]
            shape_triang = get_route_shape(points_triang)
            
            features_base = create_smooth_geojson(shape_base, '#FF0000', 'Truk Base Case', speed_kmh=60)
            features_triang = create_smooth_geojson(shape_triang, '#00FF00', 'Truk Triangulasi', speed_kmh=60)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Jarak Base Case", f"{row.get('JARAK_VIA_PORT_KM', 0):.1f} km")
        m2.metric("Jarak Triangulasi", f"{row.get('JARAK_TRIANGULASI_KM', 0):.1f} km")
        m3.metric("Net Saving", format_rp(row.get('ESTIMASI_SAVING_RP', 0)), delta="PROFIT")
        m4.metric("Idle Time", f"{row.get('IDLE_TIME_JAM', 0):.1f} Jam")
        
        st.markdown("---")
        
        col_left, col_right = st.columns(2)
        
        mid_lat = (dest['lat'] + org['lat'] + port['lat']) / 3
        mid_lon = (dest['lon'] + org['lon'] + port['lon']) / 3
        zoom_lvl = 10

        with col_left:
            st.subheader("🔴 Skenario Base Case")
            
            m1 = folium.Map(location=[mid_lat, mid_lon], zoom_start=zoom_lvl, tiles="CartoDB positron")
            
            folium.PolyLine(shape_base, color='green', weight=3, opacity=0.3).add_to(m1)
            
            folium.Marker([port['lat'], port['lon']], icon=folium.Icon(color='blue', icon='anchor', prefix='fa'), tooltip="PORT").add_to(m1)
            folium.Marker([dest['lat'], dest['lon']], icon=folium.Icon(color='red', icon='arrow-down', prefix='fa'), tooltip="BONGKAR").add_to(m1)
            folium.Marker([org['lat'], org['lon']], icon=folium.Icon(color='green', icon='arrow-up', prefix='fa'), tooltip="MUAT").add_to(m1)
            
            if features_base:
                plugins.TimestampedGeoJson(
                    {'type': 'FeatureCollection', 'features': features_base},
                    period='PT1M',       
                    duration='PT1M',     
                    transition_time=50,  
                    auto_play=False,
                    loop=True,
                    max_speed=100,
                    loop_button=True,
                    date_options='HH:mm',
                    time_slider_drag_update=True
                ).add_to(m1)
            
            st_folium(m1, width="100%", height=500, key="map_left")

        with col_right:
            st.subheader("🟢 Skenario Triangulasi")
            
            m2 = folium.Map(location=[mid_lat, mid_lon], zoom_start=zoom_lvl, tiles="CartoDB positron")
            
            folium.PolyLine(shape_triang, color='green', weight=3, opacity=0.3).add_to(m2)
            
            folium.Marker([port['lat'], port['lon']], icon=folium.Icon(color='blue', icon='anchor', prefix='fa'), tooltip="PORT").add_to(m2)
            folium.Marker([dest['lat'], dest['lon']], icon=folium.Icon(color='red', icon='arrow-down', prefix='fa'), tooltip="BONGKAR").add_to(m2)
            folium.Marker([org['lat'], org['lon']], icon=folium.Icon(color='green', icon='arrow-up', prefix='fa'), tooltip="MUAT").add_to(m2)
            
            if features_triang:
                plugins.TimestampedGeoJson(
                    {'type': 'FeatureCollection', 'features': features_triang},
                    period='PT1M',       
                    duration='PT1M',     
                    transition_time=50,
                    auto_play=False,
                    loop=True,
                    max_speed=100,
                    loop_button=True,
                    date_options='HH:mm',
                    time_slider_drag_update=True
                ).add_to(m2)
            
            st_folium(m2, width="100%", height=500, key="map_right")
        
        row_display = row.drop(labels=['SOPT_Label', 'CEK'], errors='ignore')
        
        row_df = pd.DataFrame(row_display).T
        row_df.index = ['Value']
        
        with st.expander("🔍 Lihat Semua Data (Full Row)", expanded=False):
            st.dataframe(row_df, use_container_width=True)
    else:
        st.warning("Data tidak ditemukan untuk cabang ini.")
else:
    st.info("Silakan Upload File Hasil Mapping")