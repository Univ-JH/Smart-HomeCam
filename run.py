# run.py

from app import create_app, vs, sense
from app import state

app = create_app()

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
    finally:
        # 서버 종료 시 리소스 해제
        print("\n[INFO] 서버 종료 중... 리소스 해제")
        vs.stop()
        sense.clear()
        if state.video_writer:
            state.video_writer.release()
