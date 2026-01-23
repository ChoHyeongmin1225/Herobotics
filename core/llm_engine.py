import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일에서 API 키 로드
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

class LLMEngine:
    def __init__(self, spec_path="config/hardware_spec.json"):
        genai.configure(api_key=API_KEY)
        
        # 1. 하드웨어 스펙 로드 (프롬프트 주입용)
        with open(spec_path, 'r', encoding='utf-8') as f:
            self.spec_text = f.read()
            
        # 2. 시스템 프롬프트 구성
        self.system_instruction = f"""
        너는 Physical AI 로봇 'Herobot'의 두뇌다.
        사용자의 말을 듣고 [대화(text)]와 [행동(motions)]을 JSON 형식으로 생성하라.
        
        [내 몸의 관절 정보 (Hardware Spec)]
        {self.spec_text}
        
        [규칙]
        1. 'motions'는 순차적으로 실행될 행동 리스트다.
        2. 각 행동은 {{"joint": "motor_name", "pos": 0~4095}} 형태여야 한다.
        3. 'pos' 값은 반드시 위 스펙의 min/max 범위 내여야 한다.
        4. 감정을 풍부하게 표현하기 위해 여러 모터를 동시에 사용하라.
        
        [출력 예시]
        {{
            "text": "반가워요! 저는 히어로봇입니다.",
            "motions": [
                {{"joint": "head_tilt_up", "pos": 900}},  // 고개 들기
                {{"joint": "r_shoulder_roll", "pos": 2200}} // 팔 벌리기
            ]
        }}
        """
        
        # 3. 모델 초기화 (JSON 모드)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config={"response_mime_type": "application/json"},
            system_instruction=self.system_instruction
        )
        self.chat = self.model.start_chat(history=[])

    def generate_response(self, user_input):
        print("🧠 [Brain] 생각 중...")
        try:
            response = self.chat.send_message(user_input)
            return json.loads(response.text)
        except Exception as e:
            print(f"❌ [Brain] 생각 오류: {e}")
            return None