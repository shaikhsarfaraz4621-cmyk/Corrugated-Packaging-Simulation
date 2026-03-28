import streamlit as st
from utils.data_handler import fill_dataframe_defaults

def render_config_tab():
    st.markdown("### Factory Floor Topology")
    st.info("Edit parameters below. Blank deletions instantly reset to previous valid values.")
    
    st.subheader("Machines & Chaos Physics")
    m_df = st.data_editor(st.session_state['machines_df'], num_rows="dynamic", width="stretch")
    st.session_state['machines_df'] = fill_dataframe_defaults(m_df, 'machines', st.session_state['machines_df'])
    
    st.subheader("Order Demands")
    if 'Interarrival_Min' not in st.session_state['jobs_df'].columns:
        st.session_state['jobs_df']['Interarrival_Min'] = 2.0
        st.session_state['jobs_df']['Interarrival_Max'] = 5.0
    j_df = st.data_editor(st.session_state['jobs_df'], num_rows="dynamic", width="stretch")
    st.session_state['jobs_df'] = fill_dataframe_defaults(j_df, 'jobs', st.session_state['jobs_df'])
    
    st.subheader("Production Routings")
    r_df = st.data_editor(st.session_state['routings_df'], num_rows="dynamic", width="stretch")
    st.session_state['routings_df'] = fill_dataframe_defaults(r_df, 'routings', st.session_state['routings_df'])
