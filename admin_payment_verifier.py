import random
import string
import sqlite3
import streamlit as st
from subscription_manager import (
    APEX_TIERS,
    DB_NAME,
    init_subscription_tables,
    verify_kyc_and_payment,
)


def _generate_access_code(length: int = 8) -> str:
    """دروستکردنی کۆدی چوونەژوورەوەی ٨ نیشانەیی هاوشێوەی ستانداردی admin.py"""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def render_admin_subscription_approvals(admin_username: str = "admin"):
    """
    مۆدیۆلی زیادکراو بۆ ناو admin.py:
    پشکنینی داواکارییەکانی KYC + پارەدان و کردنەوەی بەشەکانی داشبۆرد بۆ کڕیار
    """
    init_subscription_tables()

    st.markdown("### 💰 پەسەندکردنی KYC، پارەدان و چالاککردنی پاکێجی کڕیاران")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, tier_code, kyc_verified, payment_verified, payment_reference, updated_at
        FROM user_subscriptions
        WHERE username != 'admin'
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        st.info("📭 هیچ داواکارییەکی نوێی بەشداریکردن تۆمار نەکراوە.")
        return

    for row in rows:
        sub_id, uname, t_code, kyc_ok, pay_ok, pay_ref, updated_at = row
        is_approved = kyc_ok == 1 and pay_ok == 1
        status_badge = "🟢 چالاککراوە" if is_approved else "🟡 چاوەڕوانی پەسەندکردن"

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1.5])
            with c1:
                st.markdown(f"**👤 کڕیار:** `{uname}` ({status_badge})")
                st.caption(f"🕒 کاتی نوێکردنەوە: {updated_at}")
            with c2:
                st.write(f"🧾 **پسوولەی پارەدان:** `{pay_ref}`")
                tier_options = list(APEX_TIERS.keys())
                default_idx = (
                    tier_options.index(t_code) if t_code in tier_options else 0
                )
                chosen_tier = st.selectbox(
                    "پاکێجی پەسەندکراو:",
                    options=tier_options,
                    index=default_idx,
                    format_func=lambda k: APEX_TIERS[k]["title"],
                    key=f"adm_tier_{sub_id}",
                )
            with c3:
                if st.button(
                    "✅ پەسەندکردن و کۆد",
                    key=f"adm_approve_{sub_id}",
                    use_container_width=True,
                ):
                    ok = verify_kyc_and_payment(
                        username=uname,
                        tier_code=chosen_tier,
                        admin_user=admin_username,
                    )
                    if ok:
                        access_code = _generate_access_code(8)
                        st.success(f"🎉 چالاک کرا! Access Code: `{access_code}`")
                        st.toast(f"پاکێجی {chosen_tier} بۆ {uname} کرایەوە", icon="✅")
