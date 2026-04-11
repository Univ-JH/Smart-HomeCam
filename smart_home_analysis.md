# 🏠 Smart AI Home Cam — 프로젝트 심층 분석 보고서

> **과목**: 임베디드 시스템 및 실습 (3학년 2학기 팀 프로젝트)  
> **플랫폼**: Raspberry Pi (Linux, V4L2 카메라)  
> **분석일**: 2026-04-10

---

## 1. 프로젝트 개요

**Smart AI Home Cam**은 Raspberry Pi 위에서 동작하는 AI 기반 스마트 홈 보안·조명 제어 시스템이다.  
블루투스로 스마트폰(집주인) 존재 여부를 감지하여 **두 가지 핵심 모드** 중 하나로 자동 전환된다.

| 모드 | 트리거 | 주요 기능 |
|------|--------|-----------|
| **홈 모드** | 블루투스 폰 감지됨 | AI 자세 분석 → 조명 자동/제스처/수동 제어 |
| **보안 모드** | 블루투스 신호 없음 | 사람 침입 감지 → 자동 영상 녹화 + 경보 |

---

## 2. 프로젝트 파일 구조

```
smart_home/
├── main.py              ← Flask 앱 + AI 인퍼런스 + 라우트 (핵심, 280줄)
├── config.py            ← 전역 설정 상수
├── global_state.py      ← 공유 상태 변수 (전역 객체 역할)
├── hardware.py          ← Sense HAT 추상화 레이어
├── camera.py            ← 카메라 스트림 스레드
├── monitor.py           ← 블루투스 감시 스레드
├── static/
│   └── manifest.json    ← PWA 웹앱 매니페스트
└── templates/
    ├── base.html        ← 공통 레이아웃 (Navbar + 하단 탭바)
    ├── index.html       ← 메인 대시보드 (영상 + 제어판)
    └── recordings.html  ← 녹화 파일 목록 + 다운로드
```

---

## 3. 기술 스택 상세

### 3.1 백엔드 / 서버 레이어
| 기술 | 버전/비고 | 역할 |
|------|----------|------|
| **Python** | 3.x | 메인 언어 |
| **Flask** | latest | HTTP 서버, 라우팅, Jinja2 템플릿 |
| **OpenCV (cv2)** | 4.x | 카메라 캡처, 영상 처리, JPEG 인코딩, VideoWriter |
| **Ultralytics YOLO** | v8n-pose | AI 인체 감지 + 포즈 키포인트 추출 |
| **PyBluez (bluetooth)** | latest | 블루투스 디바이스 이름 조회 |
| **sense_hat** | RPi 전용 | Sense HAT LED 매트릭스 제어 |
| **threading** | stdlib | 카메라/블루투스 백그라운드 스레드 |

### 3.2 프론트엔드 레이어
| 기술 | 역할 |
|------|------|
| **Flask/Jinja2** | 서버사이드 HTML 렌더링 |
| **Bootstrap 5.3** | 반응형 레이아웃, 컴포넌트 |
| **Bootstrap Icons** | 아이콘 폰트 |
| **Multipart MJPEG** | `/video_feed` 브라우저 스트리밍 |
| **PWA manifest.json** | 홈 화면 추가 / 앱처럼 실행 |

### 3.3 하드웨어 레이어
| 하드웨어 | 인터페이스 | 역할 |
|---------|-----------|------|
| **USB/CSI 카메라** | V4L2, MJPG 640×480 | 영상 입력 |
| **Sense HAT** | I²C (sense_hat 라이브러리) | RGB LED 조명 출력 |
| **스마트폰 (집주인)** | Bluetooth Classic | 재실 감지 신호 |

---

## 4. 모듈별 심층 분석

### 4.1 `config.py` — 설정 상수 모듈

```python
OWNER_MAC_ADDRESS = "A4:75:B9:A7:EF:2F"  # 블루투스 MAC
RECORD_COOLDOWN   = 5.0    # 침입자 소실 후 녹화 유지(초)
FRAME_SKIP_HOME   = 3      # 홈 모드: 3프레임마다 1회 AI 추론
FRAME_SKIP_AWAY   = 2      # 보안 모드: 2프레임마다 1회 AI 추론
RECORD_DIR        = "recordings"  # 녹화 파일 저장 폴더
```

**설계 포인트:**
- 하드코딩 배제: 모든 조정 가능한 값을 `config.py` 하나에 집중
- 서버 시작 시 `os.makedirs(RECORD_DIR)`로 폴더 자동 생성
- `FRAME_SKIP`이 보안 모드에서 더 작은 이유: 홈 모드는 포즈 추론(무거움)을 자주 할 필요가 없고, 보안 모드는 침입자를 빠르게 탐지해야 하기 때문

