import streamlit as st
import pandas as pd
import plotly.express as px

def render_top_metrics(results):
    total_time = results["Total_Time"]
    df_batches = results["Batch_Metrics"]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Production Makespan", f"{round(total_time, 1)} min")
    m2.metric("Total Batches Finished", len(df_batches))
    
    total_units = df_batches['Units'].sum()
    m3.metric("Total Success Units", int(total_units))
    
    total_jams = results["Logs"][results["Logs"]["Event"] == "Jam Start"].shape[0] if not results["Logs"].empty else 0
    m4.metric("Total Machine Jams", total_jams)

def render_utilization_analysis(results, res_machines_df):
    total_time = results["Total_Time"]
    stats = results["Machine_Stats"]
    
    utilization_data = []
    for m_id, m_stat in stats.items():
        count = int(res_machines_df[res_machines_df['Machine_ID'] == m_id]['Count'].values[0])
        avail = total_time * count
        
        util = (m_stat['working_time'] / avail) * 100 if avail > 0 else 0
        setup = (m_stat['setup_time'] / avail) * 100 if avail > 0 else 0
        fail = (m_stat['down_time'] / avail) * 100 if avail > 0 else 0
        starved = (m_stat['starved_time'] / avail) * 100 if avail > 0 else 0
        blocked = (m_stat['blocked_time'] / avail) * 100 if avail > 0 else 0
        idle = 100 - (util + setup + fail + starved + blocked)
        
        for t, v in [("Processing", util), ("Setup (Changeover)", setup), ("Failed (Jam)", fail), 
                     ("Starved (Forklift)", starved), ("Blocked (Queue Limit)", blocked), ("Idle", idle)]:
            utilization_data.append({"Machine": m_id, "State": t, "Percentage": v})
            
    df_util = pd.DataFrame(utilization_data)
    
    st.subheader("🔍 Bottleneck Forensics: Human Chaos Breakdown")
    fig_util = px.bar(
        df_util, x="Machine", y="Percentage", color="State",
        title="Comprehensive Machine State Breakdown",
        color_discrete_map={
            "Processing": "#10b981", "Setup (Changeover)": "#f59e0b", 
            "Failed (Jam)": "#ef4444", "Starved (Forklift)": "#8b5cf6", 
            "Blocked (Queue Limit)": "#f97316", "Idle": "#9ca3af"
        }
    )
    st.plotly_chart(fig_util, use_container_width=True)

