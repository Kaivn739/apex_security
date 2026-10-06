import base64
import os
import streamlit as st


def get_base64_of_bin_file(bin_file):
    """گۆڕینی وێنە بۆ کۆدی Base64"""
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


def apply_apex_style():
    """ستایلی تاریکی داشبۆردی سەرەکی (Cyber Command Center)"""
    st.markdown(
        """
    <style>
    /* Force Absolute Dark Theme */
    html, body, [data-testid="stAppViewContainer"], .stApp, section[data-testid="stSidebar"] {
        background-color: #080b11 !important;
        color: #94a3b8 !important;
    }

    /* Hide Streamlit Default Header & Footer */
    header[data-testid="stHeader"], footer {
        visibility: hidden !important;
        height: 0px !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #0d121d !important;
        border-right: 1px solid #1e293b !important;
    }

    div[data-testid="stMetric"] {
        background-color: #0f172a !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def apply_dragon_login_style():
    """ستایلی لۆگین بە شووشەییی تەواو (Glassmorphism) بۆ نیشاندانی دراگۆنەکە"""
    bg_css_url = ""
    if os.path.exists("dragon_bg.jpg"):
        encoded_bg = get_base64_of_bin_file("dragon_bg.jpg")
        bg_css_url = f"data:image/jpg;base64,{encoded_bg}"

    st.markdown(
        f"""
    <style>
    /* 1. وێنەی دراگۆن لە پاشبنەما */
    .stApp {{
        background: url("{bg_css_url}") no-repeat center center fixed !important;
        background-size: cover !important;
    }}
    
    /* 2. کەمکردنەوەی تیرەیی شاشەکە بۆ دەرکەوتنی وێنەی پشتەوە */
    [data-testid="stAppViewContainer"] {{
        background: rgba(0, 0, 0, 0.40) !important;
    }}

    header[data-testid="stHeader"], footer {{
        visibility: hidden !important;
        height: 0px !important;
    }}

    /* 3. کانتێنەری شووشەییی لۆگین (Glassmorphism Container) */
    div[data-testid="stForm"], 
    div[data-testid="stVerticalBlock"] > div:has(div.stTextInput) {{
        background: rgba(15, 23, 42, 0.40) !important;
        backdrop-filter: blur(14px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(14px) saturate(160%) !important;
        border: 1px solid rgba(255, 0, 51, 0.4) !important;
        border-radius: 16px !important;
        padding: 35px 30px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6) !important;
    }}

    /* 4. شووشەییکردنی خانەکانی تێپەڕاندنی دەق */
    input {{
        background-color: rgba(15, 23, 42, 0.50) !important;
        border: 1px solid rgba(255, 0, 51, 0.3) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }}

    /* ستایلی ناونیشانی APEX */
    .apex-title {{
        color: #ff0033 !important;
        font-family: 'Segoe UI', Tahoma, monospace !important;
        font-weight: 800 !important;
        text-align: center !important;
        font-size: 26px !important;
        white-space: nowrap !important;
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )