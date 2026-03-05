import time
import sys
import os
from dotenv import load_dotenv
from contextlib import contextmanager

# 모듈 임포트
from hardware.dxl_driver import DxlDriver
from core.llm_engine import LLMEngine
from core.voice_interface import VoiceInterface
from core.vision_brain import VisionBrain 

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

@contextmanager
def suppress_alsa_warnings():
    fd = sys.stderr.fileno()
    old_stderr = os.dup(fd)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, fd)
    try:
        yield
    finally:
        os.dup2(old_stderr, fd)
        os.close(old_stderr)
        os.close(devnull)

def main():
    print("=============================================")
    print("🤖 Herobot HRI Mode (RGB Vision Only)")
    print("=============================================")
    
    try:
        print("1. 하드웨어 연결 중...", end=" ")
        driver = DxlDriver()
        print("✅ 성공")
        
        print("2. 두뇌(LLM) 연결 중...", end=" ")
        brain = LLMEngine()
        print("✅ 성공")

        print("3. 청각(Voice) 연결 중...", end=" ")
        with suppress_alsa_warnings():
            voice = VoiceInterface()
        print("✅ 성공")
        
        print("4. 시각(Vision) 연결 중...", end=" ")
        vision = VisionBrain(api_key=GEMINI_API_KEY)
        print("✅ 성공")
        
        print("\n⚠️  [주의] 로봇이 초기 자세로 움직입니다.")
        driver.go_to_neutral()
        
    except Exception as e:
        print(f"\n🔥 초기화 실패: {e}")
        return

    print("\n✅ 준비 완료. 언제든지 '히어로봇'이라고 불러주세요.")
    print("---------------------------------------------")
    
    while True:
        try:
            with suppress_alsa_warnings():
                is_awake = voice.wait_for_wake_word("히어로봇")
                
            if is_awake:
                with suppress_alsa_warnings():
                    user_input = voice.listen_command()
                
                if not user_input:
                    print("⚡ [Idle] 명령을 듣지 못했습니다. 다시 불러주세요.")
                    continue
                    
                if any(w in user_input for w in ['종료', '꺼줘', '잘자']):
                    print("👋 시스템을 종료합니다.")
                    break
                
                # (일반 대화 및 행동 제어만 남김)
                action_plan = brain.generate_response(user_input)
                
                if action_plan:
                    motions = action_plan.get('motions', [])
                    
                    if motions:
                        print(f"⚡ [Action] {len(motions)}개의 시퀀스 실행")
                        
                        for i, motion in enumerate(motions):
                            if 'delay' in motion:
                                time.sleep(float(motion['delay']))
                                continue

                            joint = motion.get('joint')
                            val = motion.get('pos') if motion.get('pos') is not None else motion.get('val')
                            speed = motion.get('speed')

                            if joint and val is not None:
                                driver.move_joint(joint, int(val), velocity=speed)
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

    if vision: vision.close()
    if driver: driver.close()

if __name__ == "__main__":
    main()