def render_flow_dynamics(results):
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("📦 WIP Backpressure (Queue)")
        if "Run_ID" in results["WIP_Timeline"].columns:
            sel_run_wip = st.selectbox("Filter WIP Chart by Run:", ["All Runs"] + list(results["WIP_Timeline"]["Run_ID"].unique()), key="dashboard_wip_run")
            if sel_run_wip == "All Runs":
                wip_render_df = results["WIP_Timeline"]
                fig_wip = px.line(wip_render_df, x="Time", y="Global_WIP", color="Run_ID", title="Cumulative Batches (All Runs)", line_shape='hv')
            else:
                wip_render_df = results["WIP_Timeline"][results["WIP_Timeline"]["Run_ID"] == sel_run_wip]
                fig_wip = px.area(wip_render_df, x="Time", y="Global_WIP", title=f"Cumulative Batches ({sel_run_wip})", line_shape='hv', color_discrete_sequence=['#3b82f6'])
            st.plotly_chart(fig_wip, use_container_width=True)
        else:
            wip_render_df = results["WIP_Timeline"]
            fig_wip = px.area(wip_render_df, x="Time", y="Global_WIP", title="Cumulative Batches in Transit", line_shape='hv', color_discrete_sequence=['#3b82f6'])
            st.plotly_chart(fig_wip, use_container_width=True)
            
        # Top 3 WIP Contributors
        m_cols = [c for c in wip_render_df.columns if c not in ['Time', 'Global_WIP', 'Run', 'Run_ID', 'WIP']]
        if len(m_cols) > 0:
            st.markdown("<br>🔥 **Top 3 WIP Queue Offenders (Bottlenecks):**", unsafe_allow_html=True)
            st.caption("Average number of batches physically waiting in the queue buffer.")
            q_sums = wip_render_df[m_cols].mean().sort_values(ascending=False).head(3)
            cc = st.columns(3)
            for i, (m, val) in enumerate(q_sums.items()):
                cc[i].metric(label=f"#{i+1} Bottleneck", value=f"{round(val, 1)}", delta=f"{m}", delta_color="off")
        
    with c_right:
        st.subheader("⏳ Machine Status Timeline")
        gdf = results.get("Gantt_Log", pd.DataFrame())
        if not gdf.empty:
            machine_options = gdf["Category_ID"].unique().tolist()
            
            if "Run_ID" in gdf.columns and len(gdf["Run_ID"].unique()) > 1:
                run_options = gdf["Run_ID"].unique().tolist()
                c_sel1, c_sel2 = st.columns(2)
                sel_run = c_sel1.selectbox("Select Run:", run_options)
                sel_m = c_sel2.selectbox("Select Machine Line:", machine_options)
                m_gdf = gdf[(gdf["Category_ID"] == sel_m) & (gdf["Run_ID"] == sel_run)].sort_values("Start")
                run_label = f"({sel_run})"
            else:
                sel_m = st.selectbox("Select Machine Line:", machine_options)
                m_gdf = gdf[gdf["Category_ID"] == sel_m].sort_values("Start")
                run_label = ""
                
            points = []
            last_end = 0
            
            if "df_stats" in results and "Run_ID" in gdf.columns and len(gdf["Run_ID"].unique()) > 1:
                run_idx = int(sel_run.split("_")[1]) - 1
                sp_total_time = results["df_stats"].iloc[run_idx]["Makespan"]
            else:
                sp_total_time = results["Total_Time"]
                
            for _, row in m_gdf.iterrows():
                if row["Start"] > last_end:
                    points.append({"Time": last_end, "State": "Idle"})
                    points.append({"Time": row["Start"], "State": "Idle"})
                points.append({"Time": row["Start"], "State": row["State"]})
                points.append({"Time": row["Finish"], "State": row["State"]})
                last_end = max(last_end, row["Finish"])
            if last_end < sp_total_time:
                points.append({"Time": last_end, "State": "Idle"})
                points.append({"Time": sp_total_time, "State": "Idle"})
                
            fig_gantt = px.line(pd.DataFrame(points), x="Time", y="State", title=f"{sel_m} Execution Timeline {run_label}", line_shape='hv')
            fig_gantt.update_yaxes(categoryorder="array", categoryarray=["Failed", "Blocked", "Starved", "Idle", "Setup", "Processing"])
            st.plotly_chart(fig_gantt, use_container_width=True)

def render_insights(results):
    st.subheader("💡 Corrugated Process Forensics & Insights")
    stats = results.get("Machine_Stats", {})
    
    # Fatigue Blocking Insight
    most_blocked = ""
    max_block_time = 0
    for m, mstat in stats.items():
        if mstat.get('blocked_time', 0) > max_block_time:
            max_block_time = mstat['blocked_time']
            most_blocked = m
    if max_block_time > 0:
        st.warning(f"🚨 **Fatigue / Floor Space Bottleneck Detected:** The downstream queue for **{most_blocked}** frequently saturated. This mechanically forced the upstream machine to permanently halt for a total of **{round(max_block_time, 1)} minutes**, effectively suffocating throughput. *Recommendation: Assign an extra operator or expand buffer capacity.*")

    # Logistics Starvation Insight
    most_starved = ""
    max_starve_time = 0
    for m, mstat in stats.items():
        if mstat.get('starved_time', 0) > max_starve_time:
            max_starve_time = mstat['starved_time']
            most_starved = m
    if max_starve_time > 0:
        st.info(f"🚚 **Forklift Logistics Delay:** The **{most_starved}** spent **{round(max_starve_time, 1)} minutes** idling because the shared Forklifts were busy elsewhere. Upstream components are waiting on logistics before they can even begin setups. *Recommendation: Dedicate a localized forklift just for this machine.*")

    # Jam Breakdowns Insight
    logs = results.get("Logs", pd.DataFrame())
    if not logs.empty and "Event" in logs.columns:
        jams = logs[logs["Event"] == "Jam Start"].shape[0]
        if jams > 0:
            st.error(f"🔧 **Quality Maintenance Error:** The simulation statistically rolled **{jams} critical machine jams** due to glue viscosity/maintenance failures, cascading severe downtime across the shift.")
