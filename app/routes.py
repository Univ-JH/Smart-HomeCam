# app/routes.py
# Flask Blueprint — HTTP 라우트 정의
# AI 추론 로직(inference.py)과 라우팅 로직을 분리하여 단일 책임 원칙을 준수합니다.

import os
import datetime

from flask import Blueprint, render_template, Response, request, send_from_directory

from . import config
from . import state
from .inference import generate_frames

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """메인 대시보드 — 카메라 피드 + 제어 패널."""
    return render_template(
        "index.html",
        is_home=state.is_owner_home,
        mode=state.control_mode,
        manual_on=state.is_manual_on,
        manual_val=state.manual_brightness,
    )


@bp.route("/video_feed")
def video_feed():
    """MJPEG 실시간 스트림 엔드포인트."""
    from app import vs  # 앱 초기화 후 참조 (순환 임포트 방지)
    return Response(
        generate_frames(vs),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@bp.route("/update_settings", methods=["POST"])
def update_settings():
    """제어 모드 및 밝기 설정을 즉시 반영합니다 (AJAX)."""
    c_mode = request.form.get("control_mode")
    m_val  = request.form.get("manual_val")
    m_on   = request.form.get("manual_on")

    if c_mode:
        state.control_mode = int(c_mode)
    if m_val:
        state.manual_brightness = int(m_val)
    state.is_manual_on = m_on is not None

    return "OK", 200


@bp.route("/recordings")
def recordings():
    """침입자 녹화 파일 목록 페이지."""
    files = []
    if os.path.exists(config.RECORD_DIR):
        for f in os.listdir(config.RECORD_DIR):
            if not f.endswith(".mp4"):
                continue
            path = os.path.join(config.RECORD_DIR, f)
            size_mb = round(os.path.getsize(path) / (1024 * 1024), 2)
            try:
                ts_str = f.replace("intruder_", "").replace(".mp4", "")
                dt_obj = datetime.datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                display_date = dt_obj.strftime("%Y년 %m월 %d일 %H:%M:%S")
            except ValueError:
                display_date = f

            files.append({
                "name": f,
                "date": display_date,
                "size": size_mb,
                "raw_time": os.path.getmtime(path),
            })

    files.sort(key=lambda x: x["raw_time"], reverse=True)
    return render_template("recordings.html", files=files)


@bp.route("/download/<filename>")
def download_file(filename: str):
    """녹화 파일 다운로드."""
    return send_from_directory(config.RECORD_DIR, filename, as_attachment=True)
