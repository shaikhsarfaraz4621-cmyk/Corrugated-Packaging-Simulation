import pandas as pd
from utils.data_handler import initialize_session_state
import streamlit as st

class DummySession(dict):
    def __getattr__(self, key):
        return self[key]

# Provide dummy streamlit state and invoke handler
st.session_state.clear()
initialize_session_state()

try:
    with pd.ExcelWriter('corrugated_factory_config.xlsx') as writer:
        st.session_state['machines_df'].to_excel(writer, sheet_name='Machines', index=False)
        st.session_state['jobs_df'].to_excel(writer, sheet_name='Jobs', index=False)
        st.session_state['routings_df'].to_excel(writer, sheet_name='Routings', index=False)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
