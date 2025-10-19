import streamlit as st
from donate_page import donate_page
from requests_page import request_page
import pandas as pd

# Set page config
st.set_page_config(
    page_title="Donation Coordination System",
    page_icon="🤝",
    layout="wide"
)

#df= pd.read_csv('user_information.csv')
# name = st.session_state.current_user

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# If not logged in, show login page
if not st.session_state.logged_in:
    # Import and show your existing login page
    exec(open("frontend.py").read())
else:

    name = st.session_state.current_user
    df = pd.read_csv("user_information.csv", sep='|', engine="python")
    user_row = df[df['Name'] == name]
    user_type = user_row.iloc[0]['User Type']
    print(user_type)
    
    with st.sidebar:
        st.title("🤝 Navigation")
        st.write(f"👤 **{st.session_state.current_user}**")
        st.write(user_type)# st.write(f"📋 {st.session_state.user_type}")
        st.divider()

        if user_type in ["Organization", "Volunteer"]:
            page = st.radio(
                "Go to:",
                ["🎁 Donate Items", "📊 Dashboard", "🤝 View Matches"],
                key="nav"
            )
        elif user_type == "Person in Need":
            page = st.radio(
                "Go to:",
                ["📝 Request Items", "📊 Dashboard", "🤝 View Matches"],
                key="nav"
            )
        
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    
    # Route to appropriate page
    if "Donate" in page:
        donate_page()
    elif "Request" in page:
        request_page()
    elif "Dashboard" in page:
        st.title("📊 Dashboard")
        st.info("Dashboard coming soon!")
    elif "Matches" in page:
        st.title("🤝 AI Matches")
        st.info("Matching system coming soon!")