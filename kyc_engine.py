import streamlit as st
import cv2
import numpy as np
import easyocr
import sqlite3
from datetime import datetime

# کردنەوەی ڕیدەری EasyOCR (بۆ خوێندنەوەی کوردی/عەرەبی یان ئینگلیزی لەسەر پاسپۆرت و کارت)
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en', 'ar'])

def process_id_document(image_file):
    """خوێندنەوەی دەق لە وێنەی کارتی نیشتمانی یان پاسپۆرت"""
    try:
        bytes_data = image_file.read()
        np_array = np.frombuffer(bytes_data, np.uint8)
        img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        
        reader = load_ocr_reader()
        results = reader.readtext(img)
        
        extracted_text = " ".join([res[1] for res in results])
        return extracted_text
    except Exception as e:
        return f"OCR Error: {e}"

def generate_formal_agreement(email, phone, username, document_info, signature):
    """دروستکردنی دەقی گرێبەستی فەرمی A4 لەگەڵ مەرجەکانی Privacy Security"""
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    agreement_html = f"""
    <div style="background-color: #ffffff; color: #000000; padding: 30px; border-radius: 5px; border: 2px solid #FF0033; font-family: Arial, sans-serif;">
        <h2 style="text-align: center; color: #FF0033;">🛡 APEX SECURITY SOLUTIONS</h2>
        <h4 style="text-align: center; color: #555555;">OFFICIAL ENTERPRISE KYC & PRIVACY AGREEMENT</h4>
        <hr style="border: 1px solid #FF0033;">
        <p><b>Date & Time:</b> {current_date}</p>
        <p><b>Registered Operator / User:</b> {username}</p>
        <p><b>Email:</b> {email}</p>
        <p><b>Phone:</b> {phone}</p>
        
        <h3 style="color: #333333;">1. Privacy & Security Policy</h3>
        <p>By signing this agreement, the user acknowledges and agrees that all surveillance data, facial recognition logs, and system interactions within the APEX platform are strictly monitored, encrypted, and protected under enterprise-grade security regulations.</p>
        
        <h3 style="color: #333333;">2. Document Verification Data</h3>
        <p style="background-color: #f9f9f9; padding: 10px; border: 1px solid #ccc; font-family: monospace;">{document_info}</p>
        
        <h3 style="color: #333333;">3. Terms and Conditions</h3>
        <p>The user agrees not to misuse access credentials, network video streams (LAN/HDMI), or secure agency nodes. Any unauthorized access will result in immediate termination of the account and legal actions.</p>
        
        <br><br>
        <div style="display: flex; justify-content: space-between;">
            <div>
                <p><b>APEX Security Authority</b></p>
                <p style="color: green;">[Digitally Verified & Locked]</p>
            </div>
            <div style="text-align: right;">
                <p><b>User Digital Signature:</b></p>
                <p style="font-family: cursive; color: blue;">{signature}</p>
            </div>
        </div>
    </div>
    """
    return agreement_html

def save_kyc_record(email, phone, doc_data, signature):
    """سەیڤکردنی سەرجەم زانیارییەکان لە داتابەیسدا"""
    try:
        conn = sqlite3.connect('apex_security.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                phone TEXT,
                doc_data TEXT,
                signature TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        
        cursor.execute(
            "INSERT INTO users (email, phone, doc_data, signature, status) VALUES (?, ?, ?, ?, ?)",
            (email, phone, doc_data, signature, "Pending")
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database error details: {e}")
        return False