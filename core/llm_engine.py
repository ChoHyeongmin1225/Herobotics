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
        
        # =================================================================
        # [Mode 2: 자율 탐색 에이전트] (자율 탐색용 프롬프트)
        # =================================================================
        self.search_instruction = """
        너는 '탐색 전문 로봇'의 두뇌다. 
        너의 목표는 사용자가 요청한 물건을 시각 정보(Vision)를 바탕으로 찾는 것이다.
        너는 상황을 판단하여 다음 [행동 명령어] 중 하나를 선택해야 한다.

        [사용 가능한 행동 명령어]
        1. "LOOK_DOWN": 바닥을 확인한다. (마우스, 신발, 떨어진 물건 등)
        2. "LOOK_FRONT": 정면이나 책상 위를 확인한다. (모니터, 컵, 사람 얼굴 등)
        3. "TURN_LEFT": 고개를 왼쪽으로 돌린다.
        4. "TURN_RIGHT": 고개를 오른쪽으로 돌린다.
        5. "STOP": 물건을 찾았거나, 도저히 없어서 포기할 때.

        [응답 형식 (JSON)]
        {
            "thought": "왜 이 행동을 선택했는지 짧은 추론",
            "command": "위 명령어 중 하나",
            "speak": "사용자에게 진행 상황 보고 (짧게)"
        }
        """
        
        # 모델 초기화 (JSON 모드)
        # ★ 캡틴의 명령대로 2.5-flash 모델명 고정
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            generation_config={"response_mime_type": "application/json"}
        )
        
        # 일반 대화용 채팅 세션 시작 (기존 프롬프트 적용)
        self.chat = self.model.start_chat(history=[
            {"role": "user", "parts": [self.system_instruction]},
            {"role": "model", "parts": ["{\"text\": \"네, 알겠습니다. 히어로봇 준비 완료!\"}"]}
        ])

    def decide_next_move(self, target, vision_result, history_text):
        """
        ★ [자율 탐색 모드] 상황을 듣고 다음 행동을 결정하는 함수
        """
        # 탐색 전용 프롬프트 구성
        prompt = f"""
        [탐색 미션: '{target}' 찾기]
        
        1. 현재 상황 (Vision Result): "{vision_result}"
        2. 지금까지 한 행동들 (History): {history_text}
        
        위 정보를 바탕으로, 물건을 찾기 위한 최적의 '다음 행동'을 결정해서 JSON으로 답해줘.
        """
        
        try:
            print("🧠 [Brain/Agent] 다음 행동 판단 중...", end=" ")
            # 시스템 프롬프트를 search_instruction으로 교체하여 추론
            response = self.model.generate_content(
                contents=[self.search_instruction, prompt]
            )
            print("✅ 결정 완료")
            return json.loads(response.text)
            
        except Exception as e:
            print(f"❌ [Brain] 판단 오류: {e}")
            return {"command": "STOP", "speak": "오류가 나서 멈출게요.", "thought": "에러 발생"}

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

    # =================================================================
    # ★ [필수] 사용자의 의도(찾을 물건 + 방향 힌트)를 파악하는 함수
    # =================================================================
    def extract_search_intent(self, user_text):
        """
        사용자 말에서 '찾을 물건(target)'과 '방향 힌트(hint)'를 JSON으로 추출합니다.
        어떤 물건이든(지갑, 차키, 리모컨 등) 영어로 변환하여 타겟으로 설정합니다.
        """
        prompt = f"""
        Analyze the following Korean text: "{user_text}"
        
        Your task is to identify if the user is asking to find any object.
        
        1. "target": Translate the object name into English. (e.g., "물통"->"water bottle", "내 지갑"->"wallet", "파란색 공"->"blue ball").
        2. "hint": Extract directional hints if present. One of ["LOOK_DOWN", "TURN_LEFT", "TURN_RIGHT", "LOOK_FRONT"] based on words like '아래/밑', '왼쪽', '오른쪽'. If no direction is specified, return null.
        
        Return ONLY a JSON object.
        Example: {{"target": "water bottle", "hint": "LOOK_DOWN"}}
        If it's NOT a search command, return {{"target": null, "hint": null}}.
        """
        
        try:
            # 모델 호출 (기존 모델 재사용)
            response = self.model.generate_content(prompt)
            
            # JSON 파싱 (혹시 모를 마크다운 기호 제거)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
            
        except Exception as e:
            print(f"⚠️ [Intent Error] {e}")
            return {"target": None, "hint": None}