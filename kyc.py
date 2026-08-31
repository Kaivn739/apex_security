import streamlit as st
from kyc_engine import process_id_document, generate_formal_agreement, save_kyc_record

def render_kyc():
    st.subheader("🛡 Enterprise KYC & Document Verification")
    st.markdown("---")
    
    # فۆرمی سەرەکی بە بێ تێکەڵکردنی ماردکۆنی هەڵە لە ناوەوەی فۆرمەکە
    with st.form("advanced_kyc_form"):
        st.markdown("### 1. Contact Information / زانیاری پەیوەندی")
        email = st.text_input("Email Address / ئیمەیڵ بۆ تۆمارکردن")
        phone = st.text_input("Phone Number / ژمارەی تەلەفۆن")
        
        st.markdown("### 2. Document Upload / بارکردنی کارتی نیشتمانی")
        st.info("تکایە هەردوو دیوی کارتەکە (پێشەوە و دواوە) بار بکە بۆ خوێندنەوەی خۆکار بە OCR")
        
        front_file = st.file_uploader("Front Side / دیوی پێشەوەی بەڵگەنامە", type=["jpg", "jpeg", "png"])
        back_file = st.file_uploader("Back Side / دیوی دواوەی بەڵگەنامە (ئەگەر هەبێت)", type=["jpg", "jpeg", "png"])
        
        st.markdown("### 3. Digital Signature / واژۆی ئەلکترۆنی")
        signature = st.text_input("Type your full name as Digital Signature / ناوی تەواوت بنووسە وەک واژۆ")
        
        submit_btn = st.form_submit_button("Process Document & Generate Agreement / پرۆسێسکردن و دروستکردنی گرێبەست")

    # جێبەجێکردن دوای کلیککردن لەسەر دوگمەی فۆرمەکە (لە دەرەوەی st.form)
    if submit_btn:
        if not email or not phone or not front_file or not signature:
            st.error("❌ تکایە هەموو خانە پێویستەکان پڕبکەرەوە و وێنەی کارتەکە بار بکە!")
        else:
            with st.spinner("⏳ خەریکی خوێندنەوەی بەڵگەنامە و تۆمارکردنی زانیارییەکان لە داتابەیس..."):
                # خوێندنەوەی دەق لە وێنەکان
                extracted_text = process_id_document(front_file, back_file)
                
                # پاشەکەوتکردن لە داتابەیس
                save_result = save_kyc_record(email, phone, extracted_text, signature)
                
                if save_result is True:
                    st.success("✅ زانیارییەکان بە سەرکەوتوویی لە داتابەیس تۆمار کران!")
                    
                    # نیشاندانی گرێبەستی فەرمی A4 بە دیزاینە پاکەکەی ناوچەی چوارچێوە
                    agreement_html = generate_formal_agreement(email, phone, extracted_text, signature)
                    st.markdown(agreement_html, unsafe_allow_html=True)
                else:
                    st.error(f"❌ هەڵە لە پاشەکەوتکردنی داتاکە: {save_result}")