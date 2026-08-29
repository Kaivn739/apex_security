import streamlit as st
import camera
camera.render_camera_module()
def show_dashboard():
    st.title("🛡️ APEX Security Dashboard")
    st.write("سیستەمی چاودێری و حوکمڕانی")
    
    st.subheader("هەڵبژاردنی کامێرا")
    
    # دوو دوگمەی جیابۆوە بۆ دەستپێکردن
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Start Wansview Camera", key="btn_wansview"):
            st.session_state.active_camera = "wansview"
            st.rerun()
            
    with col2:
        if st.button("Start Laptop Camera", key="btn_laptop"):
            st.session_state.active_camera = "laptop"
            st.rerun()

    # پشکنین بۆ ئەوەی بزانین کام کامێرا هەڵبژێردراوە
    if 'active_camera' in st.session_state:
        if st.session_state.active_camera == "wansview":
            if st.button("← گەڕانەوە بۆ داشبۆرد", key="back_from_wansview"):
                del st.session_state.active_camera
                st.rerun()
            camera.show_wansview()
            
        elif st.session_state.active_camera == "laptop":
            if st.button("← گەڕانەوە بۆ داشبۆرد", key="back_from_laptop"):
                del st.session_state.active_camera
                st.rerun()
            camera.show_laptop()