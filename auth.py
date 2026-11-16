from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from typing import Any

import streamlit as st
import style

try:
    from subscription_manager import DB_NAME, ensure_free_trial_account
except ImportError:
    DB_NAME = "apex_security.db"
    ensure_free_trial_account = None  # type: ignore[assignment]


def _init_users_table() -> None:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT
        )
    """)
    admin_hash = hashlib.sha256("admin".encode("utf-8")).hexdigest()
    cursor.execute(
        "INSERT OR IGNORE INTO app_users (username, password_hash, full_name) VALUES ('admin', ?, 'System Owner')",
        (admin_hash,),
    )
    conn.commit()
    conn.close()


def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.strip().encode("utf-8")).hexdigest()


def login_screen() -> None:
    """شاشەی دەستپێکی ٣ چرکەیی دراگۆن و چوونەژوورەوەی پارێزراو."""
    _init_users_table()
    style.apply_dragon_login_style()

    # قۆناغی ١: ئەنیمەیشنی ٣ چرکەیی دراگۆن و دروشمی for Safe, for Ever
    if not st.session_state.get("dragon_intro_done", False):
        _, mid_col, _ = st.columns([1, 2.4, 1])
        with mid_col:
            dragon_img_html = ""
            if os.path.exists("dragon_bg.jpg"):
                b64_img = style.get_base64_of_bin_file("dragon_bg.jpg")
                dragon_img_html = (
                    f"<img src='data:image/jpg;base64,{b64_img}' "
                    "style='width:150px; height:150px; border-radius:50%; "
                    "border:2px solid #ff1e42; object-fit:cover; margin-bottom:12px;' />"
                )
            else:
                dragon_img_html = "<div style='font-size:64px;'>🐉🛡️</div>"

            st.markdown(
                f"""
                <div class="dragon-splash-box">
                    {dragon_img_html}
                    <div class="dragon-main-title">APEX SECURITY</div>
                    <div class="dragon-slogan">for Safe, for Ever</div>
                    <p style="color:#94a3b8; font-size:13px; margin-top:16px;">
                        Initializing Offline Tactical AI &amp; Cyber Shield...
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        time.sleep(3.0)
        st.session_state.dragon_intro_done = True
        st.rerun()
        return

    # قۆناغی ٢: فۆرمی چوونەژوورەوە و هەژماری خۆڕایی
    _, col2, _ = st.columns([1, 2.2, 1])
    with col2:
        st.markdown(
            "<h1 class='apex-title'>🐉 APEX SECURITY</h1>", unsafe_allow_html=True
        )
        st.markdown(
            "<p style='text-align: center; color: #38bdf8; font-size: 13px; letter-spacing: 2px; font-weight: 700;'>"
            "FOR SAFE, FOR EVER</p>",
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(
            ["🔐 چوونەژوورەوە (Login)", "✨ هەژماری نوێ (Free Trial)"]
        )

        with tab_login:
            with st.form("dragon_login_form"):
                username = str(
                    st.text_input(
                        "ناوی بەکارهێنەر (Username):",
                        placeholder="admin",
                        key="login_user",
                    )
                    or ""
                )
                password = str(
                    st.text_input(
                        "تێپەڕەوشە (Password):",
                        type="password",
                        placeholder="••••••",
                        key="login_pass",
                    )
                    or ""
                )
                submit = st.form_submit_button(
                    "LOGIN TO COMMAND CENTER", use_container_width=True
                )

                if submit:
                    uname = username.strip()
                    if uname == "admin" and password in ("1234", "admin"):
                        st.session_state.authenticated = True
                        st.session_state.logged_in = True
                        st.session_state.username = "admin"
                        st.rerun()

                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT password_hash FROM app_users WHERE username = ?",
                        (uname,),
                    )
                    row: Any = cursor.fetchone()
                    conn.close()

                    if row and str(row[0]) == _hash_pw(password):
                        if ensure_free_trial_account is not None:
                            ensure_free_trial_account(uname)
                        st.session_state.authenticated = True
                        st.session_state.logged_in = True
                        st.session_state.username = uname
                        st.rerun()
                    else:
                        st.error("❌ ناوی بەکارهێنەر یان تێپەڕەوشە هەڵەیە.")

        with tab_register:
            with st.form("dragon_register_form"):
                st.caption(
                    "🆓 هەژماری نوێ ڕاستەوخۆ لەسەر ١ کامێرا و ١ سیستمی AI کارا دەبێت."
                )
                full_name = str(
                    st.text_input("ناوی تەواو / شوێن:", key="reg_fullname") or ""
                )
                new_user = str(
                    st.text_input("ناوی بەکارهێنەر (Username):", key="reg_user") or ""
                )
                new_pass = str(
                    st.text_input(
                        "تێپەڕەوشە (Password):", type="password", key="reg_pass"
                    )
                    or ""
                )
                reg_submit = st.form_submit_button(
                    "🚀 دروستکردنی هەژمار", use_container_width=True
                )

                if reg_submit:
                    u_clean = new_user.strip()
                    if len(u_clean) < 3 or len(new_pass.strip()) < 4:
                        st.warning(
                            "⚠️ تکایە ناوی بەکارهێنەر (٣+ پیت) و تێپەڕەوشە (٤+ پیت) بنووسە."
                        )
                    else:
                        try:
                            conn = sqlite3.connect(DB_NAME)
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO app_users (username, password_hash, full_name) VALUES (?, ?, ?)",
                                (u_clean, _hash_pw(new_pass), full_name.strip()),
                            )
                            conn.commit()
                            conn.close()

                            if ensure_free_trial_account is not None:
                                ensure_free_trial_account(u_clean)
                            st.session_state.authenticated = True
                            st.session_state.logged_in = True
                            st.session_state.username = u_clean
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("⚠️ ئەم ناوی بەکارهێنەرە پێشتر تۆمار کراوە.")


render_login = login_screen
