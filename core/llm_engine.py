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
            
        # 2. 시스템 프롬프트 구성 (★ Delay 규칙 추가됨)
        self.system_instruction = f"""
        너는 Physical AI 로봇 'Herobot'의 두뇌다.
        너는 상체(관절)와 하체(바퀴)를 모두 제어할 수 있다.
        사용자의 말을 듣고 [대화(text)]와 [행동(motions)]을 JSON 형식으로 생성하라.
        
        [내 몸의 관절 정보 (Hardware Spec)]
        {self.spec_text}
        
        [행동 생성 규칙]
        1. 'motions'는 순차적으로 실행될 행동 리스트다.
        
        [Type A: 상체 관절 (Joint) 제어]
        - 형식: {{"joint": "관절이름", "pos": 0~4095, "speed": 0~200(옵션)}}
        - 설명: 지정된 각도(pos)로 관절을 움직임.
        - "speed" 옵션: 
            * 생략 시 기본 속도(빠름)로 이동.
            * 30~50: 아주 천천히 (우아하게 내릴 때 사용)
            * 100~200: 보통 속도
        
        [Type B: 바퀴 (Wheel) 제어]
        - 형식: {{"joint": "바퀴이름", "val": -200~200}}
        - 설명: 바퀴는 'pos' 대신 'val'(속도)을 사용.
        - wheel_left:  양수(+) 전진, 음수(-) 후진
        - wheel_right: 음수(-) 전진, 양수(+) 후진
        
        [Type C: 대기 (Delay) 제어]
        - 형식: {{"delay": 초(seconds)}}
        - 설명: 동작 사이에 잠시 멈춤(여운)이 필요할 때 사용.
        - 중요: 인사를 하거나 포즈를 취한 뒤에는 반드시 1.0~2.0초 정도 delay를 줘서 사용자가 볼 시간을 줘라.
        
        [출력 예시: 자연스러운 인사]
        {{
            "text": "안녕하세요! (천천히 손을 내립니다)",
            "motions": [
                // 1. 빠르게 손 들기 (speed 생략)
                {{"joint": "r_wrist_pitch", "pos": 2475}}, 
                {{"delay": 0.5}},
                // 2. 손 흔들기
                {{"joint": "r_wrist_pitch", "pos": 2800}},
                {{"joint": "r_wrist_pitch", "pos": 2100}},
                {{"delay": 1.0}},
                // 3. ★ 천천히 팔 내리기 (speed: 40 적용)
                {{"joint": "r_shoulder_pitch", "pos": 1071, "speed": 40}},
                {{"joint": "r_wrist_pitch", "pos": 1464, "speed": 40}}
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
        
        max_retries = 3
        retry_delay = 30

        for attempt in range(max_retries):
            try:
                response = self.chat.send_message(user_input)
                print(" ✅ 완료")
                return json.loads(response.text)

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Quota exceeded" in error_msg:
                    print(f"\n⏳ [System] API 호출 한도 초과! ({attempt+1}/{max_retries})")
                    print(f"   - 구글 무료 정책 때문에 {retry_delay}초간 대기...")
                    for i in range(retry_delay, 0, -1):
                        print(f"   ... {i}초 남음", end='\r')
                        time.sleep(1)
                    print("   ▶️ 다시 시도합니다!                    ")
                else:
                    print(f"\n❌ [Brain] 생각 오류: {e}")
                    return None
        
        print("❌ [System] 실패")
        return None