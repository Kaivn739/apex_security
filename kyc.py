import streamlit as st
from kyc_engine import process_id_document, generate_formal_agreement, save_kyc_record
from style import apply_apex_style

def render_kyc():
    apply_apex_style()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #FF0033;'>🛡 APEX ENTERPRISE KYC</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #A0A0A0;'>AUTOMATED ID SCANNING & A4 AGREEMENT</h4><br>", unsafe_allow_html=True)
        
        with st.form("advanced_kyc_form"):
            st.subheader("1. Contact Information / زانیاری پەیوەندی")
            email = st.text_input("Email Address / ئیمەیڵ بۆ ناردنی کۆد")
            phone = st.text_input("Phone Number / ژمارەی تەلەفۆن")
            
            st.markdown(agreement_html, unsafe_allow_html=True)
            st.subheader("2. Document Upload / بارکردنی کارتی نیشتمانی یان پاسپۆرت")
            st.info("تکایە هەردوو دیوی کارتەکە (پێشەوە و دواوە) بار بکە بۆ خوێندنەوەی خۆکار.")
            
            front_file = st.file_uploader("Front Side / دیوی پێشەوەی بەڵگەنامە", type=["jpg", "jpeg", "png"])
            back_file = st.file_uploader("Back Side / دیوی دواوەی بەڵگەنامە (ئەگەر هەبوو)", type=["jpg", "jpeg", "png"])
            
            st.markdown(agreement_html, unsafe_allow_html=True)
            st.subheader("3. Digital Signature / واژۆی ئەلیکترۆنی")
            signature = st.text_input("Type your full name as Digital Signature / ناوی تەواوت بنووسە وەکو واژۆ")
            
            submit_btn = st.form_submit_button("Process Document & Generate A4 Agreement / خوێندنەوە و دروستکردنی گرێبەست")
            
            if submit_btn:
                if not email or not phone or not front_file or not signature:
                    st.warning("⚠️ تکایە ئیمەیڵ، ژمارەی تەلەفۆن، دیوی پێشەوەی بەڵگەنامە و واژۆ پڕ بکەرەوە!")
                else:
                    with st.spinner("🔄 خەریکی خوێندنەوەی وێنەکانە (OCR) و دروستکردنی گرێبەستی A4..."):
                        # خوێندنەوەی دەقی هەردوو دیوی بەڵگەنامەکە
                        extracted_text = process_id_document(front_file)
                        if back_file:
                            extracted_text += " " + process_id_document(back_file)
                        
                        # سەیڤکردن لە داتابەیسدا (بە ناردنی ئیمەیڵ و تەلەفۆن)
                        saved = save_kyc_record(email, phone, extracted_text, signature)
                        
                        if saved:
                            st.success("✅ زانیارییەکان خوێنرانەوە و گرێبەستی فەرمی A4 سەرکەوتووانە دروست کرا!")
                            
                            # نیشاندانی گرێبەستی فەرمی A4
                            st.markdown("### 📄 Official A4 Security & Privacy Agreement")
                            agreement_html = generate_formal_agreement(email, phone, extracted_text, signature)
                            st.markdown(agreement_html, unsafe_allow_html=True)
                            
                            st.info("ℹ️ داواکارییەکەت بۆ ئەدمین نێردرا. پاش پەسەندکردن، کۆدی چوونەژوورەوەت بە ئیمەیڵ بۆ دێت.")
                        else:
                            st.error("❌ هەڵەیەک ڕوودا لە پاشەکەوتکردنی داتاکە.")