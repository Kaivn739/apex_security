import streamlit as st


def apply_custom_style():
    """ڕێکخستنی بنەڕەتی لاپەڕە بە سادەیی"""
    pass


# --- 📍 ناوە کۆنەکان تا فایلی تر تووشی هەڵەی AttributeError نەبن ---


def apply_apex_style():
    apply_custom_style()


def apply_dragon_login_style():
    apply_custom_style()


def render_stat_box(title, value, subtext="", sub_color=""):
    """نیشاندانی ئامار بە شێوازی سادەی Streamlit"""
    st.metric(label=title, value=value, delta=subtext if subtext else None)


def render_stat_card(title, value, subtext="", sub_color=""):
    render_stat_box(title, value, subtext, sub_color)


def render_interactive_lottie_card():
    """جێگرەوەی سادە بۆ ئانیمەیشنەکە"""
    st.info("🤖 AI Engine Status: Active")
