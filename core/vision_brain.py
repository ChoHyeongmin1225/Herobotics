import cv2
from google import genai

class VisionBrain:
    def __init__(self, api_key):
        print("👁️ [Vision] 일반 웹캠(RGB) 로딩 중...")
        self.client = genai.Client(api_key=api_key)
        
        # 일반 웹캠 연결 (0번 인덱스가 기본 카메라)
        self.cap = cv2.VideoCapture(0)
        
        if not self.cap.isOpened():
            print("❌ [Vision] 카메라를 열 수 없습니다. 연결을 확인하세요.")
        else:
            print("✅ [Vision] 웹캠 연결 성공!")

    def capture_frame(self):
        """
        현재 화면을 캡처하여 반환합니다.
        추후 HRI 상호작용(얼굴/제스처 인식)을 위해 사용될 기본 뼈대입니다.
        """
        if not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if not ret:
            print("❌ [Vision] 프레임을 읽어올 수 없습니다.")
            return None
            
        return frame
        
    def show_monitor(self, frame, text=""):
        """
        모니터링 창을 띄워 현재 시야를 확인합니다.
        """
        display_frame = frame.copy()
        if text:
            cv2.putText(display_frame, text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        cv2.imshow('HeroBot RGB Monitor', display_frame)
        cv2.waitKey(1)

    def close(self):
        """종료 시 리소스 해제"""
        if self.cap and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        print("👁️ [Vision] 카메라 종료됨.")