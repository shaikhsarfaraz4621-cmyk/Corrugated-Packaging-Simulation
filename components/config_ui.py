import streamlit as st

def fill_dataframe_defaults(df, table_type):
    """Silent fail-safe recovery for nulls in Streamlit DataFrames."""
    defaults = {
        'machines': {'Count': 1, 'Input_Buffer_Capacity': 5, 'Jam_Weibull_Alpha': 1.5, 'Jam_Weibull_Beta': 0.0, 'Repair_Lognormal_Mu': 10.0, 'Repair_Lognormal_Sigma': 0.0},
        'jobs': {'Target_Demand': 1000, 'Batch_Size': 1000, 'Interarrival_Min': 2.0, 'Interarrival_Max': 5.0},
        'routings': {'Sequence_Order': 1, 'Process_Time_Per_Unit': 0.01, 'Setup_Time_Base': 5.0, 'Setup_Time_Std': 1.0, 'Requires_Forklift': False}
    }
    if table_type in defaults:
        for col, val in defaults[table_type].items():
            if col in df.columns:
                df[col] = df[col].fillna(val)
    return df

def render_config_tab():
    st.markdown("### Factory Floor Topology")
    st.info("Edit parameters below. Blank deletions instantly reset to fail-safe defaults.")
    
    st.subheader("Machines & Chaos Physics")
    m_df = st.data_editor(st.session_state['machines_df'], num_rows="dynamic", width="stretch")
    st.session_state['machines_df'] = fill_dataframe_defaults(m_df, 'machines')
    
    st.subheader("Order Demands")
    if 'Interarrival_Min' not in st.session_state['jobs_df'].columns:
        st.session_state['jobs_df']['Interarrival_Min'] = 2.0
        st.session_state['jobs_df']['Interarrival_Max'] = 5.0
    j_df = st.data_editor(st.session_state['jobs_df'], num_rows="dynamic", width="stretch")
    st.session_state['jobs_df'] = fill_dataframe_defaults(j_df, 'jobs')
    
    st.subheader("Production Routings")
    r_df = st.data_editor(st.session_state['routings_df'], num_rows="dynamic", width="stretch")
    st.session_state['routings_df'] = fill_dataframe_defaults(r_df, 'routings')
