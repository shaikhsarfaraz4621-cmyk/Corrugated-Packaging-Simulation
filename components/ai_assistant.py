import streamlit as st
from openai import OpenAI
import pandas as pd

def get_ai_context(results, machines_df):
    total_time = results.get("Total_Time", 0)
    logs = results.get("Logs", pd.DataFrame())
    stats = results.get("Machine_Stats", {})
    
    total_jams = 0
    if not logs.empty and "Event" in logs.columns:
        total_jams = logs[logs["Event"] == "Jam Start"].shape[0]
        
    total_blocked = sum(m.get('blocked_time', 0) for m in stats.values())
    total_starved = sum(m.get('starved_time', 0) for m in stats.values())
    
    if "df_stats" in results and len(results["df_stats"]) > 1:
        df = results["df_stats"]
        n = len(df)
        
        def calc_stats(series):
            mean = series.mean()
            std = series.std()
            var = series.var()
            ci = 1.96 * (std / (n ** 0.5)) if n > 0 else 0
            return f"{round(mean,1)} (SD: {round(std,1)}, Var: {round(var,1)}, 95%CI: ±{round(ci,1)})"
            
        m_span = calc_stats(df['Makespan'])
        m_blk = calc_stats(df['Total_Blocked'])
        m_strv = calc_stats(df['Total_Starved'])
        m_jams = calc_stats(df['Total_Jams'])
        
        stat_block = f"""
        MULTIPLE RUNS DETECTED ({n} iterations). 
        You MUST use the following Descriptive Statistics (Mean, SD, Variance, 95% CI) to answer the user's "What-If" scenarios to explain if a bottleneck is a guaranteed systemic constraint or simply statistical variance:
        - Makespan: {m_span} min
        - Total Fatigue Blocked Time: {m_blk} min
        - Total Forklift Starved Time: {m_strv} min
        - Total Machine Jams: {m_jams}
        """
    else:
        stat_block = f"""
        SINGLE RUN EXECUTED.
        - Makespan: {round(total_time, 1)} min.
        - Total Machine Jams: {total_jams} (Due to glue/ink maintenance failures).
        - Total Time Blocked by Fatigue: {round(total_blocked, 1)} min.
        - Total Time Starved by Logistics: {round(total_starved, 1)} min.
        """
        
    context = f"""
    You are an expert Factory Consultant for an industrial Corrugated Box manufacturing plant. 
    Analyze the recent discrete-event simulation results detailing heavy human-oriented chaotic bottlenecks:
    
    {stat_block}
    
    Resource Stats (Averages if Multi-run): {stats}
    
    Answer the user's questions strictly using this data. Emphasize how human unpredictable setups and constraints caused these bottlenecks.
    """
    return context

import json
from engine import CorrugatedSimulation

def _run_sim_for_tool(machines_df, jobs_df, routings_df, machine_id=None, new_count=None, new_buffer=None, new_forklifts=None):
    m_df = machines_df.copy()
    forklift_count = new_forklifts if new_forklifts else 2
    
    if machine_id and machine_id in m_df['Machine_ID'].values:
        if new_count is not None:
            m_df.loc[m_df['Machine_ID'] == machine_id, 'Count'] = new_count
        if new_buffer is not None:
            m_df.loc[m_df['Machine_ID'] == machine_id, 'Input_Buffer_Capacity'] = new_buffer
            
    sim = CorrugatedSimulation(m_df, jobs_df, routings_df, forklift_count=forklift_count)
    res = sim.run()
    
    sts = res.get("Machine_Stats", {})
    t_blocked = sum(m.get('blocked_time', 0) for m in sts.values())
    t_starved = sum(m.get('starved_time', 0) for m in sts.values())
    lgs = res.get("Logs", pd.DataFrame())
    t_jams = lgs[lgs["Event"] == "Jam Start"].shape[0] if not lgs.empty and "Event" in lgs.columns else 0
    
    return json.dumps({
        "Hypothetical_Makespan_Minutes": round(res["Total_Time"], 1),
        "Total_Blocked_Time": round(t_blocked, 1),
        "Total_Starved_Time": round(t_starved, 1),
        "Total_Jams": t_jams
    })

tools_schema = [
     {
         "type": "function",
         "function": {
             "name": "run_hypothetical_simulation",
             "description": "Run the Simulation engine under the hood to calculate the ROI of a hypothetical factory modification. ALWAYS execute this tool BEFORE deciding whether a What-If scenario is beneficial! Returns new Makespan, Blocked Time, and Starved Time.",
             "parameters": {
                 "type": "object",
                 "properties": {
                     "machine_id": {
                         "type": "string",
                         "description": "Exact ID of the machine to modify (e.g. 'Corrugator', 'Slotter_Puncher', 'Stitcher', 'Bundling')"
                     },
                     "new_count": {
                         "type": "integer",
                         "description": "New requested quantity of units for this machine stage."
                     },
                     "new_buffer": {
                         "type": "integer",
                         "description": "New physical queue capacity (WIP Buffer limit) right before this machine."
                     },
                     "new_forklifts": {
                         "type": "integer",
                         "description": "Total physical quantity of Forklifts operating globally on the factory floor."
                     }
                 }
             }
         }
     }
]

