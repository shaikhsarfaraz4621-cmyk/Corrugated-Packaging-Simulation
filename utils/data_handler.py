import pandas as pd
import streamlit as st

def initialize_session_state():
    if 'machines_df' not in st.session_state:
        df_m = pd.DataFrame({
            "Machine_ID": ["Corrugator", "Sizer_Cutter", "Laminator", "Slotter_Puncher", "Stitcher", "Bundling"],
            "Count": [1, 1, 1, 2, 2, 1],
            "Input_Buffer_Capacity": [10, 5, 5, 3, 2, 1], # Strict limits causing downstream blocking
            "Jam_Weibull_Alpha": [1.5, 0, 0, 1.2, 0, 0], # Jams primarily on Corrugator and Slotter
            "Jam_Weibull_Beta": [180.0, 0.0, 0.0, 120.0, 0.0, 0.0], # MTBF ~ 2 to 3 hours
            "Repair_Lognormal_Mu": [15.0, 0, 0, 10.0, 0, 0], # 10 to 15 mins to clear jam
            "Repair_Lognormal_Sigma": [5.0, 0, 0, 3.0, 0, 0]
        })
        st.session_state['machines_df'] = df_m

    if 'jobs_df' not in st.session_state:
        df_j = pd.DataFrame({
            "Job_Type": ["Standard_Box", "Custom_Punch_Box", "Printed_Display_Box"],
            "Target_Demand": [50000, 15000, 25000],
            "Batch_Size": [5000, 1000, 2500],
            "Interarrival_Min": [2.0, 1.0, 3.0],
            "Interarrival_Max": [5.0, 3.0, 6.0]
        })
        st.session_state['jobs_df'] = df_j

    if 'routings_df' not in st.session_state:
        routings = [
            {"Job_Type": "Standard_Box", "Sequence_Order": 1, "Machine_ID": "Corrugator", "Process_Time_Per_Unit": 0.015, "Setup_Time_Base": 25.0, "Setup_Time_Std": 10.0, "Requires_Forklift": True},
            {"Job_Type": "Standard_Box", "Sequence_Order": 2, "Machine_ID": "Sizer_Cutter", "Process_Time_Per_Unit": 0.005, "Setup_Time_Base": 5.0, "Setup_Time_Std": 2.0, "Requires_Forklift": False},
            {"Job_Type": "Standard_Box", "Sequence_Order": 3, "Machine_ID": "Slotter_Puncher", "Process_Time_Per_Unit": 0.008, "Setup_Time_Base": 15.0, "Setup_Time_Std": 8.0, "Requires_Forklift": False},
            {"Job_Type": "Standard_Box", "Sequence_Order": 4, "Machine_ID": "Stitcher", "Process_Time_Per_Unit": 0.03, "Setup_Time_Base": 10.0, "Setup_Time_Std": 3.0, "Requires_Forklift": False},
            {"Job_Type": "Standard_Box", "Sequence_Order": 5, "Machine_ID": "Bundling", "Process_Time_Per_Unit": 0.05, "Setup_Time_Base": 2.0, "Setup_Time_Std": 0.5, "Requires_Forklift": False},
            
            {"Job_Type": "Printed_Display_Box", "Sequence_Order": 1, "Machine_ID": "Corrugator", "Process_Time_Per_Unit": 0.015, "Setup_Time_Base": 25.0, "Setup_Time_Std": 10.0, "Requires_Forklift": True},
            {"Job_Type": "Printed_Display_Box", "Sequence_Order": 2, "Machine_ID": "Sizer_Cutter", "Process_Time_Per_Unit": 0.005, "Setup_Time_Base": 5.0, "Setup_Time_Std": 2.0, "Requires_Forklift": False},
            {"Job_Type": "Printed_Display_Box", "Sequence_Order": 3, "Machine_ID": "Laminator", "Process_Time_Per_Unit": 0.015, "Setup_Time_Base": 15.0, "Setup_Time_Std": 5.0, "Requires_Forklift": True},
            {"Job_Type": "Printed_Display_Box", "Sequence_Order": 4, "Machine_ID": "Slotter_Puncher", "Process_Time_Per_Unit": 0.01, "Setup_Time_Base": 20.0, "Setup_Time_Std": 10.0, "Requires_Forklift": False},
            {"Job_Type": "Printed_Display_Box", "Sequence_Order": 5, "Machine_ID": "Stitcher", "Process_Time_Per_Unit": 0.03, "Setup_Time_Base": 10.0, "Setup_Time_Std": 3.0, "Requires_Forklift": False},
            {"Job_Type": "Printed_Display_Box", "Sequence_Order": 6, "Machine_ID": "Bundling", "Process_Time_Per_Unit": 0.05, "Setup_Time_Base": 2.0, "Setup_Time_Std": 0.5, "Requires_Forklift": False},
            
            {"Job_Type": "Custom_Punch_Box", "Sequence_Order": 1, "Machine_ID": "Corrugator", "Process_Time_Per_Unit": 0.015, "Setup_Time_Base": 25.0, "Setup_Time_Std": 10.0, "Requires_Forklift": True},
            {"Job_Type": "Custom_Punch_Box", "Sequence_Order": 2, "Machine_ID": "Sizer_Cutter", "Process_Time_Per_Unit": 0.005, "Setup_Time_Base": 5.0, "Setup_Time_Std": 2.0, "Requires_Forklift": False},
            {"Job_Type": "Custom_Punch_Box", "Sequence_Order": 3, "Machine_ID": "Slotter_Puncher", "Process_Time_Per_Unit": 0.015, "Setup_Time_Base": 25.0, "Setup_Time_Std": 12.0, "Requires_Forklift": False},
            {"Job_Type": "Custom_Punch_Box", "Sequence_Order": 4, "Machine_ID": "Stitcher", "Process_Time_Per_Unit": 0.03, "Setup_Time_Base": 10.0, "Setup_Time_Std": 3.0, "Requires_Forklift": False},
            {"Job_Type": "Custom_Punch_Box", "Sequence_Order": 5, "Machine_ID": "Bundling", "Process_Time_Per_Unit": 0.05, "Setup_Time_Base": 2.0, "Setup_Time_Std": 0.5, "Requires_Forklift": False},
        ]
        st.session_state['routings_df'] = pd.DataFrame(routings)

def handle_file_upload(uploaded_file):
    try:
        xl = pd.ExcelFile(uploaded_file)
        if 'Machines' in xl.sheet_names:
            st.session_state['machines_df'] = xl.parse('Machines')
        if 'Jobs' in xl.sheet_names:
            st.session_state['jobs_df'] = xl.parse('Jobs')
        if 'Routings' in xl.sheet_names:
            st.session_state['routings_df'] = xl.parse('Routings')
        st.success("✅ Configuration Loaded!")
    except Exception as e:
        st.error(f"Error reading file: {e}")

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
