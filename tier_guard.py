from typing import Dict, Any, Tuple
import streamlit as st
from subscription_manager import get_user_access_profile, APEX_TIERS
from kyc_tier_extension import render_kyc_package_and_payment_box

ALL_DASHBOARD_MODULES = [
    "🖥️ MAIN CAMERA MATRIX",
    "🎬 VIDEO TEST LAB (تۆماری ڤیدیۆ)",
    "🧪 TESTER CAMERAS (وێبکام و RTSP)",
    "🗺️ REAL-TIME MAP TRACKER (نەخشەی ژێندراو)",
    "⚙️ CAMERA CONFIG & LINKS",
    "🔍 HISTORICAL ANALYTICS (داتای کۆن)",
    "🚨 EMERGENCY ALERTS (ئاگاداری)",
    "🚀 UPGRADE & KYC (بەرزکردنەوەی پاکێج)",
]


def get_current_user_profile() -> Dict[str, Any]:
    username = str(st.session_state.get("username", "guest"))
    return get_user_access_profile(username)


def render_sidebar_tier_status() -> Dict[str, Any]:
    """نیشاندانی دۆخی پاکێجی ئێستا، سنووری کامێرا، و سیستمی AI چالاک لە سایدباردا"""
    profile = get_current_user_profile()
    tier_info = profile["tier_info"]
    ai_feat = tier_info["ai_features"]

    active_systems = [
        name
        for name, enabled in [
            ("Face ID", ai_feat.get("face_id", False)),
            ("ALPR تابلۆ", ai_feat.get("alpr", False)),
            ("GIS نەخشە", ai_feat.get("gis_map", False)),
            ("Threat AI", ai_feat.get("threat_detection", False)),
        ]
        if enabled
    ]

    with st.sidebar:
        with st.container(border=True):
            st.markdown(f"**👤 بەکارهێنەر:** `{profile['username']}`")
            st.markdown(f"**📦 ئاست:** {tier_info['title']}")
            st.caption(
                f"📹 سنووری کامێرا: **{tier_info['max_cameras']} کامێرا** | "
                f"🤖 سیستمی چالاک: **{', '.join(active_systems) if active_systems else 'None'}**"
            )
            if profile.get("is_pending_upgrade"):
                req_title = APEX_TIERS.get(profile["requested_tier"], {}).get(
                    "title", ""
                )
                st.info(
                    f"⏳ داواکاریی KYC بۆ ({req_title}) لەژێر پشکنینی بەڕێوەبەردایە."
                )

    return profile


def enforce_camera_limit(
    camera_config: Dict[int, Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:
    """سنووردارکردنی کامێراکان بەپێی پاکێج (بۆ Free Trial تەنها ١ کامێرا دەگەڕێنێتەوە)"""
    profile = get_current_user_profile()
    max_cams = int(profile["tier_info"]["max_cameras"])
    sorted_ids = sorted(camera_config.keys())[:max_cams]
    return {cid: camera_config[cid] for cid in sorted_ids}


def enforce_ai_permissions(
    face_requested: bool, alpr_requested: bool
) -> Tuple[bool, bool]:
    """تەنها ڕێگە بەو سیستمانەی AI دەدات کە لە پاکێجی کڕیارەکەدا کراوەن (Free Trial = تەنها Face ID)"""
    profile = get_current_user_profile()
    ai_feat = profile["tier_info"]["ai_features"]
    face_allowed = bool(face_requested and ai_feat.get("face_id", False))
    alpr_allowed = bool(alpr_requested and ai_feat.get("alpr", False))
    return face_allowed, alpr_allowed


def render_locked_or_upgrade_view(selected_module: str) -> bool:
    """
    ئەگەر بەکارهێنەر پەڕەی Upgrade & KYC یان بەشێکی قوفڵکراوی (🔒) هەڵبژارد،
    فۆرمی KYC و هەڵبژاردنی پاکێج پیشان دەدات و True دەگەڕێنێتەوە.
    """
    profile = get_current_user_profile()
    allowed = profile["tier_info"]["allowed_modules"]
    clean_name = selected_module.replace("🔒 ", "")

    if (
        clean_name == "🚀 UPGRADE & KYC (بەرزکردنەوەی پاکێج)"
        or clean_name not in allowed
    ):
        if clean_name != "🚀 UPGRADE & KYC (بەرزکردنەوەی پاکێج)":
            st.warning(
                f"🔒 بەشی **{clean_name}** لە پاکێجی ئێستاتدا ({profile['tier_info']['title']}) داخراوە. "
                "تکایە فۆرمی KYC و بەرزکردنەوەی پاکێج لە خوارەوە پڕ بکەرەوە:"
            )
        render_kyc_package_and_payment_box(default_username=profile["username"])
        return True

    return False
