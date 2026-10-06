import streamlit as st
import sqlite3
import pandas as pd


def render_historical_analytics_module():
    st.markdown("## 🔍 HISTORICAL ARCHIVE & LOGS")
    st.caption("گەڕان و تەماشاکردنی گشت ئەرشیفە کۆنەکانی عەقڵی APEX")

    conn = sqlite3.connect("apex_security.db")
    try:
        df_targets = pd.read_sql_query("SELECT * FROM targets ORDER BY id DESC", conn)
        df_alerts = pd.read_sql_query("SELECT * FROM alert_logs ORDER BY id DESC", conn)

        tab_a1, tab_a2 = st.tabs(["📋 ئەرشیفی تارگێتەکان", "🚨 ئەرشیفی ئاگادارییەکان"])
        with tab_a1:
            st.dataframe(df_targets, use_container_width=True)
        with tab_a2:
            st.dataframe(df_alerts, use_container_width=True)
    except Exception:
        st.info("⚠️ هێشتا داتای ئەرشیفکراو لە داتابەیستدا بەردەست نییە.")
    finally:
        conn.close()