import streamlit as st
import cv2
import numpy as np
import easyocr
import sqlite3
from datetime import datetime

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en', 'ar'])

def process_id_document(front_file, back_file=None):
    """خوێندنەوەی دەق لە هەردوو دیوی کارتی نیشتمانی یان پاسپۆرت"""
    try:
        reader = load_ocr_reader()
        extracted_texts = []
        
        if front_file:
            bytes_data = front_file.read()
            np_array = np.frombuffer(bytes_data, np.uint8)
            img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
            if img is not None:
                results = reader.readtext(img)
                front_text = " ".join([res[1] for res in results])
                extracted_texts.append(f"--- Front Side ---\n{front_text}")
            
        if back_file:
            bytes_data_b = back_file.read()
            np_array_b = np.frombuffer(bytes_data_b, np.uint8)
            img_b = cv2.imdecode(np_array_b, cv2.IMREAD_COLOR)
            if img_b is not None:
                results_b = reader.readtext(img_b)
                back_text = " ".join([res[1] for res in results_b])
                extracted_texts.append(f"--- Back Side ---\n{back_text}")
            
        return "\n".join(extracted_texts) if extracted_texts else "No text found"
    except Exception as e:
        return f"OCR Error: {str(e)}"

def generate_formal_agreement(email, phone, document_info, signature):
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    agreement_html = f"""
    <div style="background-color: #ffffff; color: #000000; padding: 30px; border-radius: 5px; border: 2px solid #FF0033; font-family: Arial, sans-serif;">
        <h2 style="text-align: center; color: #FF0033;">🛡 APEX SECURITY SOLUTIONS</h2>
        <h4 style="text-align: center; color: #555555;">OFFICIAL ENTERPRISE KYC & PRIVACY AGREEMENT</h4>
        <hr style="border: 1px solid #FF0033;">
        <p><b>Date & Time:</b> {current_date}</p>
        <p><b>Client Email:</b> {email} | <b>Phone:</b> {phone}</p>
        <h3 style="color: #333333;">1. Extracted Document Information (OCR)</h3>
        <p style="background-color: #f9f9f9; padding: 10px; border: 1px solid #ccc; font-family: monospace; white-space: pre-wrap;">{document_info}</p>
        <br>
        <div style="display: flex; justify-content: space-between;">
            <div><p><b>APEX Security Authority</b></p><p style="color: green;">[Verified]</p></div>
            <div style="text-align: right;"><p><b>Digital Signature:</b></p><p style="font-family: cursive; color: blue; font-size: 18px;">{signature}</p></div>
        </div>
    </div>
    """
    return agreement_html

def save_kyc_record(email, phone, doc_text, signature):
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
            (email, phone, doc_text, signature, "Pending")
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return str(e)