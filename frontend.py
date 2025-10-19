import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components
import folium
from geopy.geocoders import Nominatim

# Set page config
st.set_page_config(page_title="Login & Signup", layout="centered")

# File to store users
USERS_FILE = "user_information.csv"

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

# Load users from CSV file
def load_users():
    if os.path.exists(USERS_FILE):
        df = pd.read_csv(USERS_FILE, sep="|")
        return df
    else:
        return pd.DataFrame(columns=["Name", "Password", "Description", "Address", "Link", "Phone Number", "Categories", "User Type"])

# Save users to CSV file
def save_users(df):
    df.to_csv(USERS_FILE, sep="|", index=False)

# Login function
def login(user, password):
    df = load_users()
    user_row = df[df["Name"] == user]
    if not user_row.empty and user_row.iloc[0]["Password"] == password:
        st.session_state.logged_in = True
        st.session_state.current_user = user
        st.session_state.auth_mode = "login"
        st.success("Login successful!")
        st.rerun()
    else:
        st.error("Invalid username or password")

# Signup function
def signup(name, password, description, address, link, phone, categories, user_type):
    df = load_users()
    if not name or not password:
        st.error("Name and password are required")
        return
    if name in df["Name"].values:
        st.error("Username already exists")
        return
    
    new_user = pd.DataFrame({
        "Name": [name],
        "Password": [password],
        "Description": [description],
        "Address": [address],
        "Link": [link],
        "Phone Number": [phone],
        "Categories": [categories],
        "User Type": [user_type]
    })
    
    df = pd.concat([df, new_user], ignore_index=True)
    save_users(df)
    st.success("Account created successfully! Please log in.")
    st.session_state.auth_mode = "login"
    st.rerun()

# Main UI
if st.session_state.logged_in:
    st.subheader("Available Resources")

    # Load user data
    df = load_users()

    # Add category filters
    st.markdown("### Filter by Category")
    col1, col2 = st.columns(2)
    with col1:
        show_food = st.checkbox("Food", value=True)
    with col2:
        show_shelter = st.checkbox("Shelter", value=True)

    selected_categories = []
    if show_food:
        selected_categories.append("Food")
    if show_shelter:
        selected_categories.append("Shelter")

    # Filter organizations
    if selected_categories:
        df_filtered = df[df["Categories"].apply(
            lambda x: any(cat.lower() in str(x).lower() for cat in selected_categories)
        )]
    else:
        df_filtered = df

    # Generate map
    geolocator = Nominatim(user_agent="streamlit_map")
    m = folium.Map(location=[47.6062, -122.3321], zoom_start=12)

    for _, row in df_filtered.iterrows():
        address = row["Address"]
        if pd.notna(address):
            try:
                location = geolocator.geocode(address)
                if location:
                    popup_text = f"<b>{row['Name']}</b><br>{row['Description']}<br>{row['Address']}"
                    folium.Marker(
                        [location.latitude, location.longitude],
                        popup=popup_text
                    ).add_to(m)
            except Exception:
                continue

    map_path = "/Users/ashwing/Documents/code/dubHacks2025/filtered_foodbanks_map.html"
    m.save(map_path)

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

    if st.button("Logout", key="logout_btn"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()

else:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sign Up", use_container_width=True, key="signup_tab"):
            st.session_state.auth_mode = "signup"
    with col2:
        if st.button("Login", use_container_width=True, key="login_tab"):
            st.session_state.auth_mode = "login"

    st.divider()

    if st.session_state.auth_mode == "login":
        st.subheader("Login")
        with st.form("login_form"):
            user = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit = st.form_submit_button("Login", use_container_width=True)
            if submit:
                login(user, password)
    else:
        st.subheader("Sign Up")
        name = st.text_input("Name", placeholder="Choose a username")
        password = st.text_input("Password", type="password", placeholder="Create a password")
        user_type = st.radio("I am a:", ["Organization", "Person in Need", "Volunteer"], horizontal=True)

        if user_type == "Organization":
            description = st.text_area("Description", placeholder="Enter your description")
            categories = st.text_input("Categories", placeholder="Enter categories (e.g., Food, Shelter)")
            link = st.text_input("Link", placeholder="Enter your link")
        else:
            description = ""
            categories = ""
            link = ""

        address = st.text_input("Address", placeholder="Enter your address")
        phone = st.text_input("Phone Number", placeholder="Enter your phone number")

        if st.button("Sign Up", use_container_width=True):
            signup(name, password, description, address, link, phone, categories, user_type)