def get_deepseek_response(prompt, context, machines_df, jobs_df, routings_df):
    try:
        # Robust lookup: secrets.toml, then environment variable
        api_key = None
        if "DEEPSEEK_API_KEY" in st.secrets:
            api_key = st.secrets["DEEPSEEK_API_KEY"]
        elif os.environ.get("DEEPSEEK_API_KEY"):
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            
        if not api_key: 
            return "❌ No API key found. Please ensure 'DEEPSEEK_API_KEY' is set in .streamlit/secrets.toml or as an Environment Variable."
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        sys_msgs = [{"role": "system", "content": context}]
        for m in st.session_state.cc_messages[:-1]: # exclude newest prompt, it's already in history
            if m["role"] not in ["tool", "function"]:
                sys_msgs.append({"role": m["role"], "content": m["content"]})
        if st.session_state.cc_messages[-1]["content"] == prompt:
             pass 
        else:
             sys_msgs.append({"role": "user", "content": prompt})

        res = client.chat.completions.create(
            model="deepseek-chat",
            messages=sys_msgs,
            tools=tools_schema,
            stream=False
        )
        
        msg = res.choices[0].message
        
        tool_args = None
        if getattr(msg, "tool_calls", None):
            t_call = msg.tool_calls[0]
            if t_call.function.name == "run_hypothetical_simulation":
                tool_args = json.loads(t_call.function.arguments)
        elif msg.content and "<｜DSML｜invoke" in msg.content:
            import re
            tool_args = {}
            m1 = re.search(r'<｜DSML｜parameter name="machine_id"[^>]*>(.*?)</｜DSML｜parameter>', msg.content)
            if m1: tool_args["machine_id"] = m1.group(1).strip()
            c1 = re.search(r'<｜DSML｜parameter name="new_count"[^>]*>(.*?)</｜DSML｜parameter>', msg.content)
            if c1: tool_args["new_count"] = int(c1.group(1).strip())
            b1 = re.search(r'<｜DSML｜parameter name="new_buffer"[^>]*>(.*?)</｜DSML｜parameter>', msg.content)
            if b1: tool_args["new_buffer"] = int(b1.group(1).strip())
            f1 = re.search(r'<｜DSML｜parameter name="new_forklifts"[^>]*>(.*?)</｜DSML｜parameter>', msg.content)
            if f1: tool_args["new_forklifts"] = int(f1.group(1).strip())

        if tool_args is not None:
            st.toast("🤖 AI spinning up invisible factory twin...", icon="⚙️")
            sim_res_json = _run_sim_for_tool(machines_df, jobs_df, routings_df, **tool_args)
            
            sys_msgs.append({"role": "assistant", "content": "Running internal physics engine..."})
            sys_msgs.append({
                "role": "user",
                "content": f"The engine completed the What-If simulation with those parameters! Here are the resulting absolute metrics: {sim_res_json}. Please summarize the ROI or outcome compared to the baseline right now."
            })
            
            res2 = client.chat.completions.create(
                model="deepseek-chat",
                messages=sys_msgs,
                stream=False
            )
            return res2.choices[0].message.content
                
        return msg.content
    except Exception as e:
        return f"❌ Error triggering AI: {e}"

def render_ai_assistant(results, machines_df, jobs_df, routings_df):
    import pandas as pd
    
    st.markdown("<div class='sticky-chat'></div>", unsafe_allow_html=True)
    st.subheader("🤖 Factory Analytics AI (Corrugated Trained)")
    
    if "cc_messages" not in st.session_state:
        st.session_state.cc_messages = [{"role": "assistant", "content": "I've analyzed the chaos metrics (Jams & Forklift delays). How can I help you eliminate the human constraints?"}]
        
    chat_container = st.container(height=1000)
    
    with chat_container:
        for msg in st.session_state.cc_messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
    if prompt := st.chat_input("Ask about bottlenecks..."):
        st.session_state.cc_messages.append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"): st.markdown(prompt)
        
        with chat_container:
            with st.spinner("AI is determining logistics constraints..."):
                ctx = get_ai_context(results, machines_df)
                resp = get_deepseek_response(prompt, ctx, machines_df, jobs_df, routings_df)
            
        st.session_state.cc_messages.append({"role": "assistant", "content": resp})
        with chat_container.chat_message("assistant"): st.markdown(resp)
