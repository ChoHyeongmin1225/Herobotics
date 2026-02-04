import time
import sys
import os
import json
from dotenv import load_dotenv

# 모듈 임포트
from hardware.dxl_driver import DxlDriver
from core.llm_engine import LLMEngine
from core.voice_interface import VoiceInterface
from core.vision_brain import VisionBrain 

# API 키 로드
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# =========================================================
# [Agent Action Map] 자율 탐색 시 사용할 행동 정의
# =========================================================
ACTION_MAP = {
    "LOOK_DOWN":  {"waist_pitch": 300, "head_tilt_down": 650, "head_pan": 2047},
    "LOOK_FRONT": {"waist_pitch": 531, "head_tilt_down": 1027, "head_pan": 2047},
    "TURN_LEFT":  {"head_pan": 2500, "waist_yaw": 3300, "head_tilt_down": 1027}, 
    "TURN_RIGHT": {"head_pan": 1500, "waist_yaw": 2900, "head_tilt_down": 1027},
    "NEUTRAL":    {"head_pan": 2047, "head_tilt_down": 1027, "waist_pitch": 531, "waist_yaw": 3122}
}

# ★ [수정] hint_action=None 추가하여 에러 해결!
def run_agent_search(driver, brain, vision, target_name, hint_action=None):
    """
    [자율 탐색 모드]
    - hint_action이 있으면 1단계에서 AI 판단 없이 즉시 실행 (반응속도 UP)
    """
    print(f"\n🧠 [Agent] '{target_name}' 탐색 시작 (힌트: {hint_action})")
    print("   (AI가 시각 정보를 분석해 스스로 움직입니다)")
    
    history_log = [] 
    
    # 최대 5번까지 시도
    for step in range(1, 6):
        print(f"\n🔄 [Step {step}/5] 관찰 및 판단")
        
        # 1. [Vision] 현재 시야 확인
        scan_result = vision.capture_and_detect(target_name)
        
        vision_status = "타겟을 찾지 못함."
        if scan_result and scan_result['found']:
            vision_status = f"타겟 발견! 거리 {scan_result['dist']:.2f}m"
            print(f"🎉 {vision_status}")
            
            # 찾았을 때 기쁜 멘트 생성
            brain.generate_response(f"내가 {target_name}를 찾았어! 거리는 {scan_result['dist']}미터야.")
            print("🛑 탐색 성공으로 종료합니다.")
            return
        else:
            print("   👀 (두리번) 아직 안 보입니다.")

        # =========================================================
        # 2. [Brain] 다음 행동 결정 (힌트 우선권 로직)
        # =========================================================
        cmd = "STOP"
        thought = ""
        speak = ""

        # ★ 첫 번째 스텝이고, 힌트가 있으면 무조건 실행!
        if step == 1 and hint_action:
            cmd = hint_action
            thought = "사용자의 방향 지시를 최우선으로 수행합니다."
            print(f"   🚀 [Priority] 사용자 지시 즉시 실행: {cmd}")
        else:
            # 힌트가 없거나 2번째부터는 AI가 판단
            decision = brain.decide_next_move(
                target=target_name, 
                vision_result=vision_status,
                history_text=str(history_log)
            )
            cmd = decision.get("command", "STOP")
            thought = decision.get("thought", "")
            speak = decision.get("speak", "")
            
            print(f"   🤔 [AI 생각]: \"{thought}\"")
            print(f"   👉 [AI 결정]: {cmd}")
            if speak: print(f"   🗣️ [Say]: \"{speak}\"")
        
        history_log.append(f"Step {step}: {cmd} 수행함 ({vision_status})")

        # 3. [Body] 행동 실행 (허리 보호 Safe Motion 적용)
        if cmd == "STOP":
            print("🛑 AI가 탐색 중단을 요청했습니다.")
            break
            
        if cmd in ACTION_MAP:
            motors = ACTION_MAP[cmd]
            
            # ★ 허리(Waist)가 포함된 동작인지 확인
            if "waist_pitch" in motors:
                # 1. 허리 먼저 아주 천천히 이동 (velocity=20)
                w_val = motors["waist_pitch"]
                driver.move_joint("waist_pitch", int(w_val), velocity=20)
                
                # 중력 관성을 고려해 허리가 다 내려갈 때까지 대기
                time.sleep(1.5) 
                
                # 2. 나머지 관절 이동 (velocity=30 ~ 40)
                for joint, val in motors.items():
                    if joint == "waist_pitch": continue # 허리는 이미 움직였음
                    driver.move_joint(joint, int(val), velocity=30)
            else:
                # 허리가 없는 동작은 일반 속도
                for joint, val in motors.items():
                    driver.move_joint(joint, int(val), velocity=30)
            
            # 카메라 초점 및 인식 안정화를 위해 2초 대기
            time.sleep(2.0) 
        else:
            print(f"⚠️ 알 수 없는 명령: {cmd}. 원위치로 천천히 갑니다.")
            driver.move_joint("waist_pitch", 531, velocity=20) 
            time.sleep(1.0)
            driver.go_to_neutral()
            time.sleep(1.0)
    
    print("\n🔚 탐색 종료. 원위치로 복귀합니다.")
    driver.move_joint("waist_pitch", 531, velocity=20) # 안전 복귀
    time.sleep(1.0)
    driver.go_to_neutral()


