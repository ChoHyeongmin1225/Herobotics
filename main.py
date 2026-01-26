import time
import sys
from hardware.dxl_driver import DxlDriver
from core.llm_engine import LLMEngine

def main():
    print("=============================================")
    print("🤖 Herobot Silent Mode (Motion Only)")
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
                        joint = motion.get('joint')
                        
                        # ★ [수정 1] 관절은 'pos', 바퀴는 'val' 값을 가져오도록 처리
                        target_value = motion.get('pos')
                        if target_value is None:
                            target_value = motion.get('val')
                        
                        if joint and target_value is not None:
                            print(f"   └─ [{i+1}] {joint} -> {target_value}")
                            driver.move_joint(joint, int(target_value))
                            
                            # ★ [수정 2] 바퀴가 연속으로 올 때는 딜레이를 줄여서(거의 0) 동시성 확보
                            if "wheel" in joint:
                                time.sleep(0.005) # 5ms (거의 동시에 실행)
                            else:
                                time.sleep(0.05)  # 관절은 기존대로 50ms
                    
                    # 동작 완료 후 안정화 대기
                    time.sleep(0.5)
                    print("   └─ (완료)")
                else:
                    print("⚡ [Idle] 움직임 없음 (판단: 가만히 있기로 결정)")
                    # 대화 내용(text)이 있으면 출력해주는 것이 좋음
                    if "text" in action_plan:
                        print(f"   🗣️  [Say]: {action_plan['text']}")
            else:
                print("⚠️ [Error] 행동 생성 실패")

        except KeyboardInterrupt:
            print("\n🛑 사용자 중단 요청")
            break
        except Exception as e:
            print(f"❌ 오류: {e}")
            # 에러 상세 내용을 보기 위해 주석 해제 가능
            # import traceback; traceback.print_exc()

    driver.close()

if __name__ == "__main__":
    main()