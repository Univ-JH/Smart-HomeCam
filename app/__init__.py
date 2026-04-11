# app/__init__.py
# Flask Application Factory — 앱 초기화 및 하드웨어 리소스 바인딩

from flask import Flask

from .camera import VideoStream
from .hardware import sense
from .monitor import start_monitoring

# ── 하드웨어 & 스트림 초기화 (앱 생명주기 동안 유지) ──────────────────────────
print("[INFO] 카메라 스트림 초기화 중...")
vs = VideoStream(src=0).start()
start_monitoring()  # 블루투스 감시 백그라운드 스레드 시작


def create_app() -> Flask:
    """Flask 애플리케이션 팩토리 함수."""
    app = Flask(__name__)

    from .routes import bp
    app.register_blueprint(bp)

    return app
