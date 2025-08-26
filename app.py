import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster, FastMarkerCluster
from streamlit_folium import st_folium

# ---------------- Page config & style ----------------
st.set_page_config(page_title="Geospatial Location Visualizer", page_icon="🌍", layout="wide")
st.markdown("""
<style>
.main-header{font-size:2.0rem;color:#1f77b4;text-align:center;margin:.25rem 0 .75rem;}
.cluster-popup{font-family:Arial, sans-serif;font-size:12px;line-height:1.25;padding:5px;max-width:320px;}
.block-container{padding-top: 0.8rem;}
</style>
""", unsafe_allow_html=True)

# ---------------- Helpers ----------------
def validate_coordinates(lat, lon):
    try:
        lat = float(lat); lon = float(lon)
        return (-90 <= lat <= 90) and (-180 <= lon <= 180)
    except Exception:
        return False

@st.cache_data(show_spinner=False)
def parse_csv(file):
    """Read a CSV and return (valid_df, valid_count, invalid_count, postal_col, name_col, lat_col, lon_col)."""
    df = pd.read_csv(file)

    # Detect lat/lon columns
    lat_col = lon_col = None
    for c in df.columns:
        lc = c.lower()
        if lat_col is None and any(t in lc for t in ["lat","latitude"]): lat_col = c
        if lon_col is None and any(t in lc for t in ["lon","long","longitude","lng"]): lon_col = c
    if lat_col is None or lon_col is None:
        nums = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(nums) >= 2:
            lat_col, lon_col = nums[:2]
        else:
            # no usable coords
            return pd.DataFrame(), 0, len(df), None, None, None, None

    # Coerce & validate
    tmp = df.copy()
    tmp["__lat"] = pd.to_numeric(tmp[lat_col], errors="coerce")
    tmp["__lon"] = pd.to_numeric(tmp[lon_col], errors="coerce")
    mask = (
        tmp["__lat"].notna() & tmp["__lon"].notna()
        & tmp["__lat"].between(-90, 90) & tmp["__lon"].between(-180, 180)
    )
    valid = tmp.loc[mask].copy()
    valid.rename(columns={"__lat":"latitude","__lon":"longitude"}, inplace=True)
    valid.drop(columns=["__lat","__lon"], inplace=True, errors="ignore")

    # Detect postal & name columns
    postal_candidates = [c for c in valid.columns if any(t in c.lower()
                         for t in ["postal","zipcode","zip code","zip","post_code","pincode"])]
    postal_col = postal_candidates[0] if postal_candidates else None
    name_candidates = [c for c in valid.columns if c.lower() in ["name","title","label","location_name"]]
    name_col = name_candidates[0] if name_candidates else None

    return valid, int(mask.sum()), int(len(df) - mask.sum()), postal_col, name_col, lat_col, lon_col

def popup_html(row, postal_col=None, name_col=None):
    parts = ["<div class='cluster-popup'>", "<b>📍 Location Details</b><br>"]
    if name_col and name_col in row and pd.notna(row[name_col]):
        parts.append(f"<b>Name:</b> {row[name_col]}<br>")
    parts.append(f"<b>Latitude:</b> {row['latitude']:.6f}<br>")
    parts.append(f"<b>Longitude:</b> {row['longitude']:.6f}<br>")
    if postal_col and postal_col in row and pd.notna(row[postal_col]):
        parts.append(f"<b>Postal Code:</b> {row[postal_col]}<br>")
    if "state" in row and pd.notna(row["state"]):   parts.append(f"<b>State:</b> {row['state']}<br>")
    if "city"  in row and pd.notna(row["city"]):    parts.append(f"<b>City:</b> {row['city']}<br>")
    if "address" in row and pd.notna(row["address"]): parts.append(f"<b>Address:</b> {row['address']}<br>")
    parts.append("</div>")
    return "".join(parts)

def tooltip_text(row, postal_col=None, name_col=None, idx=0):
    """
    Always show Lat/Lon and Postal Code (if available) on hover.
    Name (if present) is prefixed on the first line.
    """
    name_part = ""
    if name_col and name_col in row and pd.notna(row[name_col]):
        name_part = f"{row[name_col]}\n"
    lat_val = row.get("latitude", None)
    lon_val = row.get("longitude", None)
    latlon_part = f"Lat: {float(lat_val):.6f}, Lon: {float(lon_val):.6f}" if lat_val is not None and lon_val is not None else "Lat/Lon: n/a"
    postal_part = ""
    if postal_col and postal_col in row and pd.notna(row[postal_col]):
        postal_part = f"\nPostal: {row[postal_col]}"
    return f"{name_part}{latlon_part}{postal_part}"

def add_layer(df, color, layer_name, cluster=True, fast=False, postal_col=None, name_col=None):
    """
    When fast=True -> FastMarkerCluster (very fast, but no custom icon/popup on spiderfy and no tooltips).
    When fast=False -> MarkerCluster with colored house icons + popups/tooltips.
    """
    layer = folium.FeatureGroup(name=layer_name, overlay=True, control=True)
    if df.empty:
        return layer

    if cluster and fast:
        pts = df[["latitude","longitude"]].to_numpy().tolist()
        FastMarkerCluster(pts, name=f"{layer_name} Fast").add_to(layer)
        return layer

    # Normal cluster path (preserves icon colors and popups/tooltips)
    cl = MarkerCluster(
        name=f"{layer_name} Clusters", overlay=True, control=False,
        options={'maxClusterRadius':50,'spiderfyOnMaxZoom':True,'showCoverageOnHover':True,'zoomToBoundsOnClick':True}
    )
    layer.add_child(cl)
    for i, r in df.iterrows():
        folium.Marker(
            [r["latitude"], r["longitude"]],
            tooltip=folium.Tooltip(tooltip_text(r, postal_col, name_col, i+1), sticky=True),
            popup=folium.Popup(popup_html(r, postal_col, name_col), max_width=320),
            icon=folium.Icon(color=color, icon="home", prefix="fa")  # colored house icon
        ).add_to(cl)
    return layer

