import os
from datetime import datetime
import streamlit as st
from subscription_manager import (
    APEX_TIERS,
    init_subscription_tables,
    register_kyc_and_payment_request,
)

RECEIPT_DIR = "kyc_receipts"
os.makedirs(RECEIPT_DIR, exist_ok=True)


def render_kyc_package_and_payment_box(default_username: str = ""):
    """
    مۆدیۆلی زیادکراو بۆ ناو kyc_engine.py:
    ڕێگە بە کڕیار دەدات ئاستی پێویستی خۆی هەڵبژێرێت و وەسڵی پارەدان بنێرێت
    """
    init_subscription_tables()

    st.markdown("### 💳 هەڵبژاردنی پاکێجی APEX و پشتڕاستکردنەوەی پارەدان")
    st.caption(
        "پاکێجەکەت بەپێی قەبارەی کارەکەت دیاری بکە تا بەشە گونجاوەکانی داشبۆردت بۆ چالاک بکرێت:"
    )

    tier_keys = list(APEX_TIERS.keys())
    selected_tier = st.selectbox(
        "📦 ئاستی خزمەتگوزاری هەڵبژێرە:",
        options=tier_keys,
        format_func=lambda k: f"{APEX_TIERS[k]['title']} — تا {APEX_TIERS[k]['max_cameras']} کامێرا",
        key="kyc_selected_tier",
    )

    tier_details = APEX_TIERS[selected_tier]
    with st.container(border=True):
        st.markdown(f"**{tier_details['title']}**")
        st.write(
            f"• **سنووری کامێراکان:** تا `{tier_details['max_cameras']}` کامێرای ڕاستەوخۆ"
        )
        st.write(
            f"• **خێرایی شیکاریی AI:** `{tier_details['target_ai_fps']} FPS` بۆ هەر کامێرایەک"
        )
        features = tier_details["ai_features"]
        st.write(
            f"• **تواناکان:** Face ID: {'✅' if features['face_id'] else '❌'} | "
            f"ALPR تابلۆ: {'✅' if features['alpr'] else '❌'} | "
            f"نەخشەی GIS: {'✅' if features['gis_map'] else '❌'} | "
            f"ئاگر و شەڕ: {'✅' if features['threat_detection'] else '❌'}"
        )

    col1, col2 = st.columns(2)
    with col1:
        sub_username = st.text_input(
            "👤 ناوی بەکارهێنەر (هەمان ناوی فۆرمی KYC):",
            value=default_username,
            placeholder="نموونە: ahmad_store",
            key="kyc_sub_user",
        )
    with col2:
        payment_ref = st.text_input(
            "🧾 ژمارەی پسوولە / حەواڵە (Transaction ID):",
            placeholder="نموونە: FIB-992841 یان FastPay-4410",
            key="kyc_payment_ref",
        )

    receipt_file = st.file_uploader(
        "📎 وێنەی وەسڵی پارەدان باربکە (ئارەزوومەندانە):",
        type=["png", "jpg", "jpeg", "pdf"],
        key="kyc_receipt_upload",
    )

    if st.button("📨 ناردنی داواکاریی پاکێج و پارەدان", use_container_width=True):
        if not sub_username.strip() or not payment_ref.strip():
            st.error("⚠️ تکایە ناوی بەکارهێنەر و ژمارەی پسوولەی پارەدان پڕ بکەرەوە.")
            return False

        saved_ref = payment_ref.strip()
        if receipt_file is not None:
            safe_name = f"{sub_username.strip()}_{int(datetime.now().timestamp())}_{receipt_file.name}"
            file_path = os.path.join(RECEIPT_DIR, safe_name)
            with open(file_path, "wb") as f:
                f.write(receipt_file.getbuffer())
            saved_ref = f"{saved_ref} | File: {safe_name}"

        register_kyc_and_payment_request(
            username=sub_username.strip(),
            tier_code=selected_tier,
            payment_ref=saved_ref,
        )
        st.success(
            f"✅ داواکاریی پاکێجی **{tier_details['title']}** بۆ هەژماری `{sub_username.strip()}` تۆمار کرا و نێردرا بۆ بەڕێوەبەر."
        )
        return True
    return False
