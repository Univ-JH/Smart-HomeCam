# app/inference.py
# YOLOv8 AI 추론 엔진 — 자세 분석 / 제스처 인식 / 침입자 감지

import time
import datetime
from typing import Generator

import cv2
from ultralytics import YOLO

from . import config
from . import state
from .hardware import sense

# ── 모델 로드 (서버 시작 시 1회) ──────────────────────────────────────────────
print("[INFO] YOLOv8n-pose 모델 로딩 중...")
model = YOLO("yolov8n-pose.pt")


# ── 알림 ───────────────────────────────────────────────────────────────────────

def _send_intruder_notification(person_count: int) -> None:
    """침입자 감지 알림을 출력합니다 (5초 쿨다운)."""
    current_time = time.time()
    if current_time - state.last_alert_time > 5:
        print(f"\n[🚨 긴급] {datetime.datetime.now()} : {person_count}명의 침입자 감지!! 녹화중...\n")
        state.last_alert_time = current_time


# ── 자세 분류 ──────────────────────────────────────────────────────────────────

def _classify_posture(person, annotated_frame, box, index: int, votes: dict) -> None:
    """
    COCO 17개 키포인트를 기반으로 자세(서있음/앉음/누움)를 분류

    판별 로직:
      - Lying  : shoulder_width > torso_height × 0.8  (가로로 누운 방향)
      - Standing: |hip_y - knee_y| > torso_height × 0.6
      - Sitting : 그 외
    """
    x1, y1, x2, y2 = box
    posture_text = "Unknown"
    box_color = (200, 200, 200)

    if len(person) >= 17 and person[5][2] > 0.5 and person[11][2] > 0.5:
        ls, rs = person[5][:2], person[6][:2]   # 왼/오른 어깨
        lh, rh = person[11][:2], person[12][:2] # 왼/오른 엉덩이
        lk, rk = person[13][:2], person[14][:2] # 왼/오른 무릎

        shoulder_mid_y = (ls[1] + rs[1]) / 2
        hip_mid_y      = (lh[1] + rh[1]) / 2
        torso_height   = abs(shoulder_mid_y - hip_mid_y)
        shoulder_width = abs(ls[0] - rs[0])

        if shoulder_width > torso_height * 0.8:
            posture_text = "Lying"
            votes["Lying"] += 1
            box_color = (0, 0, 255)
        elif person[13][2] > 0.5 or person[14][2] > 0.5:
            knee_mid_y = (lk[1] + rk[1]) / 2
            if abs(hip_mid_y - knee_mid_y) > torso_height * 0.6:
                posture_text = "Standing"
                votes["Standing"] += 1
                box_color = (0, 255, 0)
            else:
                posture_text = "Sitting"
                votes["Sitting"] += 1
                box_color = (0, 255, 255)
        else:
            posture_text = "Sitting"
            votes["Sitting"] += 1
            box_color = (0, 255, 255)

    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, 2)
    cv2.putText(annotated_frame, f"P{index + 1}: {posture_text}",
                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)


