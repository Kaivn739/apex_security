import streamlit as st

def render_alerts_panel():
    """
    ئەم فەنکشنە بەرپرسە لە نیشاندانی ئاگادارییە خێراکان لە لای ڕاستی شاشەکە
    """
    st.markdown("### 🚨 ACTIVE ALERTS")
    
    # کارتەکانی ئاگاداری (Alert Cards)
    st.error("🚨 CRITICAL: Intrusion Detected (CAM-04 Restricted Zone)")
    st.error("🔥 CRITICAL: Fire Detection Alert (CAM-03 Reception)")
    st.warning("⚠️ WARNING: High Occupancy Rate (CAM-02 Parking)")
    st.info("ℹ️ INFO: Camera Restored Connection (CAM-01 Warehouse)")

    st.markdown("---")
    
    st.markdown("### ⚙️ AI ENGINE STATUS")
    col1, col2 = st.columns(2)
    with col1:
        st.write("• Object Detection")
        st.write("• Object Tracking")
        st.write("• Zone Analytics")
    with col2:
        st.success("ONLINE")
        st.success("ONLINE")
        st.success("ONLINE")