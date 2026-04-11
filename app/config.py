# app/config.py
# 프로젝트 전역 설정 상수

import os

# ── 사용자 설정 ──────────────────────────────────────────────────────────────
OWNER_MAC_ADDRESS: str = "00:00:00:00:00:00"   # 집주인 스마트폰 블루투스 MAC 주소
RECORD_COOLDOWN: float = 5.0                    # 침입자 소실 후 녹화 유지 시간(초)
FRAME_SKIP_HOME: int = 3                        # 홈 모드: N 프레임마다 1회 AI 추론
FRAME_SKIP_AWAY: int = 2                        # 보안 모드: N 프레임마다 1회 AI 추론

# ── 시스템 설정 ──────────────────────────────────────────────────────────────
RECORD_DIR: str = "recordings"                  # 침입자 녹화 파일 저장 디렉토리

# 녹화 폴더 자동 생성
if not os.path.exists(RECORD_DIR):
    os.makedirs(RECORD_DIR)
