# 🤖 Herobot: Human-Embodied Robot for Open-ended Tasks

> **A Research Platform for Generative Motion Control using Large Language Models**
> LLM 기반의 생성형 동작 제어 및 Physical AI 연구를 위한 휴머노이드 플랫폼

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Gemini API](https://img.shields.io/badge/AI-Google%20Gemini-orange)](https://deepmind.google/technologies/gemini/)
[![Dynamixel](https://img.shields.io/badge/Hardware-Dynamixel-red)](https://emanual.robotis.com/)

---

## 📖 Project Overview

**Herobot(히어로봇)**은 기존의 규칙 기반(Rule-based) 로봇 제어 방식에서 벗어나, 거대 언어 모델(LLM)이 로봇의 신체적 제약(Morphology)을 이해하고 상황에 맞는 행동을 스스로 생성하는 **Physical AI** 연구 프로젝트입니다.

사전에 정의되지 않은 명령(Zero-shot Instruction)에 대해 로봇이 어떻게 추론하고, 자신의 신체 자유도(DoF)를 활용하여 의도를 표현하는지를 탐구합니다.

### 🎯 Core Goals
1.  **Generative Motion:** "인사해봐"와 같은 실제 세계의 명령을 물리적 모터 제어로 변환.
2.  **Morphological Prompting:** 하드웨어 변경 시 코드 수정 없이 프롬프트(Body Spec) 수정만으로 제어 가능.
3.  **Hybrid Architecture:** 안전성과 창의성을 동시에 확보하는 3단계 제어 방어막 구축.

---

## 🏗 System Architecture

Herobot은 LLM의 환각(Hallucination)을 방지하고 물리적 안전성을 확보하기 위해 **"3-Layer Defense System"**을 채택하고 있습니다.

### Layer 1. Reference-Guided Tuning (매뉴얼 기반 튜닝)
* **작동:** 사용자의 의도가 기존 매뉴얼(예: 인사, 환호)과 유사할 경우, 기본 동작을 가져와 LLM이 상황(감정, 강도)에 맞게 속도와 각도를 미세 조정(Tuning)합니다.
* **효과:** 가장 안정적이고 빠르며, 로봇의 캐릭터성을 유지합니다.

### Layer 2. Primitive Assembly (프리미티브 조립)
* **작동:** 매뉴얼에 없는 새로운 행동(예: 숭배, 좀비)을 요청받을 경우, LLM이 단위 동작 블록(Head_Pan, Arm_Lift 등)을 레고처럼 조립하여 시퀀스를 생성합니다.
* **효과:** 무한한 행동 확장성을 가집니다 (Generative capability).

### Layer 3. Graceful Failure (우아한 거절)
* **작동:** 물리적으로 불가능하거나 위험한 요청(예: 날아라, 팔을 360도 꺾어라)에 대해 시스템 에러 대신, "거절 제스처(어깨 으쓱)"와 함께 거절 의사를 표현합니다.
* **효과:** 로봇의 생명력을 유지하며 안전을 보장합니다.

---

## ⚙️ Hardware Specifications

Herobot은 상호작용 연구를 위해 정밀하게 설계된 **17-DoF High-End Tabletop Humanoid**입니다.

| Part | Motors | Structure (IDs) | Description & Features |
| :--- | :---: | :--- | :--- |
| **Head** | 3 | Pan(2), Tilt-Up(1), Tilt-Down(3) | **Split-Pitch Mechanism.** 상(Up)/하(Down) 움직임 모터가 분리되어 있어, 인간의 미세한 턱 끝 움직임과 시선 처리를 정교하게 모방함. |
| **Waist** | 2 | Yaw(6), Pitch(7) | **Core Expression.** 인사(Pitch)와 거절/회피(Yaw) 등 로봇의 태도(Attitude)를 결정짓는 핵심 부위. |
| **R-Arm** | 6 | Shd(4,8), Arm(9), Elb(10+11), Wri(12) | **Dual-Motor Elbow.** 팔꿈치 관절 하나에 2개의 모터(10, 11)를 동기화하여 사용하여 토크를 강화하고 떨림을 방지함. |
| **L-Arm** | 6 | Shd(5,13), Arm(14), Elb(15+16), Wri(17) | **Symmetric Design.** 오른팔과 완벽한 대칭 구조. 복잡한 핸드 제스처 및 자기 신체 접촉(Self-touch) 가능. |
| **Total** | **17** | **Full Upper Body** | **Physical AI Optimized.** LLM이 생성한 복합적인 감정 표현을 물리적으로 구현하기 위한 고자유도 설계. |

* **Actuators:** ROBOTIS Dynamixel **2XL430-W250-T** Series (Dual Axis Module)
* **Controller:** ROBOTIS **U2D2** (USB Interface)
* **Communication:** Protocol 2.0 (57600 bps)

---

## 📂 Project Structure

모듈화된 설계를 통해 하드웨어와 소프트웨어의 의존성을 분리했습니다.

```bash
Herobot/
├── main.py                     # [Entry Point] 시스템 실행 및 이벤트 루프
├── requirements.txt            # 의존성 패키지 목록
│
├── config/                     # [Identity] 로봇의 자아 및 신체 정의
│   ├── hardware_spec.json      # ★ LLM에게 주입되는 '신체 사용 설명서'
│   ├── safety_limits.json      # 모터 과부하 방지를 위한 물리적 한계값
│   └── system_prompt.txt       # LLM 페르소나 정의
│
├── core/                       # [Brain] 지능 처리 엔진
│   ├── llm_engine.py           # Gemini API 통신 모듈
│   └── action_parser.py        # JSON 응답 파싱 및 유효성 검사
│
├── motion/                     # [Action] 행동 계획 및 생성
│   ├── motion_planner.py       # ★ 3-Layer Defense Logic 구현부
│   ├── primitives.py           # 단위 동작 함수 모음 (Lego Blocks)
│   └── manual_library.json     # 기본 매뉴얼 동작 DB
│
├── hardware/                   # [Body] 하드웨어 추상화 계층 (HAL)
│   └── dxl_driver.py           # Dynamixel SDK 래퍼 및 모션 스무딩
│
└── utils/                      # [Tools]
    └── logger.py               # 데이터 로깅 (연구 분석용)

