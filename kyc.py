import streamlit as st
from kyc_engine import process_id_document, generate_formal_agreement, save_kyc_record
from style import apply_apex_style

def render_kyc():
    apply_apex_style()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #FF0033;'>🛡 APEX ENTERPRISE KYC</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #A0A0A0;'>SECURE IDENTITY VERIFICATION & AGREEMENT</h4><br>", unsafe_allow_html=True)
        
        with st.form("advanced_kyc_form"):
            st.subheader("1. User Information / زانیاری کەسی")
            username = st.text_input("Username / ناوی بەکارهێنەر")
            email = st.text_input("Email Address / ئیمەیڵ")
            phone = st.text_input("Phone Number / ژمارەی تەلەفۆن")
            address = st.text_input("Address / ناونیشان")
            
            st.markdown("---")
            st.subheader("2. Official Document Upload / بارکردنی کارتی نیشتمانی یان پاسپۆرت")
            doc_file = st.file_uploader("Upload ID Card or Passport (Image)", type=["jpg", "jpeg", "png"])
            
            st.markdown("---")
            st.subheader("3. Facial Verification / وێنەی دەموچاو (Selfie)")
            selfie_file = st.camera_input("Take a clear photo of your face")
            
            submit_btn = st.form_submit_button("Process KYC & Generate A4 Agreement / پرۆسێسکردن و دروستکردنی گرێبەست")
            
            if submit_btn:
                if not username or not email or not doc_file:
                    st.warning("⚠️ تکایە هەموو خانە سەرەکییەکان پڕ بکەرەوە و وێنەی بەڵگەنامەکە بار بکە!")
                else:
                    with st.spinner("🔄 ئیشکردن لەسەر خوێندنەوەی بەڵگەنامە (OCR) و دروستکردنی گرێبەست..."):
                        # خوێندنەوەی دەقی بەڵگەنامەکە بە EasyOCR
                        extracted_text = process_id_document(doc_file)
                        
                        # سەیڤکردنی لە داتابەیسدا
                        saved = save_kyc_record(username, email, phone, address, extracted_text)
                        
                        if saved:
                            st.success("✅ پرۆسەی KYC بە سەرکەوتوویی تێپەڕی و داتاکان سەیڤ کران!")
                            
                            # نیشاندانی فۆڕمی فەرمی A4 بۆ بەکارهێنەر
                            st.markdown("### 📄 Official A4 Security & Privacy Agreement")
                            agreement_html = generate_formal_agreement(username, extracted_text)
                            st.markdown(agreement_html, unsafe_allow_html=True)
                            
                            st.info("ℹ️ ئێستا دەتوانیت چاوەڕێی پەسەندکردنی کۆتایی ئەدمین بیت بۆ وەرگرتنی کلیلی چوونەژوورەوە.")
                        else:
                            st.error("❌ هەڵەیەک ڕوودا لە سەیڤکردنی داتاکە.")