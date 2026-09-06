import streamlit as st
import pandas as pd
import numpy as np

def render_analytics():
    """
    نیشاندانی هێڵکاری و ئامارەکانی چوونەژوورەوە و دەرچوون
    """
    st.markdown("### 📊 DETECTION & TREND ANALYTICS")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.caption("📈 Entry / Exit Trend (Today)")
        
        # دروستکردنی داتای ئاماری تاقیکاری بۆ هێڵکاری
        chart_data = pd.DataFrame(
            np.random.randint(10, 50, size=(12, 2)),
            columns=['Entries', 'Exits']
        )
        st.line_chart(chart_data)
        
    with col2:
        st.caption("📋 Detection Summary")
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric("People Detected", "1,182", "+14%")
            st.metric("Bags / Items", "32", "+2")
        with m_col2:
            st.metric("Vehicles", "248", "+8%")
            st.metric("Other Objects", "20", "0%")