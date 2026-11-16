import streamlit as st

try:
    import psutil
except ImportError:
    psutil = None

from apex_developer import (
    get_step10_bridge_status,
    start_apex_developer_background,
)


@st.cache_resource
def init_background_developer_ai() -> bool:
    """کارپێکردنی APEX AI Developer لە باکگراوندی APEX Security بەبێ لاگ"""
    return start_apex_developer_background(interval_seconds=60)


def render_compact_developer_widget() -> None:
    """
    ڕووکارێکی بچووک لە سەرەوەی داشبۆردی سەرەکی:
    تەنها CPU و دۆخی کێشەکان پیشان دەدات لە کاتێکدا Developer AI لە باکگراوند کار دەکات
    """
    init_background_developer_ai()

    cpu_pct = round(float(psutil.cpu_percent(interval=None)), 1) if psutil else 0.0
    ram_pct = round(float(psutil.virtual_memory().percent), 1) if psutil else 0.0

    bridge = get_step10_bridge_status()
    telemetry = bridge.get("hardware_telemetry", {})
    if cpu_pct == 0.0 and isinstance(telemetry, dict):
        cpu_pct = float(telemetry.get("cpu_percent", 0.0))

    issues_count = int(bridge.get("alerts_indexed_this_run", 0))
    learned_count = int(bridge.get("total_learned_patterns", 0))

    is_healthy = cpu_pct < 80.0 and ram_pct < 90.0 and issues_count == 0
    border_color = "#16a34a" if is_healthy else "#d97706"
    status_label = "چالاک (باکگراوند)" if is_healthy else "چاودێریی چڕ (باکگراوند)"

    st.markdown(
        f"""
        <div style="
            display:flex; justify-content:space-between; align-items:center;
            background:#0f172a; color:#f8fafc; padding:7px 14px;
            border-radius:8px; border-left:4px solid {border_color};
            font-size:13px; margin-bottom:10px;
        ">
            <div>🛡️ <b>APEX Dev AI:</b> <span style="color:#38bdf8;">{status_label}</span></div>
            <div>⚡ <b>CPU:</b> {cpu_pct}% &nbsp;|&nbsp; 🧠 <b>RAM:</b> {ram_pct}%</div>
            <div>🚨 <b>کێشەکان:</b> {issues_count} &nbsp;|&nbsp; 📚 <b>فێربوون:</b> {learned_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
