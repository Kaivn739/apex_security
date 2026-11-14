import streamlit as st


def render_emergency_alerts_module():
    st.markdown("## 🚨 THREAT & EMERGENCY MODULES")
    st.caption("بەڕێوەبردنی سیستمەکانی ئاگادارکردنەوەی بەپەلە و تەلەگرام")

    with st.container(border=True):
        st.markdown("##### 📲 ڕێکخستنی کەناڵی ئاگادارکردنەوەی تەلەگرام")
        st.text_input("Telegram Bot Token:", value="683920194:AAFx...", type="password")
        st.text_input("Telegram Chat ID:", value="-10019384920")

        st.toggle("🔔 ناردنی ئاگاداری بێدەنگ (Silent Alert)", value=False)
        st.toggle("🚨 ڕەوانەکردنی وێنەی فریم بۆ کەناڵ", value=True)

        if st.button(
            "🧪 تاقیکردنەوەی ئاگاداری تەلەگرام (Test Alert)", use_container_width=True
        ):
            st.toast("🚀 پەیامی تاقیکردنەوە رەوانەی تەلەگرام کرا!", icon="🚨")