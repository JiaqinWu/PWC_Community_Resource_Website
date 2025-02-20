from flask import Flask, render_template, request, jsonify
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

app = Flask(__name__)

# Load data
df2 = pd.read_csv("Existing_withlatlong.csv")

# Define custom icons for different resource types
ICON_MAP = {
    "Family": ("users", "purple"),
    "Food": ("cutlery", "orange"),
    "Housing Utilities Finances": ("home", "blue"),
    "Medical and Healthcare": ("medkit", "red"),
    "Criminal Justice": ("balance-scale", "black"),
    "Mental Health Substance Use": ("heartbeat", "pink"),
    "Clothing": ("shopping-bag", "brown"),
    "Veteran Services": ("star", "darkgreen"),
    "Parenting": ("child", "green"),
    "Hotlines Crisis": ("phone", "darkred"),
    "Community and Recreation Centers": ("users","teal")
}

geolocator = Nominatim(user_agent="resource_locator")  # Initialize Nominatim Geocoder

def create_empty_map():
    """Generate an empty map placeholder before user searches."""
    m = folium.Map(location=[38.7, -77.3], zoom_start=10)
    folium.Marker(
        location=[38.7, -77.3],
        popup="Start by searching for a location",
        icon=folium.Icon(color="gray", icon="info-sign"),
    ).add_to(m)
    return m._repr_html_(), None

def create_main_map():
    """Generate the main overview map."""
    m = folium.Map(location=[38.7, -77.3], zoom_start=10)
    marker_cluster = MarkerCluster().add_to(m)

    for _, res in df2.iterrows():
        icon_symbol, icon_color = ICON_MAP.get(res["Type"], ("info-circle", "gray"))
        website_link = f'<a href="{res["Website"]}" target="_blank">Visit</a>' if isinstance(res["Website"], str) and res["Website"] else "N/A"

        popup_content = f"""
        <div style="font-family: Arial; font-size: 13px;">
            <b style="font-size: 14px;">{res['Name of Org']}</b><br>
            <i style="color: #555;">{res['Type']}</i><br><br>
            <b>Services Provided:</b> {res['Services Provided']}<br>
            <b>Address:</b> {res['Address']}<br>
            <b>Email:</b> {res['Email'] if res['Email'] else 'N/A'}<br>
            <b>Phone:</b> {res['Phone'] if res['Phone'] else 'N/A'}<br>
            <b>Website:</b> {website_link}
        </div>
        """
        folium.Marker(
            location=[res["latitude"], res["longitude"]],
            popup=folium.Popup(popup_content, max_width=300),
            icon=folium.Icon(color=icon_color, icon=icon_symbol, prefix="fa")
        ).add_to(marker_cluster)

    return m._repr_html_()

def create_nearest_map(user_address, resource_type):
    """Generate map with nearest locations based on user input."""
    try:
        location = geolocator.geocode(user_address, timeout=10)
        if location is None:
            return None, "Address not found. Please try again."
        user_coords = (location.latitude, location.longitude)
    except Exception as e:
        return None, f"Geocoding error: {str(e)}"

    filtered_df = df2.copy() if resource_type == "All" else df2[df2["Type"] == resource_type].copy()
    filtered_df = filtered_df.dropna(subset=["latitude", "longitude"])

    filtered_df["Distance"] = filtered_df.apply(
        lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).miles 
        if pd.notna(row["latitude"]) and pd.notna(row["longitude"]) else None, axis=1
    )

    nearest_df = filtered_df.nsmallest(5, "Distance")

    m = folium.Map(location=user_coords, zoom_start=12)
    
    folium.Marker(
        location=user_coords, 
        icon=folium.Icon(color="red", icon="home", prefix="fa"),
        popup="Your Location"
    ).add_to(m)

    for _, res in nearest_df.iterrows():
        distance = round(res["Distance"], 2)
        website_link = f'<a href="{res["Website"]}" target="_blank">Visit</a>' if isinstance(res["Website"], str) and res["Website"] else "N/A"
        icon_symbol, icon_color = ICON_MAP.get(res["Type"], ("info-circle", "gray"))

        popup_content = f"""
        <div style="font-family: Arial; font-size: 13px;">
            <b style="font-size: 14px;">{res['Name of Org']}</b><br>
            <i style="color: #555;">{res['Type']}</i><br><br>
            <b>Services Provided:</b> {res['Services Provided'] if pd.notna(res['Services Provided']) else 'N/A'}<br>
            <b>Address:</b> {res['Address'] if pd.notna(res['Address']) else 'N/A'}<br>
            <b>Email:</b> {res['Email'] if pd.notna(res['Email']) else 'N/A'}<br>
            <b>Phone:</b> {res['Phone'] if pd.notna(res['Phone']) else 'N/A'}<br>
            <b>Website:</b> {website_link}<br>
            <b>Distance:</b> {distance} miles
        </div>
        """

        folium.Marker(
            location=[res["latitude"], res["longitude"]],
            popup=folium.Popup(popup_content, max_width=300),
            icon=folium.Icon(color=icon_color, icon=icon_symbol, prefix="fa")
        ).add_to(m)

    return m._repr_html_(), None

@app.route("/")
def index():
    main_map = create_main_map()
    nearest_map, error_message = create_empty_map()

    return render_template(
        "index.html",
        main_map=main_map,
        nearest_map=nearest_map,
        error_message=error_message,
        resource_types=["All"] + sorted(df2["Type"].unique())
    )

@app.route("/get_address", methods=["POST"])
def get_address():
    """Retrieve an address from latitude & longitude using Nominatim."""
    data = request.json
    lat, lon = data.get("latitude"), data.get("longitude")

    try:
        location = geolocator.reverse((lat, lon), exactly_one=True)
        if location:
            return jsonify({"address": location.address})
        else:
            return jsonify({"error": "Could not retrieve address"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search", methods=["GET", "POST"])
def search():
    """Handle user input for nearest locations and return the updated map."""
    if request.method == "POST":
        user_address = request.form.get("user_address")
        resource_type = request.form.get("resource_type")
        nearest_map, error_message = create_nearest_map(user_address, resource_type)
    else:
        nearest_map, error_message = create_empty_map()  # Default empty map if no search

    return render_template(
        "index.html",
        main_map=create_main_map(),
        nearest_map=nearest_map,
        error_message=error_message,
        resource_types=["All"] + sorted(df2["Type"].unique()),
    )


if __name__ == "__main__":
    app.run(debug=True)
