import sqlite3
from datetime import datetime
from typing import Dict, Any

DB_NAME = "apex_security.db"

# ============================================================
# پێناسەی هەموو ئاستەکانی APEX (لە Free Trial تا Enterprise 60+)
# ============================================================
APEX_TIERS: Dict[str, Dict[str, Any]] = {
    "FREE_TRIAL": {
        "title": "🆓 پاکێجی تاقیکردنەوەی خۆڕایی (Free Trial)",
        "max_cameras": 1,
        "target_ai_fps": 4.0,
        "min_free_disk_gb": 5.0,
        "allowed_modules": [
            "🖥️ MAIN CAMERA MATRIX",
            "⚙️ CAMERA CONFIG & LINKS",
            "🚀 UPGRADE & KYC (بەرزکردنەوەی پاکێج)",
        ],
        "ai_features": {
            "face_id": True,  # تەنها ١ سیستمی AI کارایە بۆ تاقیکردنەوە
            "alpr": False,
            "threat_detection": False,
            "gis_map": False,
        },
    },
    "BASIC_SHOP": {
        "title": "🏪 پاکێجی دوکان و ماڵان (Basic)",
        "max_cameras": 4,
        "target_ai_fps": 5.0,
        "min_free_disk_gb": 10.0,
        "allowed_modules": [
            "🖥️ MAIN CAMERA MATRIX",
            "⚙️ CAMERA CONFIG & LINKS",
            "🚨 EMERGENCY ALERTS (ئاگاداری)",
            "🚀 UPGRADE & KYC (بەرزکردنەوەی پاکێج)",
        ],
        "ai_features": {
            "face_id": True,
            "alpr": False,
            "threat_detection": False,
            "gis_map": False,
        },
    },
    "PRO_BUSINESS": {
        "title": "🏢 پاکێجی کۆمپانیا و دامەزراوە (Pro Business)",
        "max_cameras": 24,
        "target_ai_fps": 10.0,
        "min_free_disk_gb": 20.0,
        "allowed_modules": [
            "🖥️ MAIN CAMERA MATRIX",
            "🎬 VIDEO TEST LAB (تۆماری ڤیدیۆ)",
            "🧪 TESTER CAMERAS (وێبکام و RTSP)",
            "⚙️ CAMERA CONFIG & LINKS",
            "🔍 HISTORICAL ANALYTICS (داتای کۆن)",
            "🚨 EMERGENCY ALERTS (ئاگاداری)",
            "🚀 UPGRADE & KYC (بەرزکردنەوەی پاکێج)",
        ],
        "ai_features": {
            "face_id": True,
            "alpr": True,
            "threat_detection": False,
            "gis_map": False,
        },
    },
    "ENTERPRISE_CITY": {
        "title": "🏛️ پاکێجی شار و ئاسایشی گشتی (Enterprise 60+)",
        "max_cameras": 64,
        "target_ai_fps": 12.0,
        "min_free_disk_gb": 30.0,
        "allowed_modules": [
            "🖥️ MAIN CAMERA MATRIX",
            "🎬 VIDEO TEST LAB (تۆماری ڤیدیۆ)",
            "🧪 TESTER CAMERAS (وێبکام و RTSP)",
            "🗺️ REAL-TIME MAP TRACKER (نەخشەی ژێندراو)",
            "⚙️ CAMERA CONFIG & LINKS",
            "🔍 HISTORICAL ANALYTICS (داتای کۆن)",
            "🚨 EMERGENCY ALERTS (ئاگاداری)",
        ],
        "ai_features": {
            "face_id": True,
            "alpr": True,
            "threat_detection": True,
            "gis_map": True,
        },
    },
}


def init_subscription_tables() -> None:
    """دروستکردنی خشتەی بەشداریکردن و پشتڕاستکردنەوەی KYC لە داتابەیسدا"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            tier_code TEXT NOT NULL DEFAULT 'FREE_TRIAL',
            requested_tier TEXT DEFAULT 'FREE_TRIAL',
            kyc_verified INTEGER NOT NULL DEFAULT 0,
            payment_verified INTEGER NOT NULL DEFAULT 0,
            payment_reference TEXT,
            approved_by TEXT,
            updated_at TEXT
        )
    """)

    # دڵنیابوونەوە لە بوونی ستوونی requested_tier ئەگەر خشتەکە پێشتر دروست کرابێت
    cursor.execute("PRAGMA table_info(user_subscriptions)")
    cols = [c[1] for c in cursor.fetchall()]
    if "requested_tier" not in cols:
        cursor.execute(
            "ALTER TABLE user_subscriptions ADD COLUMN requested_tier TEXT DEFAULT 'FREE_TRIAL'"
        )

    # هەژماری سەرەکی admin هەمیشە Enterpriseـە
    cursor.execute(
        """
        INSERT OR IGNORE INTO user_subscriptions
        (username, tier_code, requested_tier, kyc_verified, payment_verified, payment_reference, approved_by, updated_at)
        VALUES ('admin', 'ENTERPRISE_CITY', 'ENTERPRISE_CITY', 1, 1, 'SYSTEM_OWNER', 'ROOT', ?)
    """,
        (datetime.now().isoformat(),),
    )

    conn.commit()
    conn.close()