---

### 4.2 `global_state.py` — 공유 상태 모듈

```python
is_owner_home    = True   # 홈 ↔ 보안 토글
control_mode     = 1      # 1=자동(자세), 2=제스처, 3=수동
manual_brightness= 100
is_manual_on     = True
current_brightness= 100
last_alert_time  = 0      # 알림 쿨다운 타임스탬프

video_writer     = None   # cv2.VideoWriter 인스턴스
is_recording     = False
last_intruder_detect_time = 0
```

**설계 패턴 분석:**
- Python 모듈을 **싱글톤 객체**처럼 사용하는 패턴
- `import global_state as state` 후 `state.변수명`으로 접근
- Flask는 멀티스레드(`threaded=True`)로 동작하므로, 여러 스레드(블루투스 스레드, 카메라 스레드, 웹 요청 스레드)가 같은 `state.*` 변수를 공유
- **잠재적 Race Condition**: `threading.Lock` 없이 변수를 공유하고 있음. Python GIL이 일부 보호하지만 원칙적으로는 Lock이 필요

---

### 4.3 `hardware.py` — Sense HAT 추상화 레이어

```python
from sense_hat import SenseHat
try:
    sense = SenseHat()
    sense.clear()
    sense.low_light = True
except Exception as e:
    class MockSense:
        def clear(self, *args): pass
    sense = MockSense()
```

**설계 포인트:**
- **Graceful Degradation 패턴**: Sense HAT 없는 환경(개발 PC 등)에서도 `MockSense`로 대체하여 앱이 중단되지 않음
- `sense.clear(R, G, B)`: LED 매트릭스 전체를 단색으로 채움 → 조명 시뮬레이션
- `low_light = True`: LED 밝기 자동 감소 모드
- **조명 매핑**: `sense.clear(brightness, brightness, brightness)` → R=G=B이므로 항상 흰색, 밝기만 가변

---

### 4.4 `camera.py` — 비동기 카메라 스트림

```python
class VideoStream:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        ...
    def start(self):
        threading.Thread(target=self.update, daemon=True).start()
    def update(self):  # 백그라운드 스레드
        while not self.stopped:
            self.ret, self.frame = self.cap.read()
    def read(self):
        return self.frame
```

**핵심 기술: Threaded Camera Pattern**
- `cv2.VideoCapture.read()`는 **블로킹 I/O** → 메인 루프에서 직접 호출하면 FPS 저하
- 별도 스레드에서 지속적으로 `cap.read()`를 호출 → 항상 최신 프레임을 메모리에 유지
- 메인 루프는 `vs.read()`로 **즉시 최신 프레임**을 가져옴 → I/O 병목 제거
- `cv2.CAP_V4L2`: Raspberry Pi 리눅스 환경의 Video4Linux2 드라이버 명시적 사용
- `MJPG` 포맷: USB 카메라 하드웨어 압축 → 전송 대역폭 절약

---

### 4.5 `monitor.py` — 블루투스 재실 감지 스레드

```python
def bluetooth_monitor():
    while True:
        result = bluetooth.lookup_name(OWNER_MAC_ADDRESS, timeout=3)
        if result is not None:
            state.is_owner_home = True   # 홈 모드
        else:
            state.is_owner_home = False  # 보안 모드
        time.sleep(5)  # 5초 주기 폴링

def start_monitoring():
    threading.Thread(target=bluetooth_monitor, daemon=True).start()
```

**기술 분석:**
- `bluetooth.lookup_name()`: Bluetooth Classic 프로토콜로 지정 MAC의 기기명을 조회
  - 연결되어 있으면 `"Galaxy S21"` 같은 문자열 반환
  - 범위 밖이면 `None` 반환
- **5초 폴링 주기**: BLE가 아닌 Classic 블루투스이므로 실시간 이벤트가 없어 폴링 방식 사용
- **데몬 스레드**: 메인 프로세스 종료 시 자동으로 같이 종료
- **한계**: 블루투스 범위는 약 10m → 집 구조에 따라 오감지 가능

---

### 4.6 `main.py` — 핵심 엔진 (280줄)

#### 4.6.1 초기화 시퀀스

```python
model = YOLO('yolov8n-pose.pt')  # YOLOv8 Nano Pose 모델 로드
vs = VideoStream(src=0).start()   # 카메라 비동기 스트림 시작
start_monitoring()                 # 블루투스 감시 스레드 시작
app = Flask(__name__)
```

**YOLOv8n-pose.pt 분석:**
- `n` = Nano (가장 경량 버전) → Raspberry Pi에서 실행 가능
- `-pose` = 17개 신체 키포인트 검출 특화 모델
- `device='cpu'`: GPU 없는 RPi에서 CPU 추론

