# app/state.py
# 멀티스레드 환경에서 공유되는 전역 상태 변수
# 모듈을 싱글톤처럼 사용: `from app import state` → `state.is_owner_home`

import cv2

# ── 운영 모드 ─────────────────────────────────────────────────────────────────
is_owner_home: bool = True  # True = 홈 모드 / False = 보안 모드

# ── 조명 제어 ─────────────────────────────────────────────────────────────────
control_mode: int = 1       # 1 = 자동(자세), 2 = 제스처, 3 = 수동
manual_brightness: int = 100
is_manual_on: bool = True
current_brightness: int = 100

# ── 알림 쿨다운 ───────────────────────────────────────────────────────────────
last_alert_time: float = 0

# ── 녹화 상태 ─────────────────────────────────────────────────────────────────
video_writer: cv2.VideoWriter = None
is_recording: bool = False
last_intruder_detect_time: float = 0
