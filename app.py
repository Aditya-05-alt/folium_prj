import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import numpy as np

# Set page configuration
st.set_page_config(
    page_title="Geospatial Location Visualizer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .map-container {
        border: 2px solid #e6e6e6;
        border-radius: 10px;
        padding: 10px;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .location-popup {
        font-family: Arial, sans-serif;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

def validate_coordinates(lat, lon):
    """Validate latitude and longitude values"""
    try:
        lat = float(lat)
        lon = float(lon)
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
        return True
    except (ValueError, TypeError):
        return False

def create_folium_map(data, cluster=True, map_style='OpenStreetMap'):
    """Create a Folium map with location details and optional clustering"""
    if len(data) == 0:
        return folium.Map(location=[20, 0], zoom_start=2, tiles=map_style)
    
    # Calculate center of the locations
    center_lat = data['latitude'].mean()
    center_lon = data['longitude'].mean()
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10 if len(data) < 100 else 8,
        tiles=map_style,
        control_scale=True
    )
    
    if cluster and len(data) > 1:
        # Create marker cluster for multiple locations
        marker_cluster = MarkerCluster(
            name="Clustered Locations",
            overlay=True,
            control=True,
            icon_create_function=None
        ).add_to(m)
        
        # Add markers to cluster with location details
        for idx, row in data.iterrows():
            # Build popup text with available location details
            popup_lines = [f"<div class='location-popup'>"]
            popup_lines.append(f"<b>📍 Location {idx + 1}</b><br>")
            popup_lines.append(f"<b>Latitude:</b> {row['latitude']:.6f}<br>")
            popup_lines.append(f"<b>Longitude:</b> {row['longitude']:.6f}<br>")
            
            # Add postal code if available
            if 'postal_code' in row and pd.notna(row['postal_code']):
                popup_lines.append(f"<b>Postal Code:</b> {row['postal_code']}<br>")
            
            # Add state if available
            if 'state' in row and pd.notna(row['state']):
                popup_lines.append(f"<b>State:</b> {row['state']}<br>")
            
            # Add city if available
            if 'city' in row and pd.notna(row['city']):
                popup_lines.append(f"<b>City:</b> {row['city']}<br>")
            
            # Add address if available
            if 'address' in row and pd.notna(row['address']):
                popup_lines.append(f"<b>Address:</b> {row['address']}<br>")
            
            popup_lines.append("</div>")
            popup_text = "".join(popup_lines)
            
            # Create tooltip with basic info
            tooltip_text = f"Location {idx + 1}"
            if 'city' in row and pd.notna(row['city']):
                tooltip_text = f"{row['city']}"
            elif 'state' in row and pd.notna(row['state']):
                tooltip_text = f"{row['state']}"
            
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=tooltip_text,
                icon=folium.Icon(color='blue', icon='map-marker', prefix='fa')
            ).add_to(marker_cluster)
    else:
        # Add individual markers without clustering
        for idx, row in data.iterrows():
            popup_lines = [f"<div class='location-popup'>"]
            popup_lines.append(f"<b>📍 Location {idx + 1}</b><br>")
            popup_lines.append(f"<b>Latitude:</b> {row['latitude']:.6f}<br>")
            popup_lines.append(f"<b>Longitude:</b> {row['longitude']:.6f}<br>")
            
            if 'postal_code' in row and pd.notna(row['postal_code']):
                popup_lines.append(f"<b>Postal Code:</b> {row['postal_code']}<br>")
            
            if 'state' in row and pd.notna(row['state']):
                popup_lines.append(f"<b>State:</b> {row['state']}<br>")
            
            if 'city' in row and pd.notna(row['city']):
                popup_lines.append(f"<b>City:</b> {row['city']}<br>")
            
            popup_lines.append("</div>")
            popup_text = "".join(popup_lines)
            
            tooltip_text = f"Location {idx + 1}"
            if 'city' in row and pd.notna(row['city']):
                tooltip_text = f"{row['city']}"
            
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=tooltip_text,
                icon=folium.Icon(color='red', icon='map-marker', prefix='fa')
            ).add_to(m)
    
    # Add plugins
    folium.plugins.MeasureControl(position='bottomleft').add_to(m)
    folium.plugins.Fullscreen(position='topright').add_to(m)
    folium.plugins.LocateControl(position='topright').add_to(m)
    folium.LayerControl().add_to(m)
    
    # Fit map bounds to show all locations
    if len(data) > 0:
        sw = data[['latitude', 'longitude']].min().values.tolist()
        ne = data[['latitude', 'longitude']].max().values.tolist()
        m.fit_bounds([sw, ne])
    
    return m

