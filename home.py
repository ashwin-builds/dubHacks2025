import streamlit as st
from donate_page import donate_page
from requests_page import request_page
from user_profile import profile
import pandas as pd
import os
import folium
from geopy.geocoders import Nominatim
import streamlit.components.v1 as components

USERS_FILE = "user_information.csv"
def load_users():
    if os.path.exists(USERS_FILE):
        df = pd.read_csv(USERS_FILE, sep="|")
        return df
    else:
        return pd.DataFrame(columns=["Name", "Password", "Description", "Address", "Link", "Phone Number", "Categories", "User Type"])

def home_page():
    st.title("Dashboard")
    if st.session_state.logged_in:
        st.subheader("Available Resources")

        # Load user data
        df = load_users()


        selected_categories = ["Food", "Shelter"]

        # Filter organizations
        if selected_categories:
            df_filtered = df[df["Categories"].apply(
                lambda x: any(cat.lower() in str(x).lower() for cat in selected_categories)
            )]
        else:
            df_filtered = df

        map_path = "foodbanks_map.html"

        # Inject CSS to remove whitespace and background
        with open(map_path, 'r') as f:
            html_data = f.read()

        css_injection = """
        <style>
        html, body {
            margin: 0 !important;
            padding: 0 !important;
            height: 100% !important;
            overflow: hidden !important;
            background-color: black;
        }
        .leaflet-container, .folium-map, #map, .map {
            height: 100vh !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """

        if "</head>" in html_data:
            html_data = html_data.replace("</head>", css_injection + "</head>")
        else:
            html_data = css_injection + html_data

        components.html(html_data, height=600, scrolling=False)