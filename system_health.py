import streamlit as st
import psutil

def render_system_health():
    """
    نیشاندانی دۆخی بەکارهێنانی سەرچاوەکانی لاپتۆپ/سێرڤەر لە خوارەوەی شاشەکە
    """
    st.markdown("### 🖥️ SYSTEM HEALTH & INFORMATION")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # بەکارهێنانی CPU و RAMی ڕاستەقینەی ئامێرەکە
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    
    with col1:
        st.caption("CPU Usage")
        st.progress(cpu_usage / 100)
        st.write(f"{cpu_usage}%")
        
    with col2:
        st.caption("RAM Usage")
        st.progress(ram_usage / 100)
        st.write(f"{ram_usage}%")
        
    with col3:
        st.caption("Disk Storage")
        st.progress(disk_usage / 100)
        st.write(f"{disk_usage}%")
        
    with col4:
        st.caption("System Status")
        st.success("Stable (100 FPS)")
        st.write("Platform: APEX v2.0")