def build_map(csv1, csv2, cluster=True, fast_csv=False,
              postal1=None, postal2=None, name1=None, name2=None):
    if csv1.empty and csv2.empty:
        return folium.Map(location=[20,0], zoom_start=2)
    base = pd.concat(
        [csv1[["latitude","longitude"]]] if not csv1.empty else [] +
        [csv2[["latitude","longitude"]]] if not csv2.empty else [],
        ignore_index=True
    )
    m = folium.Map(location=[base["latitude"].mean(), base["longitude"].mean()], zoom_start=9)

    # URL Data = GREEN, Store Data = BLUE
    add_layer(csv1, "green", "URL Data (Green)",  cluster, fast_csv, postal1, name1).add_to(m)
    add_layer(csv2, "blue",  "Store Data (Blue)", cluster, fast_csv, postal2, name2).add_to(m)

    folium.plugins.Fullscreen(position='topright').add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m

# ---------------- App ----------------
def main():
    st.markdown('<h1 class="main-header">🌍 Location Visualizer — URL Data (Green) & Store Data (Blue)</h1>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("📁 Upload CSVs")
        c1, c2 = st.columns(2)
        with c1:
            up1 = st.file_uploader("URL Data (CSV)", type=["csv"], key="csv1")
        with c2:
            up2 = st.file_uploader("Store Data (CSV)", type=["csv"], key="csv2")

        st.header("⚙️ Map Settings")
        cluster = st.checkbox("Cluster locations", value=True)
        fast_csv = st.checkbox(
            "High-speed for large CSVs (FastMarkerCluster)",
            value=False,
            help="Much faster for big files. Disables custom icons/popups/tooltips on spiderfy."
        )

    # Parse CSVs
    csv1, c1_ok, c1_bad, postal1, name1, _, _ = parse_csv(up1) if up1 else (pd.DataFrame(),0,0,None,None,None,None)
    csv2, c2_ok, c2_bad, postal2, name2, _, _ = parse_csv(up2) if up2 else (pd.DataFrame(),0,0,None,None,None,None)

    # Metrics
    total = len(csv1) + len(csv2)
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Total Locations", f"{total:,}")
    with m2:
        if total:
            lat_all = pd.concat([s for s in [csv1.get("latitude"), csv2.get("latitude")] if s is not None], ignore_index=True)
            st.metric("Avg Latitude", f"{lat_all.mean():.6f}")
        else: st.metric("Avg Latitude", "—")
    with m3:
        if total:
            lon_all = pd.concat([s for s in [csv1.get("longitude"), csv2.get("longitude")] if s is not None], ignore_index=True)
            st.metric("Avg Longitude", f"{lon_all.mean():.6f}")
        else: st.metric("Avg Longitude", "—")
    with m4:
        any_postal = postal1 or postal2
        if any_postal:
            series_list = []
            if postal1 and postal1 in csv1.columns: series_list.append(csv1[postal1])
            if postal2 and postal2 in csv2.columns: series_list.append(csv2[postal2])
            if series_list:
                st.metric("Unique Postal Codes", pd.concat(series_list, ignore_index=True).nunique(dropna=True))
            else:
                st.metric("Unique Postal Codes", "0")
        else:
            st.metric("Unique Postal Codes", "Not found")

    # Map (full width)
    st.markdown("### 📍 Map (Green = URL Data, Blue = Store Data)")
    with st.spinner("Rendering map..."):
        fmap = build_map(
            csv1, csv2, cluster=cluster, fast_csv=fast_csv,
            postal1=postal1, postal2=postal2, name1=name1, name2=name2
        )
    st_folium(fmap, width=None, height=640, returned_objects=[])

    # Postal Code summary (bar graph)
    st.markdown("### 🧭 Postal Code Summary")
    if postal1 or postal2:
        series = []
        if postal1 and postal1 in csv1.columns: series.append(csv1[postal1].dropna().astype(str))
        if postal2 and postal2 in csv2.columns: series.append(csv2[postal2].dropna().astype(str))
        if series:
            combined = pd.concat(series, ignore_index=True)
            counts = combined.value_counts().head(20)  # top 20
            st.bar_chart(counts)
        else:
            st.info("No postal codes detected in the uploaded files.")
    else:
        st.info("No postal code column detected. Make sure your CSV has a column like 'postal', 'zip', 'zipcode', etc.")

    # Data previews
    with st.expander("📊 URL Data (valid rows)"):
        if not csv1.empty:
            st.write(f"✅ Valid: {c1_ok:,} | ❌ Invalid: {c1_bad:,}")
            st.dataframe(csv1.head(25), use_container_width=True)
        else:
            st.info("No valid rows in URL Data.")
    with st.expander("📊 Store Data (valid rows)"):
        if not csv2.empty:
            st.write(f"✅ Valid: {c2_ok:,} | ❌ Invalid: {c2_bad:,}")
            st.dataframe(csv2.head(25), use_container_width=True)
        else:
            st.info("No valid rows in Store Data.")

if __name__ == "__main__":
    main()
