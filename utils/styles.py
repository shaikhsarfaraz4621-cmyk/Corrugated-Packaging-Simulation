import streamlit as st

def inject_custom_css():
    st.markdown("""
        <style>
        .reportview-container .main .block-container{
            padding-top: 2rem;
        }
        .dashboard-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1E3A8A;
            margin-bottom: 2rem;
            border-bottom: 3px solid #3B82F6;
            padding-bottom: 10px;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.8rem;
            color: #2563EB;
        }
        .stAlert {
            padding: 1rem;
            border-radius: 8px;
        }
        [data-testid="column"]:has(.sticky-chat) {
            position: -webkit-sticky;
            position: sticky;
            top: 3rem;
            align-self: flex-start;
            z-index: 999;
        }
        </style>
    """, unsafe_allow_html=True)
