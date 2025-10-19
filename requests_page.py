import streamlit as st
import pandas as pd
from models import CoordinationSystem, Needers, Shelter, TextParser

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
        elif user_type == "Person in Need":
            return Needers(name, location, contact), user_type
    
    return None, None

def request_page():
    """Main request page for people in need and shelters"""
    
    # Check if user is logged in
    if not st.session_state.get("logged_in", False):
        st.error("Please log in to access this page")
        return
    
    username = st.session_state.get("current_user")
    name = st.session_state.current_user
    df = pd.read_csv("user_information.csv", sep='|', engine="python")
    user_row = df[df['Name'] == name]
    user_type = user_row.iloc[0]['User Type']
    print(user_type)
    
    # Only allow Organizations and Person in Need to request
    if user_type not in ["Organization", "Person in Need"]:
        st.error("Only Organizations and People in Need can create requests")
        st.info("You are logged in as: Volunteer - Please use the Donate page instead")
        return
    
    # Load user object
    user_obj, _ = load_user_from_csv(username)
    if not user_obj:
        st.error("Error loading user information")
        return
    
    # Page header
    st.title("📝 Request Items")
    st.write(f"Welcome, **{username}**!")
    st.divider()
    
    # Search/Filter section at top
    st.subheader("🔍 Search Available Donations")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "Search for available donations",
            placeholder="e.g., blankets, food, medical supplies",
            help="Search through current offerings to find items you need"
        )
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("🔍 Search", use_container_width=True, type="primary"):
            st.session_state.search_performed = True
    
    # Display search results if search was performed
    if st.session_state.get("search_performed", False) and search_query:
        st.info(f"Searching for offerings matching: **{search_query}**")
        
        # Load and filter offerings
        try:
            offerings_df = pd.read_csv("offerings.csv")
            
            # Filter by search query
            matching_offerings = offerings_df[
                (offerings_df['items'].str.contains(search_query, case=False, na=False)) &
                (offerings_df['available'] == True)
            ]
            
            if not matching_offerings.empty:
                st.success(f"Found {len(matching_offerings)} matching offerings")
                
                for idx, row in matching_offerings.head(5).iterrows():
                    with st.expander(f"🎁 {row['donor_name']}"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Available:** {row['items']}")
                            st.caption(f"Posted: {row['created_at'][:10]}")
                        with col2:
                            st.button("📞 Contact", key=f"contact_{idx}", use_container_width=True)
            else:
                st.warning(f"No available offerings found matching '{search_query}'")
        
        except FileNotFoundError:
            st.warning("No offerings available yet")
    
    st.divider()
    
    # Main request section - Tabs for different views
    tab1, tab2 = st.tabs(["✍️ Create New Request", "📊 View All Offerings"])
    
    with tab1:
        st.subheader("Create a New Request")
        st.info("💡 Describe what you need in plain English. Our AI will parse it automatically!")
        
        # Text input for request
        request_text = st.text_area(
            "What do you need?",
            placeholder="Example: We urgently need 20 warm blankets and 50 cans of soup for the winter shelter\n\nOr: Need groceries for my family of 4, especially food for the kids",
            height=150,
            help="Be as specific as possible about quantities and urgency"
        )
        
        # Preview parsed items before submitting
        if request_text and len(request_text) > 5:
            with st.expander("🔍 Preview Parsed Items (AI Analysis)", expanded=False):
                with st.spinner("Analyzing your request..."):
                    try:
                        # Parse the text to show preview
                        parsed_items = TextParser.parse_text_to_items(request_text)
                        urgency = TextParser.analyze_urgency(request_text)
                        
                        st.write("**AI detected these items:**")
                        for item in parsed_items:
                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                st.write(f"• **{item.name}**")
                            with col2:
                                st.write(f"Qty: {item.quantity}")
                            with col3:
                                st.write(f"📦 {item.category.value}")
                        
                        # Show urgency
                        urgency_colors = {
                            'urgent': '🔴',
                            'high': '🟠',
                            'normal': '🟡',
                            'low': '🟢'
                        }
                        st.write(f"**Detected Urgency:** {urgency_colors.get(urgency, '⚪')} **{urgency.upper()}**")
                        st.caption("✨ Parsed automatically using AI")
                    except Exception as e:
                        st.error(f"Error parsing items: {e}")
        
        # Submit button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Post Request", 
                        type="primary", 
                        use_container_width=True,
                        disabled=not request_text or len(request_text) < 5):
                
                with st.spinner("Creating your request..."):
                    try:
                        # Create request using models.py
                        request = user_obj.create_request_from_text(request_text)
                        st.session_state.system.add_request(request)
                        
                        st.success("✅ Request posted successfully!")
                        st.balloons()
                        
                        # Show confirmation
                        with st.expander("✅ Request Details", expanded=True):
                            st.write(f"**Posted by:** {username}")
                            st.write(f"**Location:** {user_obj.location}")
                            st.write(f"**Urgency:** {request.urgency.upper()}")
                            st.write("**Items:**")
                            for item in request.items:
                                st.write(f"  • {item.name} - Quantity: {item.quantity} ({item.category.value})")
                            st.caption(f"Request ID: {request.id}")
                        
                        st.info("📢 Your request is now visible to all donors and will be matched by our AI system!")
                        
                    except Exception as e:
                        st.error(f"Error creating request: {e}")
                        st.exception(e)
    
    with tab2:
        st.subheader("All Available Offerings")
        st.info("Browse current donations to see what's available")
        
        # Load offerings from CSV
        try:
            offerings_df = pd.read_csv("offerings.csv")
            available_offerings = offerings_df[offerings_df['available'] == True]
            
            if not available_offerings.empty:
                # Category filter
                st.write(f"**Showing {len(available_offerings)} available offerings**")
                
                # Display offerings in a nice format
                for idx, row in available_offerings.iterrows():
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"### 🎁 {row['donor_name']}")
                            st.write(f"**Offering:** {row['items']}")
                            st.caption(f"📍 Posted on: {row['created_at'][:10]}")
                        
                        with col2:
                            st.write("")
                            st.write("")
                            if st.button("📞 Contact Donor", key=f"contact_offer_{idx}", use_container_width=True):
                                df = pd.read_csv("user_information.csv", sep='|', engine="python")
                                user_row = df[df['Name'] == name]
                                user_type = user_row.iloc[0]['User Type']
                                link = user_row.iloc[0]['Link']
                                phone = user_row.iloc[0]["Phone Number"]
                                st.markdown(f"""
**Contact information for {row['donor_name']}**

- 🌐 **Website:** {link if link else "N/A"}  
- 📞 **Phone Number:** {phone if phone else "N/A"}
""")

                        st.divider()
            else:
                st.info("No available offerings at this time")
        
        except FileNotFoundError:
            st.warning("No offerings file found")
        except Exception as e:
            st.error(f"Error loading offerings: {e}")
    
    # Sidebar with quick stats
    with st.sidebar:
        st.subheader("Your Request Stats")
        
        # Count requests by this user
        try:
            requests_df = pd.read_csv("requests.csv")
            user_requests = requests_df[requests_df['requester_name'] == username]
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Requests", len(user_requests))
            with col2:
                open_reqs = len(user_requests[user_requests['status'] == 'open'])
                st.metric("Open", open_reqs)
            
            if not user_requests.empty:
                st.divider()
                st.write("**Recent Requests:**")
                for idx, row in user_requests.tail(3).iterrows():
                    status_emoji = {
                        'open': '🟡',
                        'fulfilled': '✅',
                        'in_progress': '🔄',
                        'cancelled': '❌'
                    }
                    st.caption(f"{status_emoji.get(row['status'], '⚪')} {row['items'][:30]}...")
        
        except FileNotFoundError:
            st.info("No requests yet")

# Run the page
if __name__ == "__main__":
    st.set_page_config(page_title="Request Items", layout="wide", page_icon="📝")
    
    # Mock session state for testing
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.current_user = "Naren"
        st.session_state.user_type = "Person in Need"
    
    request_page()