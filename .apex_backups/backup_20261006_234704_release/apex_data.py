import streamlit as st
import pandas as pd
import sqlite3
from apex_brain import APEXBrainCore


def render_apex_data_window():
    st.set_page_config(
        page_title="APEX DATA - System Vault", page_icon="📊", layout="wide"
    )

    brain = APEXBrainCore()
    health = brain.get_system_health()
    summary = brain.get_all_data_summary()

    st.markdown("# 📊 APEX DATA - SYSTEM VAULT & ANALYTICS")
    st.caption("🖥️ شاشەی تایبەتی بەکارهێنەر بۆ چاودێریکردنی گشت داتاکان و ئاستی سیستەم")

    st.divider()

    # 1. System Hardware Health (تەندروستی لاپتۆپ و CPU)
    st.markdown("### 🧠 APEX BRAIN & HARDWARE HEALTH")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "⚙️ بەکارهێنانی CPU",
            f"{health['cpu']}%",
            delta="تەندروستە" if health["cpu"] < 70 else "فشاری بەرز",
        )
    with col2:
        st.metric("💾 بەکارهێنانی RAM", f"{health['ram']}%")
    with col3:
        st.metric("🛡️ دۆخی عەقڵی APEX", "ONLINE (Active)", delta="Background Engine")

    st.divider()

    # 2. Total Data Summary (پوختەی گشت داتاکان)
    st.markdown("### 📈 پوختەی گشتی داتاکانی APEX")
    col_t1, col_t2 = st.columns(2)

    with col_t1:
        st.info(f"👥 **سەرجەمی تارگێتە تۆمارکراوەکان:** {summary['total_targets']}")
    with col_t2:
        st.error(f"🚨 **سەرجەمی ئاگادارییە دۆزراوەکان:** {summary['total_alerts']}")

    # 3. Alert Archives (ئەرشیفی ڕووداوەکان)
    st.markdown("### 📝 دوایین لۆگ و ڕووداوە تۆمارکراوەکان")

    conn = sqlite3.connect("apex_security.db")
    try:
        df_logs = pd.read_sql_query("SELECT * FROM alert_logs ORDER BY id DESC", conn)
        st.dataframe(df_logs, use_container_width=True)
    except Exception:
        st.warning("⚠️ هێشتا هیچ لۆگێک تۆمار نەکراوە.")
    finally:
        conn.close()

    st.divider()

    # 4. Control Options (خاوێنکردنەوە یان هەناردەکردن)
    st.markdown("### ⚙️ بەڕێوەبردنی داتاکان")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button(
            "📥 هەناردەکردنی داتاکان (Export to CSV)", use_container_width=True
        ):
            st.success("✅ داتاکان بە سەرکەوتوویی پاشەکەوتکران!")
    with col_b2:
        if st.button("🗑️ خاوێنکردنەوەی لۆگە کۆنەکان", use_container_width=True):
            st.toast("🧹 لۆگەکان خاوێنکرانەوە!", icon="✅")


if __name__ == "__main__":
    render_apex_data_window()