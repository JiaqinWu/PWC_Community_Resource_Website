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

CATEGORY_TRANSLATIONS = {
    "Family": "Familia",
    "Housing Utilities Finances": "Vivienda, Servicios Públicos y Finanzas",
    "Community and Recreation Centers": "Centros Comunitarios y de Recreación",
    "Education Services": "Servicios Educativos",
    "Food": "Alimentos",
    "Immigrant Support Services": "Servicios de Apoyo a Inmigrantes",
    "Medical and Healthcare": "Servicios Médicos y de Salud",
    "Employment Services": "Servicios de Empleo",
    "Clothing": "Ropa",
    "Parenting": "Crianza",
    "Veteran Services": "Servicios para Veteranos",
    "Mental Health Substance Use": "Salud Mental y Uso de Sustancias",
    "Hotlines Crisis": "Líneas Directas de Crisis",
    "Pet": "Mascotas",
    "Real Estate": "Bienes Raíces",
    "Environmental Services": "Servicios Ambientales",
    "Voting Services": "Servicios de Votación",
    "LGBTQ": "LGBTQ",
    "Language": "Idiomas",
    "Legal Services": "Servicios Legales",
    "Detention Services": "Servicios de Detención",
    "Business Services": "Servicios Empresariales"
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
    return m._repr_html_()  



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
    """Find nearest services based on user input or return empty map if no input."""
    
    # If no user address is provided, return the empty map and an empty resource list
    if not user_address:
        return create_empty_map(), None, []

    try:
        location = geolocator.geocode(user_address, timeout=10)
        if location is None:
            return create_empty_map(), "Address not found. Please try again.", []
        user_coords = (location.latitude, location.longitude)
    except Exception as e:
        return create_empty_map(), f"Geocoding error: {str(e)}", []

    # Filter dataset based on selected resource type
    filtered_df = df2[df2["CATEGORY"] == resource_type].copy()
    filtered_df = filtered_df.dropna(subset=["latitude", "longitude"])

    # Compute distances
    filtered_df["Distance"] = filtered_df.apply(
        lambda row: round(geodesic(user_coords, (row["latitude"], row["longitude"])).miles, 2)
        if pd.notna(row["latitude"]) and pd.notna(row["longitude"]) else None, axis=1
    )

    # Sort resources by distance
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

    # Convert nearest_df to a list of dictionaries for display
    resource_list = nearest_df[["ORGANIZATION", "CATEGORY", "Distance", "latitude", "longitude"]].to_dict(orient="records")

    return m._repr_html_(), None, resource_list




@app.route("/", methods=["GET", "POST"])
def home():
    selected_categories = request.form.getlist("categories")  # Get selected categories from form
    
    # Pass categories in both English and Spanish
    categories_en = sorted(df3["CATEGORY"].unique())
    categories_es = [CATEGORY_TRANSLATIONS.get(cat, cat) for cat in categories_en]  # Translate categories

    main_map = create_main_map(selected_categories)

    # Generate resource list
    filtered_df = df3 if not selected_categories or "All" in selected_categories else df3[df3["CATEGORY"].isin(selected_categories)]
    
    resource_list = filtered_df[["ORGANIZATION", "CATEGORY", "latitude", "longitude"]].to_dict(orient="records")

    return render_template(
        "home.html",
        main_map=main_map,
        categories_en=categories_en,
        categories_es=categories_es,
        selected_categories=selected_categories,
        resource_list=resource_list,
        zip=zip  
    )



@app.route("/focus_resource")
def focus_resource():
    """Zoom in on a selected resource when clicked from the list, displaying full details."""
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if not lat or not lon:
        return jsonify({"success": False, "error": "Invalid coordinates"}), 400

    # Find the matching resource
    selected_resource = df2[(df2["latitude"] == float(lat)) & (df2["longitude"] == float(lon))].iloc[0]

    # Create the map focusing on this resource
    m = folium.Map(location=[float(lat), float(lon)], zoom_start=15)

    icon_symbol, icon_color = ICON_MAP.get(selected_resource["CATEGORY"], ("info-circle", "gray"))
    website_link = f'<a href="{selected_resource["WEBSITE"]}" target="_blank">Visit</a>' if pd.notna(selected_resource["WEBSITE"]) else "N/A"

    popup_content = f"""
    <div style="font-family: Arial; font-size: 13px;">
        <b style="font-size: 14px;">{selected_resource['ORGANIZATION']}</b><br>
        <i style="color: #555;">{selected_resource['CATEGORY']}</i><br><br>
        <b>Services Provided:</b> {selected_resource['Services Provided'] if pd.notna(selected_resource['Services Provided']) else 'N/A'}<br>
        <b>Hours of Service:</b> {selected_resource['Hours of Service'] if pd.notna(selected_resource['Hours of Service']) else 'N/A'}<br>
        <b>Address:</b> {selected_resource['ADDRESS'] if pd.notna(selected_resource['ADDRESS']) else 'N/A'}<br>
        <b>Email:</b> {selected_resource['EMAIL'] if pd.notna(selected_resource['EMAIL']) else 'N/A'}<br>
        <b>Phone:</b> {selected_resource['PHONE'] if pd.notna(selected_resource['PHONE']) else 'N/A'}<br>
        <b>Website:</b> {website_link}
    </div>
    """

    folium.Marker(
        location=[float(lat), float(lon)],
        popup=folium.Popup(popup_content, max_width=300),
        icon=folium.Icon(color=icon_color, icon=icon_symbol, prefix="fa")
    ).add_to(m)

    return jsonify({"success": True, "map": m._repr_html_()})



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
    nearest_map, error_message, resource_list = create_empty_map(), None, []

    if request.method == "POST":
        user_address = request.form.get("user_address", "").strip()
        resource_type = request.form.get("resource_type")

        if user_address and resource_type:
            nearest_map, error_message, resource_list = create_nearest_map(user_address, resource_type)

    return render_template(
        "nearest.html",
        nearest_map=nearest_map,
        error_message=error_message,
        resource_types=sorted(df2["CATEGORY"].unique()),  
        resource_list=resource_list
    )




@app.route("/contact")
def contact():
    return render_template("contact.html")





if __name__ == "__main__":
    app.run(debug=True)

