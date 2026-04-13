<div align="center">

# 🏠 Smart AI Home Cam

**AI-Powered Smart Home Security & Lighting Control System**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?style=for-the-badge)](https://ultralytics.com)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-4B-A22846?style=for-the-badge&logo=raspberry-pi&logoColor=white)](https://raspberrypi.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

*임베디드 시스템 및 실습 — 팀 프로젝트 (2024 2학기)*

</div>

---

## 📖 개요 (Overview)

**Smart AI Home Cam**은 Raspberry Pi 위에서 동작하는 AI 기반 스마트 홈 통합 시스템입니다.  
블루투스를 통해 집주인의 스마트폰 존재 여부를 감지하여 **두 가지 모드**로 자동 전환됩니다.

| 모드 | 조건 | 기능 |
|:----:|:----:|------|
| 🏠 **홈 모드** | 집주인 블루투스 신호 감지 | YOLOv8 자세 분석 → Sense HAT 조명 자동 제어 |
| 🚨 **보안 모드** | 블루투스 신호 없음 | 침입자 감지 → 자동 영상 녹화 + 경보 LED |

웹 인터페이스는 **PWA(Progressive Web App)** 형태로 제공되어 스마트폰 홈 화면에서 앱처럼 사용할 수 있습니다.

---

## ✨ 주요 기능 (Key Features)

### 🤖 AI 자세 인식 기반 조명 제어
- **YOLOv8n-pose** 모델로 17개 신체 키포인트 실시간 추출
- 자세 → 조명 밝기 자동 매핑:
  - 🧍 **서있음(Standing)** → 조명 최대 (255)
  - 🪑 **앉음(Sitting)** → 조명 중간 (128, 집중 모드)
  - 🛌 **누움(Lying)** → 조명 최소 (30, 수면 모드)
- 여러 명 감지 시 **다수결(Voting)** 방식으로 최종 자세 결정

### 🖐️ 손 제스처 조명 제어
- 카메라 앵글 내 가장 가까운 사용자를 CMD USER로 지정
- 손목-어깨 Y좌표 비교를 통한 제스처 인식:
  - 오른손 위 + 왼손 아래 → 밝기 **+10**
  - 왼손 위 + 오른손 아래 → 밝기 **-10**
  - 양손 모두 위 → 밝기 **최대(255)**

### 🔒 보안 모드 자동 녹화
- 집주인 부재 시 자동 보안 모드 전환
- 침입자 감지 즉시 `mp4v` 코덱으로 녹화 시작
- 마지막 감지 후 `RECORD_COOLDOWN`초(기본 5초) 동안 녹화 유지
- Sense HAT LED 빨간색 경보
- 웹 UI에서 녹화 파일 목록 조회 및 다운로드

### 📱 모바일 최적화 웹 UI
- Bootstrap 5.3 기반 반응형 다크 테마
- PWA manifest — 홈 화면 추가로 앱처럼 실행
- AJAX 기반 실시간 설정 반영 (페이지 새로고침 불필요)
- MJPEG 스트림으로 실시간 카메라 영상 표시

---

## 🏗️ 시스템 아키텍처 (Architecture)

<img height="600" alt="Image" src="https://github.com/user-attachments/assets/1d4f6d20-6508-47cc-8e14-2eaaebbc1de1" />

---

## 🛠️ 기술 스택 (Tech Stack)

| 분류 | 기술 | 버전 | 역할 |
|------|------|------|------|
| **언어** | Python | 3.9+ | 메인 언어 |
| **웹 서버** | Flask | 2.3+ | HTTP 서버, Jinja2 템플릿 |
| **AI** | Ultralytics YOLOv8 | 8.0+ | 인체 감지 + 포즈 키포인트 추출 |
| **영상 처리** | OpenCV | 4.8+ | 카메라 캡처, 프레임 처리, 녹화 |
| **블루투스** | PyBluez | 0.23+ | Classic Bluetooth 기기명 조회 |
| **하드웨어** | sense-hat | 2.4+ | Sense HAT LED 매트릭스 제어 |

---

## 🔧 하드웨어 요구사항 (Hardware)

| 부품 | 사양 | 비고 |
|------|------|------|
| **메인 보드** | Raspberry Pi 4B (권장) | 2GB RAM 이상 |
| **카메라** | USB 웹캠 or CSI 카메라 모듈 | 640×480 / MJPG 지원 |
| **조명 액추에이터** | Raspberry Pi Sense HAT | LED 8×8 매트릭스 |
| **재실 감지** | 집주인 스마트폰 | Bluetooth Classic 지원 |

---

## 📱 사용 방법 (Usage)

### 홈 화면 앱으로 추가 (PWA)

1. 스마트폰 브라우저에서 `http://<Pi_IP>:5000` 접속
2. 브라우저 메뉴 → **"홈 화면에 추가"**
3. 앱 아이콘으로 네이티브 앱처럼 실행

### 제어 모드 설명

| 모드 | 설명 |
|:----:|------|
| **자세** | AI가 자동으로 자세를 분석하여 조명을 조절합니다 |
| **제스처** | 손 동작으로 밝기를 직접 제어합니다 |
| **수동** | 슬라이더와 전원 스위치로 직접 제어합니다 |

### 녹화 파일 관리

- 상단/하단 탭바의 **"녹화 목록"** 탭에서 조회
- 각 파일의 다운로드 버튼(⬇)으로 MP4 파일을 로컬에 저장

---

## 📁 프로젝트 구조 (Project Structure)

```
smart_home/
├── run.py                  # 📌 애플리케이션 진입점
├── requirements.txt        # Python 의존성 목록
├── .gitignore
├── README.md
│
├── recordings/             # 침입자 녹화 파일 저장 (Git 추적 제외)
│   └── .gitkeep
│
└── app/                    # Flask 애플리케이션 패키지
    ├── __init__.py         # 앱 팩토리 & 하드웨어 초기화
    │
    ├── config.py           # ⚙️ 전역 설정 상수
    ├── state.py            # 🔄 멀티스레드 공유 상태
    │
    ├── camera.py           # 📷 비동기 카메라 스트림 (Threaded)
    ├── hardware.py         # 💡 Sense HAT 추상화
    ├── monitor.py          # 📡 블루투스 재실 감지 스레드
    │
    ├── inference.py        # 🤖 YOLOv8 AI 추론 엔진
    │                       #    ├── generate_frames()  MJPEG 스트리머
    │                       #    ├── _classify_posture()  자세 분류
    │                       #    └── _apply_gesture_control()  제스처 인식
    │
    ├── routes.py           # 🌐 Flask Blueprint (HTTP 라우트)
    │
    ├── static/
    │   └── manifest.json   # PWA 매니페스트
    │
    └── templates/
        ├── base.html       # 공통 레이아웃 (NavBar + 하단 탭바)
        ├── index.html      # 메인 대시보드
        └── recordings.html # 녹화 파일 목록
```

---

## 🌐 API 엔드포인트 (API Endpoints)

| Method | Endpoint | 설명 |
|:------:|----------|------|
| `GET` | `/` | 메인 대시보드 |
| `GET` | `/video_feed` | MJPEG 실시간 카메라 스트림 |
| `POST` | `/update_settings` | 제어 모드/밝기 설정 업데이트 (AJAX) |
| `GET` | `/recordings` | 녹화 파일 목록 페이지 |
| `GET` | `/download/<filename>` | 녹화 파일 다운로드 |

### `/update_settings` 파라미터

| 파라미터 | 타입 | 값 | 설명 |
|---------|------|-----|------|
| `control_mode` | int | `1`, `2`, `3` | 자동/제스처/수동 |
| `manual_val` | int | `0`~`255` | 수동 밝기 값 |
| `manual_on` | flag | 존재/부재 | 수동 모드 전원 |

---

## 🔬 핵심 알고리즘 (Core Algorithms)

### 자세 분류 (Posture Classification)

```
COCO Keypoint 인덱스:
  [5] 왼어깨  [6] 오른어깨
  [9] 왼손목  [10] 오른손목
  [11] 왼엉덩이  [12] 오른엉덩이
  [13] 왼무릎  [14] 오른무릎

torso_height = |어깨 중간 Y - 엉덩이 중간 Y|
shoulder_width = |왼어깨 X - 오른어깨 X|

if shoulder_width > torso_height × 0.8  → Lying  (수평 방향 감지)
elif |엉덩이 Y - 무릎 Y| > torso_height × 0.6  → Standing
else  → Sitting
```

### 블루투스 재실 감지

```
5초 주기 폴링:
  bluetooth.lookup_name(MAC, timeout=3)
  → 기기명 반환: is_owner_home = True   (홈 모드)
  → None 반환:   is_owner_home = False  (보안 모드)
```

---

## 👥 팀원 (Contributors)

> *임베디드 시스템 및 실습 — 팀 프로젝트*
