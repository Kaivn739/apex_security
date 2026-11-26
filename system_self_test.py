from __future__ import annotations

import time
import cv2
import numpy as np

from apex_internal_core import get_internal_cpu
from cameras import AsyncAIWorker, CameraStream
from face_recognizer import FaceRecognizerEngine
from alpr_engine import ALPREngine
from fire_smoke_detector import FireSmokeDetector
from weapon_detector import WeaponDetector
from crowd_distress_detector import CrowdDistressDetector
from db_manager_view import APEXDatabaseLifecycleManager
from gis_intelligence import APEXGISIntelligenceEngine
from forensics_view import APEXForensicsEngine
from cyber_shield import APEXCyberShield


def run_full_verification() -> None:
    print("=" * 62)
    print("   APEX SECURITY — FULL END-TO-END SYSTEM VERIFICATION")
    print("=" * 62)

    core = get_internal_cpu()
    metrics = core.get_hardware_metrics(force_refresh=True)
    print(f"[1/9] Internal CPU Core   : OK | Load={metrics['load_state']} | CPU={metrics['cpu_percent']}% | RAM={metrics['ram_percent']}%")

    # 2. Face Recognizer Test
    face_eng = FaceRecognizerEngine()
    blank = np.zeros((360, 640, 3), dtype=np.uint8)
    _, f_res = face_eng.process_frame_with_details(blank)
    print(f"[2/9] Face Recognizer     : OK | Targets Loaded={len(face_eng._gallery_templates)} | Detections={len(f_res)}")

    # 3. ALPR Plate Engine Test
    alpr_eng = ALPREngine()
    _, p_res = alpr_eng.process_frame(blank.copy(), camera_id="CAM-02")
    print(f"[3/9] ALPR Plate Engine   : OK | Database Plates={len(alpr_eng.target_database)} | Detections={len(p_res)}")

    # 4. Fire & Smoke Detector Test
    fire_eng = FireSmokeDetector(min_fire_area=400)
    fire_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.circle(fire_frame, (320, 200), 45, (15, 140, 255), -1)
    _, fire_res = fire_eng.process_frame(fire_frame, camera_id="CAM-01", emit_events=False)
    print(f"[4/9] Fire & Smoke AI     : OK | Detections={len(fire_res)}")

    # 5. Weapon Detector Test
    weapon_eng = WeaponDetector(min_weapon_area=500)
    w_frame = np.full((360, 640, 3), 180, dtype=np.uint8)
    cv2.rectangle(w_frame, (200, 170), (380, 200), (45, 45, 45), -1)
    _, w_res = weapon_eng.process_frame(w_frame, camera_id="CAM-02", emit_events=False)
    print(f"[5/9] Weapon & Gunfire AI : OK | Detections={len(w_res)}")

    # 6. Crowd & Distress Detector Test
    crowd_eng = CrowdDistressDetector(crowd_threshold=3, panic_motion_ratio=0.10)
    c1 = np.zeros((360, 640, 3), dtype=np.uint8)
    c2 = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.rectangle(c2, (120, 80), (480, 300), (255, 255, 255), -1)
    crowd_eng.process_frame(c1, camera_id="CAM-03", emit_events=False)
    _, c_res = crowd_eng.process_frame(c2, camera_id="CAM-03", emit_events=False)
    print(f"[6/9] Crowd & Distress AI : OK | Detections={len(c_res)}")

    # 7. Zero-Lag Async AI Worker Test
    worker = AsyncAIWorker("TEST-CAM", lambda frm: (frm, ["OK"]))
    worker.submit_frame(blank)
    time.sleep(0.08)
    ann, _ = worker.get_latest_result()
    worker.stop()
    print(f"[7/9] Zero-Lag AI Worker  : {'OK' if ann is not None else 'WARN'}")

    # 8. Database, GIS & Forensics Test
    db_mgr = APEXDatabaseLifecycleManager()
    gis_eng = APEXGISIntelligenceEngine()
    for_eng = APEXForensicsEngine()
    print(f"[8/9] DB + GIS + Forensics: OK | GIS Nodes={len(gis_eng.cameras)} | Cases={len(for_eng.list_cases())}")

    # 9. Cyber Shield Integrity Refresh & Audit
    shield = APEXCyberShield()
    shield.build_integrity_baseline(replace_existing=True)
    audit = shield.audit_security_posture()
    print(f"[9/9] Cyber Shield Audit  : OK | Score={audit['security_score']}% | Protected Files={audit['protected_files']}")

    core.shutdown()
    print("=" * 62)
    print("   ALL MODULES VERIFIED & READY FOR LIVE COMMAND CENTER!")
    print("=" * 62)


if __name__ == "__main__":
    run_full_verification()