def _apply_gesture_control(person, annotated_frame, box) -> str:
    """
    제스처 제어를 적용하고 상태 텍스트를 반환

    제스처 기준 (COCO 키포인트):
      - 오른손 UP + 왼손 DOWN → 밝기 +10
      - 왼손 UP + 오른손 DOWN → 밝기 -10
      - 양손 모두 UP          → 밝기 최대 (255)
    """
    x1, y1, x2, y2 = box
    status_text = ""
    cv2.putText(annotated_frame, "CMD USER",
                (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)

    ls, rs = person[5][:2], person[6][:2]   # 어깨
    lw, rw = person[9][:2], person[10][:2]  # 손목

    if person[9][2] > 0.5 and person[10][2] > 0.5:
        if rw[1] < rs[1] and lw[1] > ls[1]:
            state.current_brightness = min(255, state.current_brightness + 10)
            status_text = "Gesture: UP (+)"
        elif lw[1] < ls[1] and rw[1] > rs[1]:
            state.current_brightness = max(0, state.current_brightness - 10)
            status_text = "Gesture: DOWN (-)"
        elif lw[1] < ls[1] and rw[1] < rs[1]:
            state.current_brightness = 255
            status_text = "Gesture: MAX"

    return status_text


# ── 메인 스트리밍 제너레이터 ──────────────────────────────────────────────────

def generate_frames(vs) -> Generator[bytes, None, None]:
    """
    카메라 프레임에 AI 추론을 적용하고 MJPEG 스트림으로 yield
    """
    frame_count = 0

    while vs.read() is None:
        time.sleep(0.1)

    last_output_frame = vs.read().copy()
    status_text = ""

    while True:
        frame = vs.read()
        if frame is None:
            continue

        frame_count += 1
        skip_rate = config.FRAME_SKIP_HOME if state.is_owner_home else config.FRAME_SKIP_AWAY

        # ── AI 추론 (FRAME_SKIP 주기마다 실행) ──────────────────────────────
        if frame_count % skip_rate == 0:
            person_count = 0
            status_text = ""
            infer_size = 448 if state.is_owner_home else 192  # 홈=정확도 우선, 보안=속도 우선

            try:
                results = model(frame, conf=0.5, verbose=False,
                                device="cpu", imgsz=infer_size, classes=[0])

                # ── [분기 A] 홈 모드 ────────────────────────────────────────
                if state.is_owner_home:
                    # 홈 모드 전환 시 진행 중이던 녹화 종료
                    if state.is_recording and state.video_writer is not None:
                        state.video_writer.release()
                        state.video_writer = None
                        state.is_recording = False
                        print("[INFO] 홈 모드 전환으로 녹화 종료")

                    annotated_frame = results[0].plot()

                    if results[0].keypoints is not None:
                        raw_keypoints = results[0].keypoints.data.cpu().numpy()
                        raw_boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)

                        people_data = [
                            {"keypoints": kpt, "box": box,
                             "area": (box[2] - box[0]) * (box[3] - box[1])}
                            for kpt, box in zip(raw_keypoints, raw_boxes)
                        ]
                        people_data.sort(key=lambda x: x["area"], reverse=True)
                        person_count = len(people_data)

                        if person_count > 0:
                            votes = {"Standing": 0, "Sitting": 0, "Lying": 0}

                            for i, p_data in enumerate(people_data):
                                person = p_data["keypoints"]
                                box    = p_data["box"]

                                _classify_posture(person, annotated_frame, box, i, votes)

                                # 제스처 제어: 화면에서 가장 큰(첫 번째) 사람만 적용
                                if state.control_mode == 2 and i == 0:
                                    status_text = _apply_gesture_control(
                                        person, annotated_frame, box)

                            # 자동 모드: 다수결 자세 → 밝기 매핑
                            if state.control_mode == 1:
                                winner = max(votes, key=votes.get)
                                if votes[winner] > 0:
                                    if winner == "Standing":
                                        state.current_brightness = 255
                                        status_text = "Auto: Active (Max)"
                                    elif winner == "Sitting":
                                        state.current_brightness = 128
                                        status_text = "Auto: Relax (Mid)"
                                    elif winner == "Lying":
                                        state.current_brightness = 30
                                        status_text = "Auto: Sleep (Min)"

                    # 수동 모드
                    if state.control_mode == 3:
                        state.current_brightness = (
                            state.manual_brightness if state.is_manual_on else 0)
                        status_text = (f"Manual: {state.current_brightness}"
                                       if state.is_manual_on else "Manual: OFF")

                    last_output_frame = annotated_frame

                # ── [분기 B] 보안 모드 ──────────────────────────────────────
                else:
                    boxes = results[0].boxes
                    person_count = len(boxes)

                    if person_count > 0:
                        state.last_intruder_detect_time = time.time()
                        for box in boxes.xyxy.cpu().numpy().astype(int):
                            x1, y1, x2, y2 = box
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                            cv2.putText(frame, "INTRUDER", (x1, y1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                    last_output_frame = frame

            except Exception as e:
                print(f"[AI Error] {e}")
                last_output_frame = frame

            frame_count = 0

        # ── OSD 오버레이 ─────────────────────────────────────────────────────
        display_frame = last_output_frame.copy()
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        (text_w, _), _ = cv2.getTextSize(now_str, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        # 타임스탬프 (우측 상단, 외곽선 처리)
        cv2.putText(display_frame, now_str, (640 - text_w - 10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
        cv2.putText(display_frame, now_str, (640 - text_w - 10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        if state.is_owner_home:
            cv2.putText(display_frame, f"Mode: {state.control_mode}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(display_frame, f"Light: {state.current_brightness}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(display_frame, status_text,
                        (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            try:
                b = state.current_brightness
                sense.clear(b, b, b)  # R=G=B → 백색 조명
            except Exception:
                pass

        else:
            cv2.putText(display_frame, "SECURITY MODE",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            should_record = (
                state.last_intruder_detect_time != 0
                and time.time() - state.last_intruder_detect_time < config.RECORD_COOLDOWN
            )

            if should_record:
                if state.video_writer is None:
                    filename = (f"{config.RECORD_DIR}/"
                                f"intruder_{now.strftime('%Y%m%d_%H%M%S')}.mp4")
                    state.video_writer = cv2.VideoWriter(
                        filename, cv2.VideoWriter_fourcc(*"mp4v"), 20.0, (640, 480))
                    state.is_recording = True
                    print(f"[REC] 녹화 시작: {filename}")

                state.video_writer.write(display_frame)

                # 깜빡이는 REC 표시
                if int(time.time() * 2) % 2 == 0:
                    cv2.circle(display_frame, (25, 60), 10, (0, 0, 255), -1)
                    cv2.putText(display_frame, "AUTO RECORDING",
                                (45, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                try:
                    sense.clear(255, 0, 0)  # 빨간 경보 LED
                except Exception:
                    pass

                if person_count > 0:
                    _send_intruder_notification(person_count)

            else:
                if state.is_recording:
                    if state.video_writer is not None:
                        state.video_writer.release()
                        state.video_writer = None
                    state.is_recording = False
                    print("[REC] 녹화 종료 (대기 시간 종료)")
                try:
                    sense.clear(0, 0, 0)  # 소등
                except Exception:
                    pass

        # ── JPEG 인코딩 → HTTP multipart yield ──────────────────────────────
        ret, buffer = cv2.imencode(".jpg", display_frame)
        if ret:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n"
                   + buffer.tobytes()
                   + b"\r\n")