def main():
    print("=============================================")
    print("🤖 Herobot Ultimate Mode (Fix: Hint Error)")
    print("=============================================")
    
    try:
        # 1. 하드웨어 & 두뇌 초기화
        print("1. 하드웨어 연결 중...", end=" ")
        driver = DxlDriver()
        print("✅ 성공")
        
        print("2. 두뇌(LLM) 연결 중...", end=" ")
        brain = LLMEngine()
        print("✅ 성공")

        # 2. 음성 모듈 초기화
        print("3. 청각(Voice) 연결 중...", end=" ")
        voice = VoiceInterface()
        print("✅ 성공")
        
        # 3. 시각 모듈 초기화
        print("4. 시각(Vision) 연결 중...", end=" ")
        vision = VisionBrain(api_key=GEMINI_API_KEY)
        print("✅ 성공")
        
        # 4. 로봇 자세 초기화
        print("\n⚠️  [주의] 로봇이 초기 자세로 움직입니다.")
        driver.go_to_neutral()
        
    except Exception as e:
        print(f"\n🔥 초기화 실패: {e}")
        return

    print("\n✅ 준비 완료. 언제든지 '히어로봇'이라고 불러주세요.")
    print("---------------------------------------------")
    
    while True:
        try:
            # (1) 호출어 대기 ("히어로봇")
            if voice.wait_for_wake_word("히어로봇"):
                
                # (2) 명령 듣기
                user_input = voice.listen_command()
                
                if not user_input:
                    print("⚡ [Idle] 명령을 듣지 못했습니다. 다시 불러주세요.")
                    continue
                    
                if any(w in user_input for w in ['종료', '꺼줘', '잘자']):
                    print("👋 시스템을 종료합니다.")
                    break
                
                # =================================================
                # ★ [MODE 1] 탐색 명령 인터셉트
                # =================================================
                if "찾아" in user_input or "어디" in user_input:
                    # 타겟 추출
                    target = "mouse"
                    if "컵" in user_input: target = "cup"
                    elif "휴대폰" in user_input or "핸드폰" in user_input: target = "phone"
                    elif "사람" in user_input: target = "person"
                    elif "리모컨" in user_input: target = "remote"
                    
                    # 힌트 분석 (아래, 왼쪽, 오른쪽)
                    hint = None
                    if any(w in user_input for w in ["아래", "바닥", "밑", "땅"]):
                        hint = "LOOK_DOWN"
                    elif any(w in user_input for w in ["왼쪽", "좌측"]):
                        hint = "TURN_LEFT"
                    elif any(w in user_input for w in ["오른쪽", "우측"]):
                        hint = "TURN_RIGHT"
                    
                    # Agent 함수 실행 (이제 hint_action을 받을 수 있음!)
                    run_agent_search(driver, brain, vision, target, hint_action=hint)
                    continue 
                # =================================================
                
                # (3) 일반 대화 및 행동
                action_plan = brain.generate_response(user_input)
                
                if action_plan:
                    motions = action_plan.get('motions', [])
                    
                    if motions:
                        print(f"⚡ [Action] {len(motions)}개의 시퀀스 실행")
                        
                        for i, motion in enumerate(motions):
                            # Delay 처리
                            if 'delay' in motion:
                                time.sleep(float(motion['delay']))
                                continue

                            # Joint / Wheel 제어
                            joint = motion.get('joint')
                            val = motion.get('pos') if motion.get('pos') is not None else motion.get('val')
                            speed = motion.get('speed')

                            if joint and val is not None:
                                driver.move_joint(joint, int(val), velocity=speed)
                                
                                # 바퀴/관절 딜레이 구분
                                if "wheel" in joint:
                                    time.sleep(0.005)
                                else:
                                    time.sleep(0.05)
                        
                        print("   └─ (완료)")
                        
                        if "text" in action_plan:
                            print(f"   🗣️  [Say]: {action_plan['text']}")
                
                print("💤 대기 모드로 전환합니다...")

        except KeyboardInterrupt:
            print("\n🚨 [비상 정지]")
            driver.move_joint("wheel_left", 0)
            driver.move_joint("wheel_right", 0)
            break
        except Exception as e:
            print(f"❌ 오류: {e}")

    # 종료 시 자원 해제
    if vision: vision.close()
    if driver: driver.close()

if __name__ == "__main__":
    main()