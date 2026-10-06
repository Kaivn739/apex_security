import streamlit as st


def apply_apex_style():
    st.markdown(
        """
        <style>
        /* ستایلی یەکگرتووی هەموو دوگمەکان (دەستەچەپ و ناوەڕاست) - هاوشێوەی Auto-Fit Grid */
        div.stButton > button, 
        section[data-testid="stSidebar"] div.stButton > button {
            width: auto !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 6px 16px !important;
            border-radius: 6px !important;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
            color: #38bdf8 !important;
            border: 1px solid #0284c7 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.4) !important;
            transition: all 0.25s ease-in-out !important;
            margin: 3px 0px !important;
        }
        
        div.stButton > button:hover,
        section[data-testid="stSidebar"] div.stButton > button:hover {
            background: #0284c7 !important;
            color: #ffffff !important;
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.6) !important;
            border-color: #38bdf8 !important;
            transform: translateY(-1px);
        }

        /* ستایلی نیشانەی جۆری کامێراکان (Badges) */
        .cam-badge {
            background: #0284c7;
            color: #ffffff;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            margin-right: 6px;
            display: inline-block;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
# ئەمە لە کۆتایی فایلی style.py زیاد بکە تا کێشەی auth.py نەمێنێت:
def apply_dragon_login_style():
    apply_apex_style()