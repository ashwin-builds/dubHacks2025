import streamlit as st
import pandas as pd
import os

# Set page config
st.set_page_config(page_title="Login & Signup", layout="centered")

# File to store users
USERS_FILE = "/Users/ashwing/Documents/code/dubHacks2025/user_information.csv"

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
        # Create empty dataframe with headers
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
    
    # Create new user row
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
    
    # Append to dataframe
    df = pd.concat([df, new_user], ignore_index=True)
    save_users(df)
    st.success("Account created successfully! Please log in.")
    st.session_state.auth_mode = "login"
    st.rerun()

# Main UI
if st.session_state.logged_in:
    st.title("Dashboard")
    st.write(f"Welcome, **{st.session_state.current_user}**!")
    
    df = load_users()
    user_data = df[df["Name"] == st.session_state.current_user].iloc[0]
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Your Profile")
        st.write(f"**Description:** {user_data['Description']}")
        st.write(f"**Address:** {user_data['Address']}")
        st.write(f"**Phone Number:** {user_data['Phone Number']}")
    
    with col2:
        st.subheader("Account Info")
        st.write(f"**Name:** {st.session_state.current_user}")
        st.write(f"**Link:** {user_data['Link']}")
        st.write(f"**Categories:** {user_data['Categories']}")
    
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
    
    else:  # signup mode
        st.subheader("Sign Up")
        name = st.text_input("Name", placeholder="Choose a username")
        password = st.text_input("Password", type="password", placeholder="Create a password")
        user_type = st.radio("I am a:", ["Organization", "Person in Need", "Volunteer"], horizontal=True)
        
        # Only show description and categories for organizations
        if user_type == "Organization":
            description = st.text_area("Description", placeholder="Enter your description")
            categories = st.text_input("Categories", placeholder="Enter categories (comma-separated)")
            link = st.text_input("Link", placeholder="Enter your link")
        else:
            description = ""
            categories = ""
            link = ""
        
        address = st.text_input("Address", placeholder="Enter your address")
        
        phone = st.text_input("Phone Number", placeholder="Enter your phone number")
        
        if st.button("Sign Up", use_container_width=True):
            signup(name, password, description, address, link, phone, categories, user_type)