import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import json
import requests
from datetime import datetime
import os
from streamlit_lottie import st_lottie
from streamlit_extras.colored_header import colored_header
from openai import OpenAI

from data_ingestion import start_ingestion_pipeline
from vector_store import query_hybrid_index, get_latest_documents
from compliance_analyzer import analyze_document_risk, categorize_by_jurisdiction
from notification_service import send_notification
from utils import format_datetime
from compliance_keywords import COMPLIANCE_KEYWORDS, RISK_LEVELS

# Initialize OpenAI client
try:
    # Try to get API key from Streamlit secrets first
    if 'openai' in st.secrets:
        openai_api_key = st.secrets.openai.api_key
    else:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    if not openai_api_key:
        st.warning("⚠️ OpenAI API key not found. Please configure it in Streamlit secrets or environment variables.")
        client = None
    else:
        client = OpenAI(api_key=openai_api_key)
except Exception as e:
    print(f"Error initializing OpenAI client: {str(e)}")
    client = None

# Page configuration
st.set_page_config(
    page_title="Financial Compliance Copilot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check if OpenAI API key is set
if not os.environ.get("OPENAI_API_KEY"):
    st.warning("⚠️ OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")

# Helper function to load Lottie animations
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = "landing"
if 'risk_threshold' not in st.session_state:
    st.session_state.risk_threshold = 0.7
if 'selected_jurisdiction' not in st.session_state:
    st.session_state.selected_jurisdiction = "All"
if 'pipeline_running' not in st.session_state:
    st.session_state.pipeline_running = False

# LANDING PAGE
if st.session_state.page == "landing":
    # Hide sidebar on landing page
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="collapsedControl"] {display: none;}
        section[data-testid="stSidebar"] {display: none;}
        .stDeployButton {display: none;}
        
        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes slideUp {
            from { transform: translateY(50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .landing-title {
            font-size: 4rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(90deg, #1E88E5, #5E35B1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: fadeIn 1.5s ease-in-out;
        }
        
        .landing-subtitle {
            font-size: 1.5rem;
            color: #5E35B1;
            margin-bottom: 2rem;
            animation: fadeIn 1.5s ease-in-out 0.3s both;
        }
        
        .landing-description {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 3rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
            animation: slideUp 1s ease-in-out 0.5s both;
        }
        
        .feature-card {
            background: white;
            border-radius: 15px;
            padding: 2rem;
            height: 100%;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
            animation: slideUp 0.8s ease-in-out both;
        }
        
        .feature-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.1);
        }
        
        .start-button {
            background: linear-gradient(90deg, #1E88E5, #5E35B1);
            color: white;
            font-size: 1.25rem;
            font-weight: 600;
            padding: 0.8rem 2rem;
            border-radius: 50px;
            border: none;
            cursor: pointer;
            width: 100%;
            text-align: center;
            transition: all 0.3s ease;
            box-shadow: 0 10px 20px rgba(30, 136, 229, 0.3);
            animation: pulse 2s infinite;
        }
        
        .start-button:hover {
            box-shadow: 0 15px 30px rgba(30, 136, 229, 0.5);
            transform: translateY(-3px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Centered content
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Title and subtitle
        st.markdown('<h1 class="landing-title">Financial Compliance Copilot</h1>', unsafe_allow_html=True)
        st.markdown('<p class="landing-subtitle">Real-time AI-powered compliance monitoring for financial institutions</p>', unsafe_allow_html=True)
        
        # Description
        st.markdown("""
        <div class="landing-description">
            <p style="font-size: 1.1rem; line-height: 1.6; color: #37474F; margin-bottom: 0;">
                Stay ahead of regulatory risks with our advanced AI-powered compliance monitoring system.
                Our platform continuously analyzes SEC filings, regulatory updates, and financial news to 
                identify potential compliance issues before they become problems.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Load and display Lottie animation
        lottie_url = "https://assets3.lottiefiles.com/packages/lf20_zq5rLt.json"  # Financial/data analysis animation
        lottie_json = load_lottieurl(lottie_url)
        if lottie_json:
            st_lottie(lottie_json, height=300, key="main_animation")
        
        # Feature cards in a 2x2 grid
        st.markdown("<h2 style='text-align: center; margin: 2rem 0 1.5rem; color: #212121;'>Key Features</h2>", unsafe_allow_html=True)
        
        feature_col1, feature_col2 = st.columns(2)
        
        with feature_col1:
            st.markdown("""
            <div class="feature-card" style="background: linear-gradient(135deg, #E3F2FD, #BBDEFB); animation-delay: 0.9s;">
                <div style="position: absolute; top: 0; right: 0; width: 100px; height: 100px; opacity: 0.2;
                     background: radial-gradient(circle, #1E88E5, transparent); border-radius: 50%;"></div>
                <h3 style="color: #1565C0; font-size: 1.5rem; margin-bottom: 1rem; position: relative;">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36" fill="#1565C0" style="margin-right: 8px;">
                        <path d="M3.5 18.5L9.5 12.5L13.5 16.5L22 6.92L20.59 5.5L13.5 13.5L9.5 9.5L2 17L3.5 18.5Z"></path>
                    </svg>
                    Real-time Monitoring
                </h3>
                <p style="color: #1565C0; font-size: 1.1rem; line-height: 1.4;">
                    Continuous analysis of financial data and regulatory updates as they happen.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="feature-card" style="background: linear-gradient(135deg, #E0F7FA, #B2EBF2); animation-delay: 1.3s; margin-top: 1rem;">
                <div style="position: absolute; top: 0; right: 0; width: 100px; height: 100px; opacity: 0.2;
                     background: radial-gradient(circle, #00BCD4, transparent); border-radius: 50%;"></div>
                <h3 style="color: #0097A7; font-size: 1.5rem; margin-bottom: 1rem; position: relative;">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36" fill="#0097A7" style="margin-right: 8px;">
                        <path d="M12 22C6.49 22 2 17.51 2 12S6.49 2 12 2s10 4.04 10 9c0 3.31-2.69 6-6 6h-1.77c-.28 0-.5.22-.5.5 0 .12.05.23.13.33.41.47.64 1.06.64 1.67A2.5 2.5 0 0 1 12 22zm0-18c-4.41 0-8 3.59-8 8s3.59 8 8 8c.28 0 .5-.22.5-.5 0-.16-.08-.28-.14-.35-.41-.46-.63-1.05-.63-1.65a2.5 2.5 0 0 1 2.5-2.5H16c2.21 0 4-1.79 4-4 0-3.86-3.59-7-8-7z"></path>
                    </svg>
                    Instant Alerts
                </h3>
                <p style="color: #0097A7; font-size: 1.1rem; line-height: 1.4;">
                    Receive notifications when high-risk issues are detected.
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with feature_col2:
            st.markdown("""
            <div class="feature-card" style="background: linear-gradient(135deg, #E8EAF6, #C5CAE9); animation-delay: 1.1s;">
                <div style="position: absolute; top: 0; right: 0; width: 100px; height: 100px; opacity: 0.2;
                     background: radial-gradient(circle, #5E35B1, transparent); border-radius: 50%;"></div>
                <h3 style="color: #3949AB; font-size: 1.5rem; margin-bottom: 1rem; position: relative;">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36" fill="#3949AB" style="margin-right: 8px;">
                        <path d="M12 1L3 5V11C3 16.55 6.84 21.74 12 23C17.16 21.74 21 16.55 21 11V5L12 1ZM12 11.99H19C18.47 16.11 15.72 19.78 12 20.93V12H5V6.3L12 3.19V11.99Z"></path>
                    </svg>
                    Risk Assessment
                </h3>
                <p style="color: #3949AB; font-size: 1.1rem; line-height: 1.4;">
                    Advanced algorithms identify and score potential compliance risks.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="feature-card" style="background: linear-gradient(135deg, #E8F5E9, #C8E6C9); animation-delay: 1.5s; margin-top: 1rem;">
                <div style="position: absolute; top: 0; right: 0; width: 100px; height: 100px; opacity: 0.2;
                     background: radial-gradient(circle, #4CAF50, transparent); border-radius: 50%;"></div>
                <h3 style="color: #388E3C; font-size: 1.5rem; margin-bottom: 1rem; position: relative;">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="36" height="36" fill="#388E3C" style="margin-right: 8px;">
                        <path d="M21 11c0 5.55-3.84 10.74-9 12-5.16-1.26-9-6.45-9-12V5l9-4 9 4v6m-9 10c3.75-1 7-5.46 7-9.78V6.3l-7-3.12L5 6.3v4.92C5 15.54 8.25 20 12 21m2.8-10V9.5C14.8 8.1 13.4 7 12 7S9.2 8.1 9.2 9.5V11c-.6 0-1.2.6-1.2 1.2v3.5c0 .7.6 1.3 1.2 1.3h5.5c.7 0 1.3-.6 1.3-1.2v-3.5c0-.7-.6-1.3-1.2-1.3m-1.3 0h-3V9.5c0-.8.7-1.3 1.5-1.3s1.5.5 1.5 1.3V11z"></path>
                    </svg>
                    AI-powered Q&A
                </h3>
                <p style="color: #388E3C; font-size: 1.1rem; line-height: 1.4;">
                    Get instant answers to your compliance questions.
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # Get Started button
        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
        if st.button("Start Real-Time Monitoring", key="get_started_btn", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
        
        # Footer
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0; color: #757575; margin-top: 2rem;">
            <p>© 2023 Financial Compliance Copilot | Powered by AI and Real-time Analytics</p>
        </div>
        """, unsafe_allow_html=True)

# DASHBOARD PAGE
else:
    # Custom styling for dashboard
    st.markdown("""
    <style>
    .dashboard-header {
        background: linear-gradient(to right, #1E88E5, #5E35B1);
        padding: 1px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .dashboard-header-content {
        background: white;
        border-radius: 8px;
        padding: 10px 20px;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .document-card {
        background: white;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .tab-content {
        animation: fadeIn 0.5s ease-out;
    }
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar for controls
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding-bottom: 1rem;">
            <h2 style="color: #1E88E5;">Control Panel</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Jurisdiction filter
        st.subheader("Jurisdiction Filter")
        selected_jurisdiction = st.selectbox(
            "Select Jurisdiction",
            ["All", "US", "EU", "INDIA", "ASIA", "GLOBAL"],
            index=0,
            key="jurisdiction_select"
        )
        st.session_state.selected_jurisdiction = selected_jurisdiction
        
        # Risk threshold slider
        st.subheader("Risk Threshold")
        risk_threshold = st.slider(
            "Set Risk Threshold",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.risk_threshold,
            step=0.1,
            format="%.1f",
            key="risk_slider"
        )
        st.session_state.risk_threshold = risk_threshold
        
        # Date range filter
        st.subheader("Date Range")
        date_range = st.date_input(
            "Select Date Range",
            value=(datetime.now().date(), datetime.now().date()),
            key="date_range"
        )
        
        # Pipeline control
        st.subheader("Data Pipeline Control")
        pipeline_col1, pipeline_col2 = st.columns(2)
        
        with pipeline_col1:
            if st.button("Start Pipeline", key="start_pipeline", use_container_width=True):
                # Start the data ingestion pipeline
                start_ingestion_pipeline()
                st.session_state.pipeline_running = True
        
        with pipeline_col2:
            if st.button("Stop Pipeline", key="stop_pipeline", use_container_width=True):
                # In a real application, this would stop the pipeline
                st.session_state.pipeline_running = False
        
        # Display pipeline status
        st.markdown(
            f"""
            <div style="background: {'#4CAF50' if st.session_state.pipeline_running else '#F44336'}; 
                color: white; padding: 0.5rem; border-radius: 5px; text-align: center; margin-top: 0.5rem;">
                {'Running' if st.session_state.pipeline_running else 'Stopped'}
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Notification settings
        st.subheader("Notification Settings")
        
        phone_number = st.text_input(
            "Phone Number", 
            placeholder="+1234567890",
            help="Enter your phone number in E.164 format (e.g., +1234567890)",
            key="phone_number"
        )
        if phone_number:
            # Update the notification service with the phone number
            import notification_service
            notification_service.NOTIFICATION_PHONE_NUMBER = phone_number
            st.success(f"✅ Phone number {phone_number} configured for notifications")
        
        # Manual notification test
        st.subheader("Send Test Alert")
        manual_notification = st.text_area("Notification Message", placeholder="Enter alert message here...", key="manual_notification")
        if st.button("Send Alert", key="send_alert"):
            if manual_notification:
                if not phone_number:
                    st.error("❌ Please enter a phone number to receive notifications")
                else:
                    # Create a test document for the notification
                    test_doc = {
                        "id": f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                        "risk_score": 0.8,
                        "jurisdiction": selected_jurisdiction if selected_jurisdiction != "All" else "GLOBAL",
                        "source": "Test Alert",
                        "content": manual_notification
                    }
                    
                    # Send notification with test document
                    notification_result = send_notification(manual_notification, test_doc["id"], test_doc["risk_score"])
                    if notification_result["success"]:
                        if notification_result.get("dev_mode", False):
                            st.success(f"✅ Development Mode: Test notification sent successfully! ({notification_result['notifications_sent']} notifications sent)\nCheck your terminal/console for the notification logs.")
                        else:
                            st.success(f"✅ Test notification sent successfully! ({notification_result['notifications_sent']} notifications sent)")
                    else:
                        error_msg = "\n".join(notification_result["errors"])
                        st.error(f"❌ Failed to send notifications:\n{error_msg}")
            else:
                st.warning("⚠️ Please enter a notification message.")
    
    # Main dashboard area
    colored_header(
        label="Financial Compliance Copilot",
        description="Real-time compliance monitoring for financial institutions",
        color_name="blue-70"
    )
    
    # Create tabs
    tabs = st.tabs(["Dashboard", "Document Analysis", "Q&A"])
    
    # Tab 1: Dashboard
    with tabs[0]:
        st.markdown("""
        <div class="dashboard-header">
            <div class="dashboard-header-content">
                <h2 style="color: #1E88E5; margin-bottom: 5px;">Real-Time Compliance Dashboard</h2>
                <p style="color: #757575; margin-top: 0;">Monitor compliance risks across your organization</p>
            </div>
        </div>
        <div class="tab-content">
        """, unsafe_allow_html=True)
        
        # Dashboard metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h3 style="color: #F44336; font-size: 1rem; margin: 0;">High Risk Documents</h3>
                <p style="font-size: 2.5rem; font-weight: bold; margin: 10px 0; color: #F44336;">12</p>
                <p style="color: #757575; font-size: 0.8rem; margin: 0;">+3 in the last 24 hours</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <h3 style="color: #FFC107; font-size: 1rem; margin: 0;">Medium Risk Documents</h3>
                <p style="font-size: 2.5rem; font-weight: bold; margin: 10px 0; color: #FFC107;">28</p>
                <p style="color: #757575; font-size: 0.8rem; margin: 0;">+5 in the last 24 hours</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card">
                <h3 style="color: #4CAF50; font-size: 1rem; margin: 0;">Compliant Documents</h3>
                <p style="font-size: 2.5rem; font-weight: bold; margin: 10px 0; color: #4CAF50;">143</p>
                <p style="color: #757575; font-size: 0.8rem; margin: 0;">+18 in the last 24 hours</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Risk distribution chart
        st.markdown("""
        <div class="metric-card" style="margin-top: 20px;">
            <h3 style="color: #1E88E5; font-size: 1.2rem; margin-bottom: 15px;">Risk Distribution by Jurisdiction</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Create a Plotly pie chart for risk distribution
        jurisdictions = ["US", "EU", "UK", "APAC", "Other"]
        risk_counts = [42, 35, 18, 12, 8]
        colors = ['#F44336', '#FF9800', '#FFC107', '#4CAF50', '#2196F3']
        
        fig = go.Figure(data=[go.Pie(
            labels=jurisdictions,
            values=risk_counts,
            hole=.4,
            marker_colors=colors
        )])
        
        fig.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            height=300,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True) # Close tab-content div
    
    # Tab 2: Document Analysis
    with tabs[1]:
        st.markdown("""
        <div class="dashboard-header" style="background: linear-gradient(to right, #5E35B1, #7B1FA2);">
            <div class="dashboard-header-content">
                <h2 style="color: #5E35B1; margin-bottom: 5px;">Document Analysis</h2>
                <p style="color: #757575; margin-top: 0;">Search and analyze compliance documents from multiple sources</p>
            </div>
        </div>
        <div class="tab-content">
        """, unsafe_allow_html=True)
        
        # Search and filter
        st.markdown("""
        <div class="metric-card" style="margin-bottom: 20px;">
            <h3 style="color: #5E35B1; margin-bottom: 15px; font-size: 1.2rem;">Search & Filter</h3>
        </div>
        """, unsafe_allow_html=True)
        
        search_col, filter_col = st.columns([2, 1])
        
        with search_col:
            search_query = st.text_input("Search Documents", placeholder="Enter keywords or document ID")
        
        with filter_col:
            min_risk = st.select_slider(
                "Minimum Risk Level",
                options=["Low", "Medium", "High", "Critical"],
                value="Low"
            )
        
        # Recent documents
        st.markdown("""
        <div class="metric-card" style="margin-bottom: 20px;">
            <h3 style="color: #5E35B1; margin-bottom: 15px; font-size: 1.2rem;">Recent Documents</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Get documents from vector store
        documents = get_latest_documents(
            jurisdiction=selected_jurisdiction if selected_jurisdiction != "All" else None,
            min_risk=min_risk,
            search_query=search_query if search_query else None
        )
        
        if documents:
            for doc in documents:
                risk_color = "#F44336" if doc["risk_score"] >= 0.8 else "#FF9800" if doc["risk_score"] >= 0.6 else "#FFC107" if doc["risk_score"] >= 0.4 else "#4CAF50"
                
                st.markdown(f"""
                <div class="document-card" style="border-left: 5px solid {risk_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <div>
                            <span style="font-weight: bold; color: #212121;">{doc['id']}</span>
                            <span style="color: #757575; font-size: 0.9rem; margin-left: 10px;">{doc['date']}</span>
                        </div>
                        <div style="background: {risk_color}; color: white; padding: 3px 8px; border-radius: 20px; font-size: 0.8rem;">
                            Risk: {doc['risk_score']:.2f}
                        </div>
                    </div>
                    <p style="margin: 5px 0; font-weight: bold; color: #212121;">{doc['title']}</p>
                    <p style="margin: 5px 0; color: #212121;"><strong>Source:</strong> {doc['source']}</p>
                    <p style="margin: 5px 0; color: #212121;"><strong>Jurisdiction:</strong> {doc['jurisdiction']}</p>
                    <p style="margin: 5px 0; color: #212121;"><strong>Keywords:</strong> {', '.join(doc['keywords'])}</p>
                    <p style="margin: 5px 0; color: #212121;"><strong>Summary:</strong> {doc['summary']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Analyze {doc['id']}", key=f"analyze_{doc['id']}"):
                    with st.spinner("Analyzing document..."):
                        analysis_result = analyze_document_risk(doc['id'], doc['content'])
                        st.json(analysis_result)
        else:
            st.info("No documents matching the current filters.")
        
        # Live document updates
        st.markdown("""
        <div class="metric-card" style="margin: 20px 0;">
            <h3 style="color: #00BCD4; margin-bottom: 15px; font-size: 1.2rem;">Live Document Updates</h3>
        </div>
        """, unsafe_allow_html=True)
        
        doc_stream = st.empty()
        
        if st.session_state.pipeline_running:
            with doc_stream.container():
                for i in range(3):
                    risk_score = 0.3 + i*0.2
                    risk_color = "#F44336" if risk_score >= 0.8 else "#FF9800" if risk_score >= 0.6 else "#FFC107" if risk_score >= 0.4 else "#4CAF50"
                    
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.8); border-radius: 8px; padding: 12px; margin-bottom: 10px; 
                         border-left: 4px solid {risk_color}; animation: fadeIn 0.5s ease-in-out;">
                        <div style="display: flex; justify-content: space-between;">
                            <strong>New Document Detected:</strong> SEC-{1000+i}-{datetime.now().strftime('%H%M%S')}
                            <span style="color: #757575;">{datetime.now().strftime('%H:%M:%S')}</span>
                        </div>
                        <div style="margin-top: 5px;">
                            <span style="background: {risk_color}; color: white; padding: 2px 6px; border-radius: 20px; font-size: 0.8rem;">
                                Risk Score: {risk_score:.2f}
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center; padding: 30px; color: #757575; background: rgba(236, 239, 241, 0.5); border-radius: 8px;">
                <p>Start real-time monitoring to see live document updates</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True) # Close tab-content div
    
    # Tab 3: Q&A
    with tabs[2]:
        st.markdown("""
        <div class="dashboard-header" style="background: linear-gradient(to right, #00BCD4, #00ACC1);">
            <div class="dashboard-header-content">
                <h2 style="color: #00BCD4; margin-bottom: 5px;">Compliance Q&A</h2>
                <p style="color: #757575; margin-top: 0;">Get instant answers to your compliance questions</p>
            </div>
        </div>
        <div class="tab-content">
        """, unsafe_allow_html=True)
        
        # Check if OpenAI is properly configured
        if not client:
            st.error("❌ OpenAI integration is not properly configured. Please check your API key.")
        else:
            # Q&A interface
            st.markdown("""
            <div class="metric-card" style="margin-bottom: 30px;">
                <p style="color: #00BCD4; font-size: 1.1rem; margin-bottom: 15px;">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="#00BCD4" style="vertical-align: middle; margin-right: 8px;">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92c-.5.51-.86.97-1.04 1.69-.08.32-.13.68-.13 1.14h-2v-.5c0-.46.08-.9.22-1.31.2-.58.53-1.1.95-1.52l1.24-1.26c.46-.44.68-1.1.55-1.8-.13-.72-.69-1.33-1.39-1.53-1.11-.31-2.14.32-2.47 1.27-.12.35-.43.58-.79.58h-.13c-.55-.06-.98-.57-.93-1.12.12-1.54 1.33-2.82 2.89-3.14 1.66-.35 3.29.54 3.93 2.2.58 1.5-.14 2.99-1.1 3.89z"></path>
                    </svg>
                    Ask any question about financial regulations and compliance
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Q&A input
            user_question = st.text_input(
                "Ask a compliance question",
                placeholder="Example: What are the latest SEC regulations on ESG reporting?",
                key="qa_input"
            )
            
            # Jurisdiction filter
            st.markdown("<p style='color: #757575; margin-bottom: 5px;'>Jurisdiction Context</p>", unsafe_allow_html=True)
            
            qa_jurisdiction = st.radio(
                "",
                options=["US", "EU", "INDIA", "ASIA", "GLOBAL"],
                index=0,
                horizontal=True,
                label_visibility="collapsed"
            )
            
            if user_question:
                with st.spinner("Searching for relevant information..."):
                    try:
                        # Query the vector store
                        search_results = query_hybrid_index(
                            query=user_question,
                            jurisdiction=qa_jurisdiction if qa_jurisdiction != "GLOBAL" else None,
                            top_k=3
                        )
                        
                        # Prepare context for OpenAI
                        context = "\n\n".join([
                            f"Document {i+1}:\n{result['excerpt']}"
                            for i, result in enumerate(search_results)
                        ])
                        
                        # Generate answer using OpenAI
                        response = client.chat.completions.create(
                            model="gpt-4",
                            messages=[
                                {
                                    "role": "system",
                                    "content": """You are a financial compliance expert assistant. 
                                    Your task is to provide accurate, clear, and concise answers to questions about financial regulations and compliance.
                                    Base your answers on the provided context documents, and clearly indicate if you're unsure about any information.
                                    Format your responses with clear sections and bullet points where appropriate."""
                                },
                                {
                                    "role": "user",
                                    "content": f"""Question: {user_question}\n\nContext:\n{context}\n\nPlease provide a comprehensive answer based on the context provided."""
                                }
                            ],
                            max_tokens=1000
                        )
                        
                        answer = response.choices[0].message.content
                        
                        # Display answer
                        st.markdown("""
                        <div class="dashboard-header" style="background: linear-gradient(to right, #00BCD4, #00ACC1); margin: 20px 0;">
                            <div class="dashboard-header-content">
                                <h3 style="color: #00BCD4; margin-bottom: 10px;">Answer</h3>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div class="metric-card">
                            <p style="color: #212121; line-height: 1.6;">
                                {answer}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Display sources
                        st.markdown("""
                        <div class="dashboard-header" style="margin: 20px 0;">
                            <div class="dashboard-header-content">
                                <h3 style="color: #00BCD4; margin-bottom: 10px;">Sources</h3>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        for i, result in enumerate(search_results):
                            with st.expander(f"Source {i+1}: {result['title']}"):
                                st.markdown(f"""
                                <div class="metric-card" style="padding: 10px;">
                                    <p><strong>Document ID:</strong> {result['id']}</p>
                                    <p><strong>Relevance Score:</strong> {result['score']:.2f}</p>
                                    <p><strong>Date:</strong> {result['date']}</p>
                                    <p><strong>Excerpt:</strong> {result['excerpt']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    except Exception as e:
                        st.error(f"❌ Error generating answer: {str(e)}")
                        st.info("Please make sure your OpenAI API key is properly configured and has sufficient credits.")
        
        st.markdown("</div>", unsafe_allow_html=True)