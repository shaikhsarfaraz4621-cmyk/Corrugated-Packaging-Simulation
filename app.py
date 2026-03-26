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
    num_runs = st.number_input("Number of Runs", min_value=1, max_value=50, value=3)
    if st.button("🚀 Run Twin", type="primary", use_container_width=True):
        st.session_state['trigger_sim'] = True
        st.session_state['num_runs'] = num_runs
        
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
        st.subheader("Machine Chaos & Physics Settings")
        st.info("Lognormal & Weibull parameters dictate the setup variances and breakdown frequencies. Keep Buffer Capacities low to test fatigue blockages.")
        st.session_state['machines_df'] = st.data_editor(st.session_state['machines_df'], num_rows="dynamic", width="stretch")
        
        st.subheader("Order Demands")
        if 'Interarrival_Min' not in st.session_state['jobs_df'].columns:
            st.session_state['jobs_df']['Interarrival_Min'] = 2.0
            st.session_state['jobs_df']['Interarrival_Max'] = 5.0
        st.session_state['jobs_df'] = st.data_editor(st.session_state['jobs_df'], num_rows="dynamic", width="stretch")
        
        st.subheader("Production Routings")
        st.session_state['routings_df'] = st.data_editor(st.session_state['routings_df'], num_rows="dynamic", width="stretch")

# --- EXECUTION LOGIC ---
if st.session_state.get('trigger_sim', False):
    with st.spinner("🚀 Booting SimPy Engine... Calculating Human Chaos Variables..."):
        try:
            results_list = []
            runs = st.session_state.get('num_runs', 1)
            for i in range(runs):
                sim = CorrugatedSimulation(st.session_state['machines_df'], st.session_state['jobs_df'], st.session_state['routings_df'])
                results_list.append(sim.run())
            
            # Aggregate stats
            df_stats = pd.DataFrame({
                'Makespan': [r['Total_Time'] for r in results_list],
                'Lead_Time': [pd.DataFrame(r['Batch_Metrics'])['Flow_Time'].mean() for r in results_list],
                'Units': [pd.DataFrame(r['Batch_Metrics'])['Units'].sum() for r in results_list],
                'Efficiency': [(pd.DataFrame(r['Batch_Metrics'])['Active_Time'] / pd.DataFrame(r['Batch_Metrics'])['Flow_Time'] * 100).mean() for r in results_list],
                'Total_Blocked': [sum(m.get('blocked_time', 0) for m in r['Machine_Stats'].values()) for r in results_list],
                'Total_Starved': [sum(m.get('starved_time', 0) for m in r['Machine_Stats'].values()) for r in results_list],
                'Total_Jams': [r['Logs'][r['Logs']['Event'] == 'Jam Start'].shape[0] if not r['Logs'].empty and 'Event' in r['Logs'].columns else 0 for r in results_list]
            })
            
            all_batches, all_logs, all_wip, all_gantt = [], [], [], []
            machine_stats_agg = {m_id: {'working_time': 0, 'setup_time': 0, 'down_time': 0, 'starved_time':0, 'blocked_time':0, 'completed_operations': 0} for m_id in results_list[0]['Machine_Stats']}
            
            for run_idx, r in enumerate(results_list):
                run_id = f"Run_{run_idx+1}"
                
                bm = pd.DataFrame(r['Batch_Metrics'])
                bm['Run_ID'] = run_id
                all_batches.append(bm)
                
                lg = r['Logs'].copy()
                lg['Run_ID'] = run_id
                all_logs.append(lg)
                
                wip = r['WIP_Timeline'].copy()
                wip['Run_ID'] = run_id
                all_wip.append(wip)
                
                gantt = pd.DataFrame(r['Gantt_Log'])
                if not gantt.empty:
                    gantt['Run_ID'] = run_id
                    all_gantt.append(gantt)
                    
                for m_id, stats in r['Machine_Stats'].items():
                    for k in stats: machine_stats_agg[m_id][k] += stats[k]
                    
            for m_id in machine_stats_agg:
                for k in machine_stats_agg[m_id]: machine_stats_agg[m_id][k] /= runs

            def get_stats(col):
                mean = df_stats[col].mean()
                std = df_stats[col].std() if len(df_stats) > 1 else 0.0
                n = len(df_stats)
                ci95 = 1.96 * (std / math.sqrt(n)) if n > 1 else 0.0
                return {"mean": mean, "std": std, "ci95": ci95}
                
            final_result = {
                "Total_Time": df_stats['Makespan'].mean(),
                "Batch_Metrics": pd.concat(all_batches, ignore_index=True),
                "Machine_Stats": machine_stats_agg,
                "Logs": pd.concat(all_logs, ignore_index=True),
                "WIP_Timeline": pd.concat(all_wip, ignore_index=True),
                "Gantt_Log": pd.concat(all_gantt, ignore_index=True) if all_gantt else pd.DataFrame(),
                "Completed_Jobs": results_list[-1]["Completed_Jobs"],
                "MultiRunStats": {
                    'Makespan': get_stats('Makespan'),
                    'Lead_Time': get_stats('Lead_Time'),
                    'Units': get_stats('Units'),
                    'Efficiency': get_stats('Efficiency')
                },
                "df_stats": df_stats
            }
            
            st.session_state['simulation_results_list'] = results_list
            st.session_state['simulation_results'] = final_result
            st.session_state['trigger_sim'] = False
        except Exception as e:
            st.error(f"Engine Failure: {e}")
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
