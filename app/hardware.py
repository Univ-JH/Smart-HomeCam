# app/hardware.py
# Sense HAT 하드웨어 추상화 레이어
# Sense HAT이 없는 환경(개발 PC 등)에서는 MockSense로 자동 대체

from sense_hat import SenseHat


class MockSense:
    """Sense HAT 미연결 환경을 위한 더미 객체."""
    def clear(self, *args) -> None:
        pass


try:
    sense = SenseHat()
    sense.clear()
    sense.low_light = True  # LED 자동 밝기 감소 모드
    print("[INFO] Sense HAT 초기화 완료")
except Exception as e:
    print(f"[WARN] Sense HAT 로드 실패, MockSense 사용: {e}")
    sense = MockSense()
