import streamlit as st

def apply_apex_style():
    st.markdown("""
        <style>
        .stApp { 
            background-color: #000000; 
            color: #ffffff; 
        }
        .stButton>button { 
            background-color: #8B0000; 
            color: white; 
            border: none; 
            font-weight: bold; 
            width: 100%; 
            border-radius: 5px; 
            padding: 10px; 
        }
        .stButton>button:hover { 
            background-color: #FF0033; 
            color: white; 
        }
        h1, h2, h3 {
            font-family: monospace;
        }
        </style>
    """, unsafe_allow_html=True)