#### 4.6.2 `generate_frames()` — 실시간 영상 파이프라인

이 함수가 프로젝트의 심장이다. **Python Generator** 패턴으로 구현된 MJPEG 스트리머다.

```
[카메라 프레임 읽기]
        ↓
[FRAME_SKIP 체크] ← 연산 주기 제어
        ↓
[YOLO 인퍼런스]
    classes=[0] (사람만 감지)
    conf=0.5 (50% 신뢰도 이상)
    imgsz=448 (홈) / 192 (보안) ← 품질/속도 트레이드오프
        ↓
[분기: is_owner_home?]
  ├── True → [홈 모드 파이프라인]
  └── False → [보안 모드 파이프라인]
        ↓
[OSD 오버레이] ← 타임스탬프, 상태 텍스트
        ↓
[JPEG 인코딩] → [HTTP multipart/x-mixed-replace 스트림]
```

#### 4.6.3 홈 모드: AI 자세 기반 조명 제어

**17개 키포인트 인덱스 (COCO 규격):**
```
0:코 1:왼눈 2:오른눈 3:왼귀 4:오른귀
5:왼어깨 6:오른어깨 7:왼팔꿈치 8:오른팔꿈치
9:왼손목 10:오른손목 11:왼엉덩이 12:오른엉덩이
13:왼무릎 14:오른무릎 15:왼발목 16:오른발목
```

**자세 판별 알고리즘 (`control_mode == 1`):**

```
confidence[5] > 0.5 AND confidence[11] > 0.5 (어깨 + 엉덩이 가시)
        ↓
torso_height = |shoulder_mid_y - hip_mid_y|   (체간 높이)
shoulder_width = |ls[0] - rs[0]|               (어깨 너비)

if shoulder_width > torso_height * 0.8:
    → "Lying" (누움): 조명 30 (수면 모드)
else:
    knee_mid_y vs hip_mid_y 비교
    if |hip_y - knee_y| > torso_height * 0.6:
        → "Standing" (서있음): 조명 255 (최대)
    else:
        → "Sitting" (앉음): 조명 128 (중간)
```

> **핵심 원리**: 누운 자세 감지는 어깨 가로 거리 > 세로 체간 높이 비교  
> 선/앉음 구분은 허리-무릎 수직 거리 > 체간 높이의 60%

**투표 시스템**: 여러 사람이 있을 때 `votes` dict로 다수결 적용

**제스처 제어 알고리즘 (`control_mode == 2`):**
- 가장 큰 사람(area 기준, 정렬된 첫 번째 인덱스)만 제어 권한
- 손목-어깨 Y 좌표 비교:
  ```
  오른손목 < 오른어깨  AND  왼손목 > 왼어깨  → UP (+10)  밝기 증가
  왼손목 < 왼어깨     AND  오른손목 > 오른어깨 → DOWN (-10) 밝기 감소
  양손목 모두 < 어깨                           → MAX (255)  최대 밝기
  ```

#### 4.6.4 보안 모드: 침입자 감지 + 자동 녹화

```
침입자 감지 → state.last_intruder_detect_time = now
                       ↓
should_record = (now - last_detect_time < RECORD_COOLDOWN=5초)
                       ↓
        True: VideoWriter 생성/지속 → 프레임 write
              Sense HAT: 빨간색 경보 LED
              1초 주기로 깜빡이는 REC 표시
        False: VideoWriter.release() → 파일 저장 완료
               Sense HAT: 소등
```

**녹화 파일명 형식**: `intruder_YYYYMMDD_HHMMSS.mp4`  
**코덱**: `mp4v` (MPEG-4), 20fps, 640×480

---

## 5. Flask 웹 서버 API 설계

| 라우트 | 메서드 | 설명 |
|-------|--------|------|
| `/` | GET | 메인 대시보드 (`index.html` 렌더링) |
| `/video_feed` | GET | MJPEG 스트림 (multipart Content-Type) |
| `/update_settings` | POST | 제어 모드/밝기 설정 업데이트 (비동기) |
| `/recordings` | GET | 녹화 파일 목록 페이지 |
| `/download/<filename>` | GET | 녹화 파일 다운로드 |

**`/update_settings` 동작 방식:**
- 브라우저에서 라디오/슬라이더 조작 시 `updateSettings()` JS 함수 즉시 호출
- `FormData` → `fetch('/update_settings', POST)` → `global_state` 업데이트
- 페이지 새로고침 없이 실시간 반영 (AJAX 패턴)

---

## 6. 프론트엔드 설계

### 6.1 모바일 PWA 최적화

