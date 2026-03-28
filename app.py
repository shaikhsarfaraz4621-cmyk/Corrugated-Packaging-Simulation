import streamlit as st
import os
import math
import pandas as pd
from engine import CorrugatedSimulation

from utils.styles import inject_custom_css
from utils.data_handler import initialize_session_state, handle_file_upload
from components.dashboard import render_top_metrics, render_utilization_analysis, render_flow_dynamics, render_insights
from components.ai_assistant import render_ai_assistant

# --- PAGE CONFIG ---
st.set_page_config(page_title="Corrugated Factory Digital Twin", page_icon="📦", layout="wide")
inject_custom_css()
initialize_session_state()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/color/200/open-box.png", width=100)
    st.title("⚙️ Corrugated Setup")
    st.markdown("---")
    
    uploaded_file = st.file_uploader("Upload Box Factory Config", type=["xlsx"])
    if uploaded_file: handle_file_upload(uploaded_file)
        
    st.markdown("---")
    st.markdown("### 🛠️ Execution Controls")
    val = st.number_input("Number of Runs", min_value=1, max_value=50, value=st.session_state.get('num_runs', 3))
    if val is not None:
        st.session_state['num_runs'] = val
    num_runs = st.session_state['num_runs']

    if st.button("🚀 Run Twin", type="primary", use_container_width=True):
        st.session_state['trigger_sim'] = True
        # st.session_state['num_runs'] is already updated above
        
    if st.button("🔄 Factory Reset", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- MAIN UI ---
st.markdown('<div class="dashboard-header">📦 Corrugated Packaging Digital Twin</div>', unsafe_allow_html=True)
st.caption("Advanced Discrete-Event Simulation explicitly modeling Human Fatigue, Forklift Starvation, and Chaotic Machine Jams.")

col_center, col_right = st.columns([7, 3], gap="large")

with col_center:
    tab_sim, tab_config = st.tabs(["📊 Live Dashboards", "📝 Factory Setup"])

    with tab_config:
        from components.config_ui import render_config_tab
        render_config_tab()

# --- EXECUTION LOGIC ---
if st.session_state.get('trigger_sim', False):
    from controllers.simulation_runner import run_simulation_batch
    
    with st.spinner("🚀 Booting SimPy Engine... Calculating Human Chaos Variables..."):
        try:
            runs = st.session_state.get('num_runs', 1)
            r_list, f_res = run_simulation_batch(
                st.session_state['machines_df'], 
                st.session_state['jobs_df'], 
                st.session_state['routings_df'], 
                runs
            )
            st.session_state['simulation_results_list'] = r_list
            st.session_state['simulation_results'] = f_res
        except Exception as e:
            st.error(f"Engine Failure: {e}")
        finally:
            st.session_state['trigger_sim'] = False

# --- DASHBOARD RENDERING ---
if 'simulation_results' in st.session_state:
    results_agg = st.session_state['simulation_results']
    results_list = st.session_state.get('simulation_results_list', [results_agg])
    
    with col_center:
        with tab_sim:
            c1, c2 = st.columns([1, 4])
            with c1:
                run_options = ["All Runs (Aggregated)"] + [f"Run_{i+1}" for i in range(len(results_list))]
                selected_view = st.selectbox("📊 View Options:", run_options)
            
            results = results_agg if selected_view == "All Runs (Aggregated)" else results_list[int(selected_view.split("_")[1]) - 1]
            
            st.divider()
            render_top_metrics(results)
            st.divider()
            render_utilization_analysis(results, st.session_state['machines_df'])
            st.divider()
            render_flow_dynamics(results)
            st.divider()
            render_insights(results)
            
            with st.expander("📝 View Raw Simulation Logs"):
                st.dataframe(results["Logs"], use_container_width=True)

    with col_right:
        render_ai_assistant(results_agg, st.session_state['machines_df'], st.session_state['jobs_df'], st.session_state['routings_df'])
else:
    with col_center:
        with tab_sim:
            st.info("👋 Welcome! Click 'Run Twin' in the sidebar to dynamically simulate human limitations in Corrugated Box manufacturing.")
    with col_right:
        st.info("🤖 AI Analysis will appear here after the simulation runs.")