def main():
    # Main content header
    st.markdown('<h1 class="main-header">🌍 Geospatial Location Visualizer</h1>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'valid_data' not in st.session_state:
        st.session_state.valid_data = pd.DataFrame()
    if 'map_style' not in st.session_state:
        st.session_state.map_style = 'OpenStreetMap'
    if 'cluster_enabled' not in st.session_state:
        st.session_state.cluster_enabled = True

    # SIDEBAR CONTROLS
    with st.sidebar:
        st.header("📁 Data Upload & Configuration")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Upload CSV File with Location Data",
            type=['csv'],
            help="Upload CSV with latitude, longitude, and optional postal_code, state, city columns"
        )
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                
                st.success(f"✅ File uploaded! {len(df)} records found")
                
                # Detect coordinate columns
                possible_lat_cols = [col for col in df.columns if any(term in col.lower() for term in ['lat', 'latitude'])]
                possible_lon_cols = [col for col in df.columns if any(term in col.lower() for term in ['lon', 'long', 'longitude', 'lng'])]
                
                st.subheader("🎯 Coordinate Selection")
                
                # Latitude selection
                if possible_lat_cols:
                    lat_col = st.selectbox(
                        "Latitude Column",
                        options=df.columns,
                        index=df.columns.get_loc(possible_lat_cols[0]),
                        help="Select the column containing latitude values"
                    )
                else:
                    lat_col = st.selectbox(
                        "Latitude Column",
                        options=df.columns,
                        help="Select the column containing latitude values"
                    )
                
                # Longitude selection
                if possible_lon_cols:
                    lon_col = st.selectbox(
                        "Longitude Column",
                        options=df.columns,
                        index=df.columns.get_loc(possible_lon_cols[0]),
                        help="Select the column containing longitude values"
                    )
                else:
                    lon_col = st.selectbox(
                        "Longitude Column",
                        options=df.columns,
                        help="Select the column containing longitude values"
                    )
                
                # Validate data
                valid_mask = df.apply(
                    lambda row: validate_coordinates(row[lat_col], row[lon_col]), 
                    axis=1
                )
                
                valid_data = df[valid_mask].copy()
                valid_data['latitude'] = pd.to_numeric(valid_data[lat_col], errors='coerce')
                valid_data['longitude'] = pd.to_numeric(valid_data[lon_col], errors='coerce')
                valid_data = valid_data.dropna(subset=['latitude', 'longitude'])
                
                st.session_state.valid_data = valid_data
                
                # Show validation results
                st.markdown("---")
                st.subheader("📊 Validation Results")
                st.write(f"✅ **Valid locations:** {len(valid_data)}")
                st.write(f"❌ **Invalid coordinates:** {len(df) - len(valid_data)}")
                
                # Show available location columns
                location_cols = [col for col in valid_data.columns if col.lower() in ['postal_code', 'zip', 'state', 'city', 'address', 'location']]
                if location_cols:
                    st.write(f"📋 **Location data found:** {', '.join(location_cols)}")
                
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
        
        else:
            st.info("👆 Please upload a CSV file to begin")
            st.markdown("---")
            st.subheader("📋 Recommended Data Format")
            st.write("""
            Include these columns:
            - **latitude** (required)
            - **longitude** (required)
            - **postal_code** (optional)
            - **state** (optional)
            - **city** (optional)
            - **address** (optional)
            """)
        
        # Map settings
        st.markdown("---")
        st.subheader("🗺️ Map Settings")
        
        st.session_state.cluster_enabled = st.checkbox(
            "Cluster Locations", 
            value=True,
            help="Group nearby locations together"
        )
        
        st.session_state.map_style = st.selectbox(
            "Map Style",
            options=['OpenStreetMap', 'CartoDB positron', 'Stamen Terrain', 'Stamen Toner'],
            index=0
        )

    # MAIN CONTENT AREA
    if not st.session_state.valid_data.empty:
        # Display location statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Locations Found", len(st.session_state.valid_data))
        
        with col2:
            avg_lat = st.session_state.valid_data['latitude'].mean()
            st.metric("Avg Latitude", f"{avg_lat:.6f}")
        
        with col3:
            avg_lon = st.session_state.valid_data['longitude'].mean()
            st.metric("Avg Longitude", f"{avg_lon:.6f}")
        
        with col4:
            unique_states = st.session_state.valid_data['state'].nunique() if 'state' in st.session_state.valid_data else 0
            st.metric("Unique States", unique_states if unique_states > 0 else "N/A")
        
        # Interactive Map
        st.markdown("### 📍 Location Map")
        st.markdown('<div class="map-container">', unsafe_allow_html=True)
        
        map_obj = create_folium_map(
            st.session_state.valid_data, 
            cluster=st.session_state.cluster_enabled,
            map_style=st.session_state.map_style
        )
        
        map_data = st_folium(
            map_obj, 
            width=None,
            height=600,
            returned_objects=[],
            key="main_map"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Location details tabs
        tab1, tab2, tab3 = st.tabs(["📍 Location Data", "📊 Statistics", "🌐 Geographic Summary"])
        
        with tab1:
            st.dataframe(st.session_state.valid_data.head(20), use_container_width=True)
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Latitude Distribution**")
                st.bar_chart(st.session_state.valid_data['latitude'].value_counts().head(10))
            with col2:
                st.write("**Longitude Distribution**")
                st.bar_chart(st.session_state.valid_data['longitude'].value_counts().head(10))
        
        with tab3:
            if 'state' in st.session_state.valid_data:
                st.write("**Locations by State**")
                state_counts = st.session_state.valid_data['state'].value_counts()
                st.dataframe(state_counts, use_container_width=True)
            
            if 'postal_code' in st.session_state.valid_data:
                st.write("**Locations by Postal Code**")
                postal_counts = st.session_state.valid_data['postal_code'].value_counts().head(10)
                st.dataframe(postal_counts, use_container_width=True)
    
    else:
        # Welcome screen
        st.info("🌐 Welcome to Location Data Visualizer!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("""
            ### How to use:
            1. **Upload** a CSV file with location data
            2. **Select** coordinate columns
            3. **View** locations on interactive map
            4. **Explore** geographic patterns
            
            ### Enhanced Features:
            - 📍 Location-based clustering
            - 📮 Postal code and state display
            - 🗺️ Professional map styling
            - 📊 Geographic analytics
            """)
        
        with col2:
            st.write("### 📋 Ideal Data Structure")
            sample_data = pd.DataFrame({
                'location_id': [1, 2, 3, 4, 5],
                'latitude': [40.7128, 34.0522, 41.8781, 39.9526, 29.7604],
                'longitude': [-74.0060, -118.2437, -87.6298, -75.1652, -95.3698],
                'postal_code': ['10001', '90001', '60601', '19102', '77001'],
                'state': ['NY', 'CA', 'IL', 'PA', 'TX'],
                'city': ['New York', 'Los Angeles', 'Chicago', 'Philadelphia', 'Houston'],
                'address': ['123 Main St', '456 Oak Ave', '789 Pine Rd', '321 Elm St', '654 Maple Ave']
            })
            st.dataframe(sample_data, use_container_width=True)

if __name__ == "__main__":
    main()