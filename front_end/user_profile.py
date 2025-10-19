import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components
import folium
from geopy.geocoders import Nominatim
import numpy as np

# File to store users
USERS_FILE = "user_information.csv"

def profile(USERS_FILE):
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

    # --- PROFILE PAGE ---
    if st.session_state.logged_in:
        # Load user data
        if not os.path.exists(USERS_FILE):
            st.error("User information file not found.")
            st.stop()

        try:
            df = pd.read_csv(USERS_FILE, sep="|")
        except Exception as e:
            st.error(f"Error loading user data: {e}")
            st.stop()

        username = st.session_state.current_user

        if username not in df["Name"].values:
            st.error("User not found in records.")
            st.stop()

        user_info = df[df["Name"] == username].iloc[0]

        # --- Display profile info ---
        st.title("👤 Profile")
        st.markdown("---")

        # Utility function: display field if valid
        def show_field(label, value):
            if pd.notna(value) and str(value).strip() != "":
                st.write(f"**{label}:** {value}")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Account Details")
            show_field("Name", user_info["Name"])
            # Password intentionally NOT shown
            show_field("User Type", user_info.get("User Type", ""))
            show_field("Description", user_info.get("Description", ""))

        with col2:
            st.subheader("Contact & Location")
            show_field("Address", user_info.get("Address", ""))
            show_field("Phone Number", user_info.get("Phone Number", ""))
            show_field("Link", user_info.get("Link", ""))
            show_field("Categories", user_info.get("Categories", ""))

        st.markdown("---")
