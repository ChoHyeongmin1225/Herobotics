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
            # (참고: LLM은 내부적으로는 'text'를 생성하지만, 여기선 출력하지 않고 무시합니다)
            action_plan = brain.generate_response(user_input)
            
            if action_plan:
                # (3) 움직이기 (말 없이 행동만 수행)
                motions = action_plan.get('motions', [])
                
                if motions:
                    print(f"⚡ [Action] {len(motions)}개의 동작 실행 중...")
                    
                    for i, motion in enumerate(motions):
                        joint = motion.get('joint')
                        pos = motion.get('pos')
                        
                        if joint and pos:
                            # 디버깅을 위해 어떤 모터가 움직이는지만 표시
                            print(f"   └─ [{i+1}] {joint} -> {pos}")
                            driver.move_joint(joint, int(pos))
                            
                            # 동작 사이 간격 (필요에 따라 조절)
                            time.sleep(0.05)
                    
                    # 동작 완료 후 안정화 대기
                    time.sleep(0.5)
                    print("   └─ (완료)")
                else:
                    print("⚡ [Idle] 움직임 없음 (판단: 가만히 있기로 결정)")
            else:
                print("⚠️ [Error] 행동 생성 실패")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ 오류: {e}")

    driver.close()

if __name__ == "__main__":
    main()