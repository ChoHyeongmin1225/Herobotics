import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

# .env 파일에서 API 키 로드
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

class LLMEngine:
    def __init__(self, spec_path="config/hardware_spec.json"):
        # 1. 하드웨어 스펙 로드
        try:
            with open(spec_path, 'r', encoding='utf-8') as f:
                self.spec_text = f.read()
        except FileNotFoundError:
            self.spec_text = "하드웨어 정보를 찾을 수 없음."
            
        # =================================================================
        # [Mode 1: 일반 대화 및 섬세한 행동 제어] (캡틴의 오리지널 프롬프트)
        # =================================================================
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
        
        # 2. 새로운 SDK 클라이언트 초기화
        self.client = genai.Client(api_key=API_KEY)
        
        # 3. 채팅 세션 시작 (새로운 SDK 문법 적용: system_instruction을 config에 직접 탑재)
        # ★ 캡틴의 명령대로 모델명 고정 (만약 2.5-flash에서 에러가 나면 "gemini-2.0-flash"로 변경하세요)
        self.chat = self.client.chats.create(
            model="gemini-3-flash-preview",
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                response_mime_type="application/json"
            )
        )

    def generate_response(self, user_input):
        """
        [일반 대화 모드] 기존 로직 유지 (섬세한 제어 가능)
        """
        print("🧠 [Brain/Chat] 생각 중...", end="", flush=True)
        
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
                    print(f"   - {retry_delay}초간 대기...")
                    time.sleep(retry_delay)
                else:
                    print(f"\n❌ [Brain] 생각 오류: {e}")
                    return None
        
        print("❌ [System] 실패")
        return None