def ensure_free_trial_account(username: str) -> None:
    """چالاککردنی خۆکاری پاکێجی خۆڕایی (١ کامێرا + ١ سیستمی AI) بۆ هەر هەژمارێکی نوێ"""
    init_subscription_tables()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO user_subscriptions
        (username, tier_code, requested_tier, kyc_verified, payment_verified, payment_reference, updated_at)
        VALUES (?, 'FREE_TRIAL', 'FREE_TRIAL', 0, 0, 'FREE_TRIAL_ACTIVE', ?)
    """,
        (str(username), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def register_kyc_and_payment_request(
    username: str, tier_code: str, payment_ref: str
) -> bool:
    """تۆمارکردنی داواکاریی KYC و بەرزکردنەوەی پاکێج بەبێ وەستاندنی Free Trialـی کڕیار"""
    if tier_code not in APEX_TIERS or tier_code == "FREE_TRIAL":
        tier_code = "BASIC_SHOP"

    ensure_free_trial_account(username)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE user_subscriptions
        SET requested_tier = ?,
            payment_reference = ?,
            updated_at = ?
        WHERE username = ?
    """,
        (str(tier_code), str(payment_ref), datetime.now().isoformat(), str(username)),
    )
    conn.commit()
    conn.close()
    return True


def verify_kyc_and_payment(
    username: str, tier_code: str, admin_user: str = "admin"
) -> bool:
    """پشتڕاستکردنەوەی KYC و پارەدان لەلایەن بەڕێوەبەرەوە و بەرزکردنەوەی پاکێج"""
    if tier_code not in APEX_TIERS:
        return False

    ensure_free_trial_account(username)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE user_subscriptions
        SET tier_code = ?,
            requested_tier = ?,
            kyc_verified = 1,
            payment_verified = 1,
            approved_by = ?,
            updated_at = ?
        WHERE username = ?
    """,
        (
            str(tier_code),
            str(tier_code),
            str(admin_user),
            datetime.now().isoformat(),
            str(username),
        ),
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_user_access_profile(username: str) -> Dict[str, Any]:
    """
    گەڕاندنەوەی پڕۆفایلی کڕیار:
    - هەموو کڕیارێکی نوێ یان چاوەڕوانی KYC بە شێوەی خۆکار لەسەر FREE_TRIAL (١ کامێرا + ١ AI) کارایە.
    - دوای پەسەندکردنی Admin دەگوازرێتەوە بۆ پاکێجە بەرزەکەی.
    """
    ensure_free_trial_account(username)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT tier_code, requested_tier, kyc_verified, payment_verified, payment_reference
        FROM user_subscriptions
        WHERE username = ?
    """,
        (str(username),),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        active_tier = "FREE_TRIAL"
        req_tier = "FREE_TRIAL"
        kyc_ok, pay_ok, pay_ref = 0, 0, "FREE_TRIAL_ACTIVE"
    else:
        db_tier, req_tier, kyc_ok, pay_ok, pay_ref = row
        # ئەگەر هێشتا Admin پەسەندی نەکردبێت، لەسەر FREE_TRIAL دەمێنێتەوە
        if kyc_ok == 1 and pay_ok == 1 and db_tier in APEX_TIERS:
            active_tier = db_tier
        else:
            active_tier = "FREE_TRIAL"

    tier_info = APEX_TIERS[active_tier]
    is_pending_upgrade = (
        kyc_ok == 0
        and req_tier not in (None, "", "FREE_TRIAL")
        and pay_ref not in (None, "", "FREE_TRIAL_ACTIVE")
    )

    return {
        "username": username,
        "is_active": True,  # هەمیشە چالاکە (لایەنی کەم لەسەر Free Trial)
        "kyc_verified": bool(kyc_ok == 1),
        "payment_verified": bool(pay_ok == 1),
        "is_pending_upgrade": is_pending_upgrade,
        "requested_tier": req_tier,
        "payment_reference": pay_ref,
        "tier_code": active_tier,
        "tier_info": tier_info,
    }
