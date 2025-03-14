from flask import Flask, render_template, request, jsonify
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from geopy.distance import geodesic


app = Flask(__name__)


# Load dataset
df2 = pd.read_csv("DataSet.csv")
df2.columns = df2.columns.str.strip()

df3 = df2[(df2["latitude"].between(38.3, 39.0)) & (df2["longitude"].between(-78.0, -77.3))]
df3 = df3[~df3['ORGANIZATION'].isin(['Virginia Community Food Connections','Postpartum Support Virginia (PWC)','Culpeper Housing and Shelter Services',\
                                     'Adams Compassionate Healthcare Network','The Chris Atwood Foundation','Formed Families Forward','Virginia 512 SEIU ',\
                                        'Grace Community Center Clinic'])]


# Define icons
ICON_MAP = {
    "Family": ("users", "purple"),
    "Housing Utilities Finances": ("home", "blue"),
    "Community and Recreation Centers": ("users", "teal"),
    "Education Services": ("graduation-cap", "darkblue"),
    "Food": ("cutlery", "orange"),
    "Immigrant Support Services": ("globe", "darkgreen"),
    "Medical and Healthcare": ("medkit", "red"),
    "Employment Services": ("briefcase", "darkblue"),
    "Clothing": ("shopping-bag", "brown"),
    "Parenting": ("child", "green"),
    "Veteran Services": ("star", "darkgreen"),
    "Mental Health Substance Use": ("heartbeat", "pink"),
    "Hotlines Crisis": ("phone", "darkred"),
    "Pet": ("paw", "darkorange"),
    "Real Estate": ("building", "gray"),
    "Environmental Services": ("leaf", "green"),
    "Voting Services": ("check-square", "black"),
    "LGBTQ": ("rainbow", "purple"),
    "Language": ("language", "darkblue"),
    "Legal Services": ("balance-scale", "black"),
    "Detention Services": ("gavel", "darkred"),
    "Business Services": ("handshake", "gold"),
}

geolocator = Nominatim(user_agent="resource_locator")

def create_empty_map():
    """Generate an empty map placeholder before user searches."""
    m = folium.Map(location=[38.7, -77.3], zoom_start=10)
    folium.Marker(
        location=[38.7, -77.3],
        popup="Start by searching for a location",
        icon=folium.Icon(color="gray", icon="info-sign"),
    ).add_to(m)
    return m._repr_html_(), None


