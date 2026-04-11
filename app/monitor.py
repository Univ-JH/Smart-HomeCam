# app/monitor.py
# 블루투스 기반 집주인 재실 감지 모듈
# 5초마다 지정된 MAC 주소 기기를 폴링하여 홈/보안 모드를 자동 전환합니다.

import time
import threading

import bluetooth

from . import config
from . import state


def _bluetooth_monitor() -> None:
    """블루투스 감시 루프 — 백그라운드 스레드에서 실행됩니다."""
    print(f"[BT] 블루투스 감시 시작... (Target MAC: {config.OWNER_MAC_ADDRESS})")

    while True:
        try:
            device_name = bluetooth.lookup_name(config.OWNER_MAC_ADDRESS, timeout=3)

            if device_name is not None:
                if not state.is_owner_home:
                    print(f"[BT] 스마트폰 감지됨! ({device_name}) → 홈 모드 전환 🏠")
                state.is_owner_home = True
            else:
                if state.is_owner_home:
                    print("[BT] 스마트폰 신호 끊김... → 보안 모드 전환 🚨")
                state.is_owner_home = False

        except Exception as e:
            print(f"[BT Error] {e}")

        time.sleep(5)


def start_monitoring() -> None:
    """블루투스 감시 데몬 스레드를 시작합니다."""
    t = threading.Thread(target=_bluetooth_monitor, daemon=True)
    t.start()
