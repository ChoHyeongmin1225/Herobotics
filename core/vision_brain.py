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
        
        # 카메라와 실제 그리퍼/중심 간의 미세 오차 보정값 (필요 시 수정)
        self.OFFSET_X = 0 
        self.OFFSET_Y = 0
        
        # 리얼센스 설정
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        # 640x480 해상도, 30프레임 설정
        self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        
        try:
            # 카메라 시작 (타임아웃 방지 로직 포함)
            self.profile = self.pipeline.start(self.config)
            
            # 깊이 센서 스케일 값 가져오기 (거리 정밀 계산용)
            depth_sensor = self.profile.get_device().first_depth_sensor()
            self.depth_scale = depth_sensor.get_depth_scale()
            
            print("✅ [Vision] RealSense 연결 성공! 모니터링 창을 띄웁니다.")
        except Exception as e:
            print(f"❌ [Vision] 카메라 연결 실패: {e}")
            self.pipeline = None

    def capture_and_detect(self, target_name):
        """
        화면을 캡처하고, Gemini에게 target_name의 위치를 물어봅니다.
        동시에 'HeroBot Monitor' 창에 보는 화면을 띄웁니다.
        """
        if not self.pipeline: 
            print("❌ 카메라 파이프라인 없음")
            return None

        try:
            # 1. 프레임 획득 (최대 3초 대기, 응답 없으면 패스)
            frames = self.pipeline.wait_for_frames(timeout_ms=3000)
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            
            if not depth_frame or not color_frame: 
                return None

            # 2. 이미지 변환 (Numpy 배열화)
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            
            # 깊이 이미지를 눈으로 보기 좋게 컬러맵(Heatmap)으로 변환
            # 가까울수록 붉은색/파란색 등으로 표현됨
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

            # ---------------------------------------------------------
            # ★ [모니터링] 분석 전, 현재 화면을 먼저 보여줌 (사용자 피드백용)
            # ---------------------------------------------------------
            # 왼쪽: 컬러 화면 / 오른쪽: 깊이 화면 (가로로 합치기)
            monitor_img = np.hstack((color_image, depth_colormap))
            
            # 화면에 텍스트 추가 (현재 찾는 물건)
            cv2.putText(monitor_img, f"Searching: {target_name}...", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            cv2.imshow('HeroBot Monitor', monitor_img)
            cv2.waitKey(1) # 화면 갱신을 위해 필수 (1ms 대기)

            h, w, _ = color_image.shape

            # 3. Gemini에게 정밀 분석 요청
            print(f"   🧠 [Vision] '{target_name}' 위치 추론 중...", end="", flush=True)
            
            # OpenCV 이미지를 바이트로 인코딩
            _, img_bytes = cv2.imencode('.jpg', color_image)
            
            # ★ 모델명: 최신 좌표 인식용 모델 (Gemini 2.0 Flash Exp 추천)
            # 만약 에러가 나면 'gemini-1.5-flash'로 변경하세요.
            MODEL_NAME = "gemini-2.0-flash-exp"
            
            # 프롬프트: 좌표(Point)를 요청하는 전문 프롬프트
            prompt = f"""
            Find the '{target_name}' in the image.
            
            [Strict Rules]
            1. You must be highly confident. Do NOT mistake shadows or similar objects.
            2. If you are not sure, return [].
            3. If found, return JSON: [{{"point": [y, x], "label": "{target_name}", "confidence": 0.0-1.0}}]
            4. The point coordinates [y, x] must be normalized between 0 and 1000.
            """
            
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    types.Part.from_bytes(data=img_bytes.tobytes(), mime_type='image/jpeg'),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0, 
                    response_mime_type="application/json"
                )
            )
            
            # 응답 파싱
            text = response.text.strip()
            # 가끔 마크다운 코드블록이 섞여올 때 제거
            if text.startswith("```json"): text = text[7:]
            if text.endswith("```"): text = text[:-3]
            
            results = json.loads(text)
            
            if not results:
                print(" ❌ 없음")
                return None
            
            # 가장 신뢰도 높은 첫 번째 결과만 사용
            target = results[0]
            confidence = target.get('confidence', 0.0) 
            
            # 신뢰도 컷 (70% 미만은 무시)
            if confidence < 0.7:
                print(f" ⚠️ 발견했으나 불확실 ({confidence*100:.0f}%) -> 무시")
                return None

            # 4. 좌표 계산 및 거리 측정
            # Gemini는 [y, x] 순서로 0~1000 정규화 좌표를 줌
            norm_y, norm_x = target['point']
            
            # 실제 픽셀 좌표로 변환
            cam_x = int((norm_x / 1000.0) * w)
            cam_y = int((norm_y / 1000.0) * h)
            
            # 깊이 측정 좌표 보정 (카메라 오차 보정값 적용)
            depth_x = max(0, min(cam_x + self.OFFSET_X, 639))
            depth_y = max(0, min(cam_y + self.OFFSET_Y, 479))
            
            # 거리 측정 (미터 단위)
            dist = depth_frame.get_distance(depth_x, depth_y)
            
            # 거리 예외 처리 (0이면 측정 불가, 2.0m 이상이면 너무 멂)
            if dist == 0 or dist > 2.5:
                 # 0일 경우 주변 픽셀 평균을 내거나, 그냥 에러 처리
                 print(f" ⚠️ 거리 측정 실패 ({dist:.2f}m) -> 재시도 필요")
                 return None

            print(f" ✨ 확정! ({confidence*100:.0f}%, 거리: {dist:.2f}m)")
            
            # 5. [시각화] 찾은 결과를 화면에 그리기
            # (1) 초록색 점 찍기
            cv2.circle(color_image, (cam_x, cam_y), 10, (0, 255, 0), -1)
            # (2) 텍스트 표시
            label_text = f"{target_name} ({dist:.2f}m)"
            cv2.putText(color_image, label_text, (cam_x + 15, cam_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # (3) Depth 화면에도 점 찍어서 위치 확인
            cv2.circle(depth_colormap, (depth_x, depth_y), 10, (0, 0, 255), -1)
            
            # ★ 업데이트된 결과 화면 보여주기
            final_monitor = np.hstack((color_image, depth_colormap))
            cv2.imshow('HeroBot Monitor', final_monitor)
            cv2.waitKey(1)
            
            return {"found": True, "x": cam_x, "y": cam_y, "dist": dist}

        except Exception as e:
            print(f" ⚠️ 비전 분석 중 에러: {e}")
            return None

    def close(self):
        """종료 시 리소스 해제"""
        if self.pipeline:
            self.pipeline.stop()
        cv2.destroyAllWindows()
        print("👁️ [Vision] 카메라 종료됨.")