def create_main_map(selected_categories=None):
    """Generate the main overview map with category filtering."""
    m = folium.Map(location=[38.7, -77.6], zoom_start=10)
    marker_cluster = MarkerCluster().add_to(m)

    # Apply filtering if categories are selected
    filtered_df = df3.copy()
    if selected_categories and selected_categories != ["All"]:
        filtered_df = df3[df3["CATEGORY"].isin(selected_categories)]

    for _, res in filtered_df.iterrows():
        icon_symbol, icon_color = ICON_MAP.get(res["CATEGORY"], ("info-circle", "gray"))
        website_link = f'<a href="{res["WEBSITE"]}" target="_blank">Visit</a>' if pd.notna(res["WEBSITE"]) else "N/A"

        popup_content = f"""
        <div style="font-family: Arial; font-size: 13px;">
            <b style="font-size: 14px;">{res['ORGANIZATION']}</b><br>
            <i style="color: #555;">{res['CATEGORY']}</i><br><br>
            <b>Services Provided:</b> {res['Services Provided'] if pd.notna(res['Services Provided']) else 'N/A'}<br>
            <b>Hours of Service:</b> {res['Hours of Service'] if pd.notna(res['Hours of Service']) else 'N/A'}<br>
            <b>Address:</b> {res['ADDRESS'] if pd.notna(res['ADDRESS']) else 'N/A'}<br>
            <b>Email:</b> {res['EMAIL'] if pd.notna(res['EMAIL']) else 'N/A'}<br>
            <b>Phone:</b> {res['PHONE'] if pd.notna(res['PHONE']) else 'N/A'}<br>
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
    """Find nearest services based on user input or keep empty map if no input."""
    
    # If no user address is provided, return the empty map
    if not user_address:
        return create_empty_map()

    try:
        location = geolocator.geocode(user_address, timeout=10)
        if location is None:
            return create_empty_map(), "Address not found. Please try again."
        user_coords = (location.latitude, location.longitude)
    except Exception as e:
        return create_empty_map(), f"Geocoding error: {str(e)}"

    if resource_type == "All":
        filtered_df = df2.copy()
    else:
        filtered_df = df2[df2["CATEGORY"] == resource_type].copy()

    filtered_df = filtered_df.dropna(subset=["latitude", "longitude"])

    # Compute distances
    filtered_df["Distance"] = filtered_df.apply(
        lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).miles if pd.notna(row["latitude"]) and pd.notna(row["longitude"]) else None, axis=1
    )

    nearest_df = filtered_df.nsmallest(10, "Distance").reset_index(drop=True)

    # Create the map centered on user's location
    m = folium.Map(location=user_coords, zoom_start=10)

    # Add user location marker
    folium.Marker(
        location=user_coords,
        icon=folium.Icon(color="red", icon="home", prefix="fa"),
        popup=folium.Popup("Your Location", max_width=300)
    ).add_to(m)

    # Add nearest locations with distance & ranking
    for index, res in nearest_df.iterrows():
        rank_num = index + 1
        rank_suffix = "th"
        if rank_num == 1:
            rank_suffix = "st"
        elif rank_num == 2:
            rank_suffix = "nd"
        elif rank_num == 3:
            rank_suffix = "rd"

        rank = f"{rank_num}{rank_suffix} Nearest"
        icon_symbol, icon_color = ICON_MAP.get(res["CATEGORY"], ("info-circle", "gray"))

        popup_content = f"""
        <div style="font-family: Arial; font-size: 13px;">
            <b style="font-size: 14px;">{rank}: {res['ORGANIZATION']}</b><br>
            <i style="color: #555;">{res['CATEGORY']}</i><br>
            <b>Distance:</b> {round(res['Distance'], 2)} miles<br>
            <b>Address:</b> {res['ADDRESS']}<br>
            <b>Email:</b> {res['EMAIL'] if pd.notna(res['EMAIL']) else 'N/A'}<br>
            <b>Phone:</b> {res['PHONE'] if pd.notna(res['PHONE']) else 'N/A'}<br>
            <b>Website:</b> <a href="{res['WEBSITE']}" target="_blank">Visit</a>
        </div>
        """

        folium.Marker(
            location=[res["latitude"], res["longitude"]],
            popup=folium.Popup(popup_content, max_width=300),
            icon=folium.Icon(color=icon_color, icon=icon_symbol, prefix="fa")
        ).add_to(m)

    return m._repr_html_(), None



@app.route("/", methods=["GET", "POST"])
def home():
    selected_categories = request.form.getlist("categories")  # Get selected categories from form
    main_map = create_main_map(selected_categories)

    return render_template(
        "home.html",  # Now home.html includes the map
        main_map=main_map,
        categories=sorted(df2["CATEGORY"].unique()),
        selected_categories=selected_categories
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
    user_address = request.form.get("user_address", "").strip()
    resource_type = request.form.get("resource_type", "All")

    # Show empty map if no input
    if not user_address:
        nearest_map, error_message = create_empty_map()
    else:
        nearest_map, error_message = create_nearest_map(user_address, resource_type)

    return render_template(
        "nearest.html",
        nearest_map=nearest_map,
        error_message=error_message,
        resource_types=["All"] + sorted(df2["CATEGORY"].unique()),
    )

@app.route("/nearest", methods=["GET", "POST"])
def nearest():
    user_address = request.form.get("user_address", "").strip()
    resource_type = request.form.get("resource_type", "All")

    # Show empty map if no input
    if not user_address:
        nearest_map, error_message = create_empty_map()
    else:
        nearest_map, error_message = create_nearest_map(user_address, resource_type)

    return render_template("nearest.html", nearest_map=nearest_map, error_message=error_message, resource_types=["All"] + sorted(df2["CATEGORY"].unique()))


@app.route("/contact")
def contact():
    return render_template("contact.html")





if __name__ == "__main__":
    app.run(debug=True)

