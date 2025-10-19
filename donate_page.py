import streamlit as st
import pandas as pd
from models import CoordinationSystem, Donor, Shelter, TextParser
import csv

# Initialize coordination system
if 'system' not in st.session_state:
    st.session_state.system = CoordinationSystem()

# Load users from CSV
def load_user_from_csv(username):
    """Load user information from CSV"""
    df = pd.read_csv("user_information.csv", sep="|")
    user_row = df[df["Name"] == username]
    
    if not user_row.empty:
        user_data = user_row.iloc[0]
        user_type = user_data["User Type"]
        name = user_data["Name"]
        location = user_data["Address"]
        contact = user_data["Phone Number"] if pd.notna(user_data["Phone Number"]) else ""
        
        # Create appropriate user object
        if user_type == "Organization":
            return Shelter(name, location, contact), user_type
        elif user_type == "Volunteer":
            return Donor(name, location, contact), user_type
    
    return None, None

def donate_page():
    """Main donate page for donors and shelters"""
    
    # Check if user is logged in
    if not st.session_state.get("logged_in", False):
        st.error("Please log in to access this page")
        return
    
    username = st.session_state.get("current_user")
    user_type = st.session_state.get("user_type")
    
    # Only allow Organizations and Volunteers to donate
    if user_type not in ["Organization", "Volunteer"]:
        st.error("Only Organizations and Volunteers can create donations")
        st.info("You are logged in as: Person in Need - Please use the Request page instead")
        return
    
    # Load user object
    user_obj, _ = load_user_from_csv(username)
    if not user_obj:
        st.error("Error loading user information")
        return
    
    # Page header
    st.title("🎁 Donate Items")
    st.write(f"Welcome, **{username}**!")
    st.divider()
    
    # Search/Filter section at top
    st.subheader("🔍 Search Requests (When you have items as a donor)")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "Search for specific needs",
            placeholder="e.g., blankets, food, winter clothes",
            help="Search through current requests to find items you can donate"
        )
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("🔍 Search", use_container_width=True, type="primary"):
            st.session_state.search_performed = True
    
    # Display search results if search was performed
    if st.session_state.get("search_performed", False) and search_query:
        st.info(f"Searching for requests matching: **{search_query}**")
        
        # Load and filter requests
        try:
            requests_df = pd.read_csv("requests.csv")
            
            # Filter by search query
            matching_requests = requests_df[
                (requests_df['items'].str.contains(search_query, case=False, na=False)) &
                (requests_df['status'] == 'open')
            ]
            
            if not matching_requests.empty:
                st.success(f"Found {len(matching_requests)} matching requests")
                
                for idx, row in matching_requests.head(5).iterrows():
                    with st.expander(f"📋 {row['requester_name']} - {row['urgency'].upper()} urgency"):
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.write(f"**Items needed:** {row['items']}")
                            st.caption(f"Posted: {row['created_at'][:10]}")
                        with col2:
                            urgency_color = {
                                'urgent': '🔴',
                                'high': '🟠',
                                'normal': '🟡',
                                'low': '🟢'
                            }
                            st.write(f"{urgency_color.get(row['urgency'], '⚪')} **{row['urgency'].title()}**")
            else:
                st.warning(f"No open requests found matching '{search_query}'")
        
        except FileNotFoundError:
            st.warning("No requests available yet")
    
    st.divider()
    
    # Main donation section - Tabs for different views
    tab1, tab2 = st.tabs(["✍️ Create New Offering", "📊 View All Requests"])
    
    with tab1:
        st.subheader("Create a New Donation Offering")
        st.info("💡 Describe what you want to donate in plain English. Our AI will parse it automatically!")
        
        # Text input for donation
        donation_text = st.text_area(
            "What would you like to donate?",
            placeholder="Example: I have 25 fleece blankets and 15 winter jackets to donate\n\nOr: Donating 50 cans of soup and 20 boxes of pasta",
            height=150,
            help="Be as specific as possible about quantities and item types"
        )
        
        # Preview parsed items before submitting
        if donation_text and len(donation_text) > 5:
            with st.expander("🔍 Preview Parsed Items (AI Analysis)", expanded=False):
                with st.spinner("Analyzing your donation..."):
                    try:
                        # Parse the text to show preview
                        parsed_items = TextParser.parse_text_to_items(donation_text)
                        
                        st.write("**AI detected these items:**")
                        for item in parsed_items:
                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                st.write(f"• **{item.name}**")
                            with col2:
                                st.write(f"Qty: {item.quantity}")
                            with col3:
                                st.write(f"📦 {item.category.value}")
                        
                        st.caption("✨ Parsed automatically using AI")
                    except Exception as e:
                        st.error(f"Error parsing items: {e}")
        
        # Submit button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Post Donation Offering", 
                        type="primary", 
                        use_container_width=True,
                        disabled=not donation_text or len(donation_text) < 5):
                
                with st.spinner("Creating your offering..."):
                    try:
                        # Create offering using models.py
                        offering = user_obj.create_offering_from_text(donation_text)
                        st.session_state.system.add_offering(offering)
                        
                        st.success("✅ Donation offering posted successfully!")
                        st.balloons()
                        
                        # Show confirmation
                        with st.expander("✅ Offering Details", expanded=True):
                            st.write(f"**Posted by:** {username}")
                            st.write(f"**Location:** {user_obj.location}")
                            st.write("**Items:**")
                            for item in offering.items:
                                st.write(f"  • {item.name} - Quantity: {item.quantity} ({item.category.value})")
                            st.caption(f"Offering ID: {offering.id}")
                        
                        # Clear the text area
                        st.session_state.clear_donation_text = True
                        
                    except Exception as e:
                        st.error(f"Error creating offering: {e}")
                        st.exception(e)
    
    with tab2:
        st.subheader("📋 All Open Requests")
        st.info("Browse current requests to see what's needed")
        
        # Load requests from CSV
        try:
            requests_df = pd.read_csv("requests.csv")
            open_requests = requests_df[requests_df['status'] == 'open'].sort_values('urgency', ascending=False)
            
            if not open_requests.empty:
                # Filter options
                col1, col2, col3 = st.columns(3)
                with col1:
                    urgency_filter = st.selectbox(
                        "Filter by urgency",
                        ["All", "urgent", "high", "normal", "low"]
                    )
                
                # Apply filters
                if urgency_filter != "All":
                    open_requests = open_requests[open_requests['urgency'] == urgency_filter]
                
                st.write(f"**Showing {len(open_requests)} requests**")
                
                # Display requests in a nice format
                for idx, row in open_requests.iterrows():
                    urgency_emoji = {
                        'urgent': '🔴',
                        'high': '🟠', 
                        'normal': '🟡',
                        'low': '🟢'
                    }
                    
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"### {urgency_emoji.get(row['urgency'], '⚪')} {row['requester_name']}")
                            st.write(f"**Needs:** {row['items']}")
                            st.caption(f"📍 Posted on: {row['created_at'][:10]}")
                        
                        with col2:
                            st.write("")
                            st.write("")
                            urgency_label = row['urgency'].upper()
                            if row['urgency'] == 'urgent':
                                st.error(f"⚠️ {urgency_label}")
                            elif row['urgency'] == 'high':
                                st.warning(f"🔶 {urgency_label}")
                            else:
                                st.info(f"ℹ️ {urgency_label}")
                        
                        st.divider()
            else:
                st.info("No open requests at this time")
        
        except FileNotFoundError:
            st.warning("No requests file found")
        except Exception as e:
            st.error(f"Error loading requests: {e}")
    
    # Sidebar with quick stats
    with st.sidebar:
        st.subheader("📊 Your Contribution Stats")
        
        # Count offerings by this user
        try:
            offerings_df = pd.read_csv("offerings.csv")
            user_offerings = offerings_df[offerings_df['donor_name'] == username]
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Offerings", len(user_offerings))
            with col2:
                available = len(user_offerings[user_offerings['available'] == True])
                st.metric("Available", available)
            
            if not user_offerings.empty:
                st.divider()
                st.write("**Recent Offerings:**")
                for idx, row in user_offerings.tail(3).iterrows():
                    status = "✅ Available" if row['available'] else "📦 Donated"
                    st.caption(f"{status} - {row['items'][:30]}...")
        
        except FileNotFoundError:
            st.info("No offerings yet")

# Run the page
if __name__ == "__main__":
    st.set_page_config(page_title="Donate Items", layout="wide", page_icon="🎁")
    
    # Mock session state for testing
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.current_user = "Ballard Food Bank"
        st.session_state.user_type = "Organization"
    
    donate_page()