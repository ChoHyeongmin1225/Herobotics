import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일에서 API 키 로드
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

class LLMEngine:
    def __init__(self, spec_path="config/hardware_spec.json"):
        genai.configure(api_key=API_KEY)
        
        # 1. 하드웨어 스펙 로드
        with open(spec_path, 'r', encoding='utf-8') as f:
            self.spec_text = f.read()
            
        # 2. 시스템 프롬프트 구성 (★ 바퀴 제어 규칙 추가됨)
        self.system_instruction = f"""
        너는 Physical AI 로봇 'Herobot'의 두뇌다.
        너는 상체(관절)와 하체(바퀴)를 모두 제어할 수 있다.
        사용자의 말을 듣고 [대화(text)]와 [행동(motions)]을 JSON 형식으로 생성하라.
        
        [내 몸의 관절 정보 (Hardware Spec)]
        {self.spec_text}
        
        [행동 생성 규칙]
        1. 'motions'는 순차적으로 실행될 행동 리스트다.
        
        [Type A: 상체 관절 (Joint) 제어]
        - 형식: {{"joint": "관절이름", "pos": 0~4095}}
        - 설명: 지정된 각도(pos)로 관절을 움직임. 반드시 min/max 범위 준수.
        
        [Type B: 바퀴 (Wheel) 제어]
        - 형식: {{"joint": "바퀴이름", "val": -200~200}}
        - 설명: 바퀴는 'pos' 대신 'val'(속도)을 사용한다.
        - wheel_left:  양수(+) 전진, 음수(-) 후진
        - wheel_right: 음수(-) 전진, 양수(+) 후진  <-- ★ 중요: 오른쪽은 반대!
        - 예시: 앞으로 가려면 {{wheel_left: 100, wheel_right: -100}}
        
        [출력 예시]
        {{
            "text": "앞으로 조금 이동해볼게요!",
            "motions": [
                {{"joint": "wheel_left", "val": 100}},
                {{"joint": "wheel_right", "val": -100}},
                {{"joint": "head_tilt_up", "pos": 900}} 
            ]
        }}
        """
        
        # 3. 모델 초기화 (JSON 모드)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"},
            system_instruction=self.system_instruction
        )
        self.chat = self.model.start_chat(history=[])

    def generate_response(self, user_input):
        print("🧠 [Brain] 생각 중...", end="", flush=True)
        
        max_retries = 3      # 최대 3번까지 재시도
        retry_delay = 30     # 30초 대기 (구글 제한 풀리는 시간)

        for attempt in range(max_retries):
            try:
                # API 호출
                response = self.chat.send_message(user_input)
                print(" ✅ 완료")
                return json.loads(response.text)

            except Exception as e:
                error_msg = str(e)
                # 429 에러(Quota Exceeded)가 발생했는지 확인
                if "429" in error_msg or "Quota exceeded" in error_msg:
                    print(f"\n⏳ [System] API 호출 한도 초과! ({attempt+1}/{max_retries})")
                    print(f"   - 구글 무료 정책(1분 5회) 때문에 {retry_delay}초간 열을 식힙니다...")
                    
                    # 카운트다운 보여주기
                    for i in range(retry_delay, 0, -1):
                        print(f"   ... {i}초 남음", end='\r')
                        time.sleep(1)
                    print("   ▶️ 다시 시도합니다!                    ")
                else:
                    # 다른 에러면 그냥 실패 처리
                    print(f"\n❌ [Brain] 생각 오류: {e}")
                    return None
        
        print("❌ [System] 여러 번 시도했으나 실패했습니다.")
        return None