```json
// manifest.json
{
  "display": "standalone",      // 브라우저 UI 숨김 → 앱처럼 보임
  "orientation": "portrait",    // 세로 고정
  "background_color": "#121212" // 다크 배경
}
```

- `user-select: none` → 텍스트 드래그 방지 (앱 느낌)
- `maximum-scale=1, user-scalable=no` → 핀치줌 방지

### 6.2 레이아웃 구조 (`base.html`)

```
┌─────────────────────────────┐
│  🎥 AI Home Cam  [상단 NavBar] │  ← sticky-top
├─────────────────────────────┤
│                             │
│    {% block content %}       │  ← 페이지별 콘텐츠
│                             │
│                             │
├─────────────────────────────┤
│  🏠 홈  |  ▶ 녹화 |  🔄 새로고침 │  ← 하단 탭바 (fixed)
└─────────────────────────────┘
```

### 6.3 홈 모드 제어 UI (`index.html`)

```
[MJPEG 스트림 이미지]
[HOME / SECURITY 배지]
[블루투스 상태 | 밝기%]
──────────────────────────
[자세 | 제스처 | 수동] ← 라디오 버튼 그룹
[전원 스위치] ← 토글
[밝기 슬라이더] ← range 0~255
```

보안 모드일 때는 제어판 대신 빨간 경보 배너 표시:
```html
{% if is_home %}
  <!-- 제어 패널 -->
{% else %}
  <!-- 경보 배너 -->
{% endif %}
```

---

## 7. 데이터 흐름 다이어그램

```
[Raspberry Pi]
    │
    ├── [카메라 스레드] ──────────→ VideoStream.frame (메모리)
    │                                        │
    ├── [블루투스 스레드] → state.is_owner_home
    │                                        │
    └── [Flask HTTP 서버]                   │
              │                              │
              ├── /video_feed → generate_frames() ←──────┘
              │        │
              │        ├── vs.read() (최신 프레임)
              │        ├── YOLO 추론()
              │        ├── 자세/제스처/보안 분기
              │        ├── sense.clear(brightness) → [Sense HAT LED]
              │        ├── VideoWriter.write() → [recordings/*.mp4]
              │        └── JPEG → HTTP stream → [브라우저]
              │
              ├── / → index.html (상태 렌더링)
              ├── /update_settings → state.control_mode 갱신
              ├── /recordings → 파일 목록
              └── /download/<f> → MP4 파일 전송
```

---

## 8. 설계 강점 분석

| 강점 | 설명 |
|------|------|
| **관심사 분리 (SoC)** | config / state / hardware / camera / monitor 모듈로 역할 명확히 분리 |
| **Threaded Camera** | I/O 블로킹 제거로 실시간 스트림 성능 향상 |
| **Graceful Degradation** | MockSense로 하드웨어 없이도 개발/테스트 가능 |
| **FRAME_SKIP 최적화** | 모드별 다른 추론 주기로 Raspberry Pi CPU 부하 균형 |
| **모드별 추론 크기** | 홈=448px(정확도), 보안=192px(속도) — 상황에 맞는 트레이드오프 |
| **PWA 지원** | 스마트폰 홈 화면에 앱으로 추가 가능 |

---

## 9. 개선 가능 포인트

| 항목 | 현황 | 개선안 |
|------|------|--------|
| **Race Condition** | `global_state` 접근에 Lock 없음 | `threading.Lock()` 또는 `queue.Queue` 사용 |
| **초음파거리** | 화면에만 표시, 서버 알림 없음 | Pushover/Telegram API 연동 |
| **녹화 용량 관리** | 무제한 축적 | 오래된 파일 자동 삭제 (용량 임계치 기반) |
| **웹 보안** | 인증 없음 → 누구나 `/recordings` 접근 가능 | Flask-Login 또는 HTTP Basic Auth |
| **키포인트 신뢰도** | 고정 임계값 0.5 | 동적 임계값 or 여러 프레임 평균 |
| **V4L2 하드코딩** | Windows/Mac 개발 시 오류 | `cv2.CAP_ANY` 폴백 추가 |
| **블루투스 지연** | 5초 폴링 → 최대 8초 지연 | BLE(Bluetooth Low Energy) 전환 검토 |

---

## 10. 실행 환경 요약

```bash
# 필요 패키지
pip install flask opencv-python ultralytics PyBluez sense-hat

# 실행
python main.py
# → http://0.0.0.0:5000 에서 서비스

# 접속
브라우저: http://<RaspberryPi_IP>:5000
```

**모델 파일**: `yolov8n-pose.pt` — 실행 디렉터리에 위치해야 함 (Ultralytics가 자동 다운로드 지원)
