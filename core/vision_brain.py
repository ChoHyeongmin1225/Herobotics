import cv2
import json
import time
import numpy as np
import pyrealsense2 as rs
from google import genai
from google.genai import types

class VisionBrain:
    def __init__(self, api_key):
        print("👁️ [Vision] Gemini Robotics (Unified Monitor) 로딩 중...")
        self.client = genai.Client(api_key=api_key)
        
        self.OFFSET_X = -31
        self.OFFSET_Y = 11
        
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        
        try:
            self.pipeline.start(self.config)
            print("✅ [Vision] RealSense 연결 성공")
        except Exception as e:
            print(f"❌ [Vision] 카메라 연결 실패: {e}")
            self.pipeline = None

    def capture_and_detect(self, target_name):
        if not self.pipeline: return None

        # 1. 프레임 획득
        frames = self.pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        
        if not depth_frame or not color_frame: return None

        # 2. 이미지 변환
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        
        # Depth 이미지를 컬러맵으로 변환 (보기 좋게)
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

        # ★ [핵심] 두 이미지를 가로로 합치기 (Horizontal Stack)
        # 왼쪽: 컬러 / 오른쪽: 뎁스
        combined_image = np.hstack((color_image, depth_colormap))
        
        # 모니터링 창 띄우기 (분석 전 깨끗한 화면)
        cv2.imshow('HeroBot Monitor', combined_image)
        cv2.waitKey(1)

        h, w, _ = color_image.shape

        # 3. Gemini 정밀 분석 요청
        print(f"   🧠 [Vision] '{target_name}' 정밀 분석 중...", end="", flush=True)
        try:
            _, img_bytes = cv2.imencode('.jpg', color_image)
            
            MODEL_NAME = "gemini-robotics-er-1.5-preview"
            
            # 엄격한 프롬프트 유지
            prompt = f"""
            Find the '{target_name}' in the image.
            
            [Strict Rules]
            1. You must be highly confident. Do NOT mistake paper, shadows, or similar looking objects for the target.
            2. If you are not sure, return [].
            3. If found, return JSON: [{{"point": [y, x], "label": "{target_name}", "confidence": 0.0-1.0}}]
            
            The points are normalized [0-1000].
            """
            
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    types.Part.from_bytes(data=img_bytes.tobytes(), mime_type='image/jpeg'),
                    prompt
                ],
                config=types.GenerateContentConfig(temperature=0.0)
            )
            
            text = response.text.replace("```json", "").replace("```", "").strip()
            results = json.loads(text)
            
            if not results:
                print(" ❌ 없음 (AI 판단)")
                return None
            
            target = results[0]
            confidence = target.get('confidence', 0.8) 
            
            # 신뢰도 컷 (70% 미만 무시)
            if confidence < 0.7:
                print(f" ⚠️ 의심됨 ({confidence*100:.0f}%) -> 무시")
                return None

            # 4. 좌표 계산 및 거리 측정
            norm_y, norm_x = target['point']
            cam_x = int((norm_x / 1000.0) * w)
            cam_y = int((norm_y / 1000.0) * h)
            
            depth_x = max(0, min(cam_x + self.OFFSET_X, 639))
            depth_y = max(0, min(cam_y + self.OFFSET_Y, 479))
            dist = depth_frame.get_distance(depth_x, depth_y)
            
            # 거리 예외 처리
            if dist == 0 or dist > 2.0:
                 print(f" ⚠️ 거리 오류 ({dist:.2f}m) -> 무시")
                 return None

            print(f" ✨ 확정! ({confidence*100:.0f}%, {dist:.2f}m)")
            
            # 5. 결과 그리기 (찾았을 때만)
            # 컬러 이미지에 타겟 표시
            cv2.circle(color_image, (cam_x, cam_y), 10, (0, 255, 0), -1)
            cv2.putText(color_image, f"{target_name} ({confidence*100:.0f}%)", (cam_x + 10, cam_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
            
            # 뎁스 이미지에도 타겟 표시 (위치 확인용)
            cv2.circle(depth_colormap, (cam_x, cam_y), 10, (0, 255, 255), -1)
            
            # ★ 다시 합쳐서 업데이트된 화면 보여주기
            combined_result = np.hstack((color_image, depth_colormap))
            cv2.imshow('HeroBot Monitor', combined_result)
            cv2.waitKey(1)
            
            return {"found": True, "x": cam_x, "y": cam_y, "dist": dist}

        except Exception as e:
            print(f" ⚠️ 분석 에러: {e}")
            return None

    def close(self):
        if self.pipeline: self.pipeline.stop()
        cv2.destroyAllWindows()