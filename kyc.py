import streamlit as st
from kyc_engine import process_id_document, generate_formal_agreement, save_kyc_record

def render_kyc():
    st.subheader("🛡 Enterprise KYC & Document Verification")
    st.markdown("---")
    
    with st.form("advanced_kyc_form"):
        st.markdown("### 1. Contact Information / زانیاری پەیوەندی")
        email = st.text_input("Email Address / ئیمەیڵ بۆ تۆمارکردن")
        phone = st.text_input("Phone Number / ژمارەی تەلەفۆن")
        
        st.markdown("### 2. Document Upload / بارکردنی کارتی نیشتمانی")
        st.info("تکایە هەردوو دیوی کارتەکە (پێشەوە و دواوە) بار بکە بۆ خوێندنەوەی خۆکار بە OCR")
        
        front_file = st.file_uploader("Front Side / دیوی پێشەوەی بەڵگەنامە", type=["jpg", "jpeg", "png"])
        back_file = st.file_uploader("Back Side / دیوی دواوەی بەڵگەنامە (ئەگەر هەبێت)", type=["jpg", "jpeg", "png"])
        
        submit_btn = st.form_submit_button("Process Document & Generate Agreement / پرۆسێسکردن و دروستکردنی گرێبەست")

    if submit_btn:
        if not email or not phone or not front_file:
            st.error("❌ تکایە هەموو خانە پێویستەکان پڕبکەرەوە و وێنەی کارتەکە بار بکە!")
        else:
            with st.spinner("⏳ خەریکی خوێندنەوەی بەڵگەنامە و تۆمارکردنی زانیارییەکان لە داتابەیس..."):
                extracted_text = process_id_document(front_file, back_file)
                
                save_result = save_kyc_record(email, phone, extracted_text)
                
                if save_result is True:
                    st.success("✅ زانیارییەکان بە سەرکەوتوویی لە داتابەیس تۆمار کران!")
                    
                    agreement_html = generate_formal_agreement(email, phone, extracted_text)
                    st.markdown(agreement_html, unsafe_allow_html=True)
                else:
                    st.error(f"❌ هەڵە لە پاشەکەوتکردنی داتاکە: {save_result}")