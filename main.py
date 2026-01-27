import time
import sys
from hardware.dxl_driver import DxlDriver
from core.llm_engine import LLMEngine

def main():
    print("=============================================")
    print("🤖 Herobot Silent Mode (With Delay Support)")
    print("=============================================")
    
    # 1. 모듈 초기화
    try:
        print("1. 하드웨어 연결 중...", end=" ")
        driver = DxlDriver()
        print("✅ 성공")
        
        print("2. 두뇌(LLM) 연결 중...", end=" ")
        brain = LLMEngine()
        print("✅ 성공")
        
        print("\n⚠️  [주의] 로봇이 초기 자세(Neutral)로 움직입니다.")
        print("   - 주변에 물건을 치우고 손을 멀리하세요.")
        input("   - 준비되었으면 [Enter] 키를 누르세요 >> ")
        
        driver.go_to_neutral()
        
    except Exception as e:
        print(f"\n🔥 초기화 실패: {e}")
        return

    print("\n✅ 준비 완료. 명령을 입력하세요.")
    print("---------------------------------------------")
    
    while True:
        try:
            # (1) 입력
            user_input = input("\n👤 명령(CMD): ")
            
            if not user_input: continue
            if user_input.lower() in ['q', 'exit', '종료']:
                break
            
            # (2) 생각하기
            action_plan = brain.generate_response(user_input)
            
            if action_plan:
                # (3) 움직이기
                motions = action_plan.get('motions', [])
                
                if motions:
                    print(f"⚡ [Action] {len(motions)}개의 동작 실행 중...")
                    
                    for i, motion in enumerate(motions):
                        # 1. Delay 처리
                        if 'delay' in motion:
                            delay_time = float(motion['delay'])
                            print(f"   ⏳ [Wait] {delay_time}초 대기...")
                            time.sleep(delay_time)
                            continue

                        # 2. Joint & Value 파싱
                        joint = motion.get('joint')
                        target_value = motion.get('pos') if motion.get('pos') is not None else motion.get('val')
                        
                        # ★ [추가] 속도(Speed) 파싱
                        # JSON에 "speed"가 있으면 가져오고, 없으면 None (기본값)
                        target_speed = motion.get('speed') 
                        
                        if joint and target_value is not None:
                            # 로그에 속도 정보도 표시
                            speed_log = f" (속도: {target_speed})" if target_speed else ""
                            print(f"   └─ [{i+1}] {joint} -> {target_value}{speed_log}")
                            
                            # 드라이버에 속도 전달
                            driver.move_joint(joint, int(target_value), velocity=target_speed)
                            
                            if "wheel" in joint:
                                time.sleep(0.005)
                            else:
                                time.sleep(0.05)
                    
                    print("   └─ (모든 시퀀스 완료)")
                    
                    if "text" in action_plan:
                        print(f"   🗣️  [Say]: {action_plan['text']}")
                else:
                    print("⚡ [Idle] 움직임 없음")
                    if "text" in action_plan:
                        print(f"   🗣️  [Say]: {action_plan['text']}")
            else:
                print("⚠️ [Error] 행동 생성 실패")

        except KeyboardInterrupt:
            print("\n🚨 [EMERGENCY] 비상 정지 발동!")
            driver.move_joint("wheel_left", 0)
            driver.move_joint("wheel_right", 0)
            break
        except Exception as e:
            print(f"❌ 오류: {e}")

    driver.close()

if __name__ == "__main__":
    main()