from __future__ import annotations

import base64
import os
import streamlit as st


def get_base64_of_bin_file(bin_file: str) -> str:
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")


def apply_dragon_login_style() -> None:
    """ستایلی شاشەی چوونەژوورەوە و ئەنیمەیشنی ٣ چرکەیی دراگۆن."""
    bg_css = "radial-gradient(circle at center, #1e0911 0%, #05070d 75%, #020308 100%)"
    if os.path.exists("dragon_bg.jpg"):
        encoded_bg = get_base64_of_bin_file("dragon_bg.jpg")
        bg_css = (
            f'url("data:image/jpg;base64,{encoded_bg}") no-repeat center center fixed'
        )

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {bg_css} !important;
            background-size: cover !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: rgba(3, 6, 14, 0.72) !important;
        }}

        header[data-testid="stHeader"], footer {{
            visibility: hidden !important;
            height: 0px !important;
        }}

        @keyframes dragonReveal {{
            0% {{ opacity: 0; transform: scale(0.92); filter: drop-shadow(0 0 0px #ff0033); }}
            50% {{ opacity: 1; transform: scale(1.02); filter: drop-shadow(0 0 24px rgba(255, 0, 51, 0.85)); }}
            100% {{ opacity: 1; transform: scale(1.0); filter: drop-shadow(0 0 14px rgba(255, 0, 51, 0.6)); }}
        }}

        .dragon-splash-box {{
            background: rgba(10, 15, 28, 0.86);
            backdrop-filter: blur(18px);
            border: 1px solid rgba(255, 0, 51, 0.65);
            border-radius: 20px;
            padding: 42px 28px;
            text-align: center;
            margin-top: 60px;
            animation: dragonReveal 2.6s ease-out forwards;
            box-shadow: 0 0 45px rgba(255, 0, 51, 0.35);
        }}

        .dragon-main-title {{
            color: #ff1e42 !important;
            font-family: 'Segoe UI', Tahoma, monospace !important;
            font-size: 36px !important;
            font-weight: 900 !important;
            letter-spacing: 3px !important;
            margin: 10px 0 6px 0 !important;
        }}

        .dragon-slogan {{
            color: #38bdf8 !important;
            font-family: 'Segoe UI', Tahoma, monospace !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            letter-spacing: 4px !important;
            text-transform: uppercase !important;
        }}

        div[data-testid="stForm"] {{
            background: rgba(12, 18, 34, 0.88) !important;
            backdrop-filter: blur(16px) !important;
            border: 1px solid rgba(255, 0, 51, 0.55) !important;
            border-radius: 16px !important;
            padding: 26px !important;
            box-shadow: 0 10px 35px rgba(0, 0, 0, 0.85) !important;
        }}

        .apex-title {{
            color: #ff1e42 !important;
            font-family: 'Segoe UI', Tahoma, monospace !important;
            font-weight: 800 !important;
            text-align: center !important;
            font-size: 26px !important;
            white-space: nowrap !important;
            margin-bottom: 2px !important;
        }}

        input {{
            background-color: #0b1222 !important;
            border: 1px solid #334155 !important;
            color: #f8fafc !important;
            border-radius: 8px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_apex_style() -> None:
    """ستایلی ڕووکاری Hikvision DVR Command Center (١٠٠٪ تاریک و بێ ئایکۆنی شکاو)."""
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #060a12 !important;
            color: #e2e8f0 !important;
        }

        [data-testid="stSidebar"] {
            background-color: #0b1120 !important;
            border-right: 1px solid #1e293b !important;
        }

        img {
            object-fit: cover !important;
            border-radius: 6px !important;
            background-color: #0b1120 !important;
        }

        img[src=""], img:not([src]) {
            opacity: 0 !important;
        }

        .dvr-topbar {
            background: linear-gradient(90deg, #0f172a 0%, #111827 50%, #1e1b2e 100%);
            border: 1px solid #1e293b;
            border-left: 4px solid #ef4444;
            border-radius: 8px;
            padding: 10px 16px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .dvr-channel-bar {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-left: 3px solid #22c55e;
            padding: 4px 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 4px;
        }

        .stButton > button {
            border-radius: 6px !important;
            font-weight: 700 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# هاوتاکردن لەگەڵ بانگکردنە کۆنەکەی ناو run_app.py
apply_custom_style = apply_apex_style
