import time
import sys
# 모듈 임포트
from hardware.dxl_driver import DxlDriver
from core.llm_engine import LLMEngine
from core.voice_interface import VoiceInterface # ★ 추가됨

def main():
    print("=============================================")
    print("🤖 Herobot Voice Mode (Wake-Word System)")
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
        
        # 3. 로봇 자세 초기화
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
            # 여기서 프로그램이 멈춰 있다가, 호출어가 들리면 다음 줄로 넘어갑니다.
            if voice.wait_for_wake_word("히어로봇"):
                
                # (2) 명령 듣기
                # 호출 감지 후 바로 명령을 듣습니다.
                user_input = voice.listen_command()
                
                if not user_input:
                    print("⚡ [Idle] 명령을 듣지 못했습니다. 다시 불러주세요.")
                    continue
                    
                if user_input.strip() in ['종료', '꺼줘', '잘자']:
                    print("👋 시스템을 종료합니다.")
                    break
                
                # (3) 생각하기 (Brain)
                action_plan = brain.generate_response(user_input)
                
                if action_plan:
                    # (4) 움직이기 (Driver)
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
                        
                        # 로봇의 대답 출력 (나중에 TTS로 연결 가능)
                        if "text" in action_plan:
                            print(f"   🗣️  [Say]: {action_plan['text']}")
                
                # (5) 쿨다운 (API 보호 및 대화 종료 느낌)
                print("💤 대기 모드로 전환합니다...")
            else:
                print("👋 시스템을 종료합니다.")
                break

        except KeyboardInterrupt:
            print("\n🚨 [비상 정지]")
            driver.move_joint("wheel_left", 0)
            driver.move_joint("wheel_right", 0)
            break
        except Exception as e:
            print(f"❌ 오류: {e}")

    driver.close()

if __name__ == "__main__":
    main()