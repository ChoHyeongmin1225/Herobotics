import pyrealsense2 as rs
import numpy as np
import cv2

def moti_vision_start():
    pipeline = rs.pipeline()
    config = rs.config()

    # [최적화 세팅] 출력된 목록을 바탕으로 가장 안전한 조합 선택
    # 1. Depth: 640x480 @ 30fps (거리 측정용 표준)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    
    # 2. RGB: 320x240 @ 30fps (USB 대역폭 절약을 위해 해상도 낮춤)
    config.enable_stream(rs.stream.color, 320, 240, rs.format.bgr8, 30)

    print("🤖 모티(Herobot) 시각 시스템 부팅 중...")
    
    try:
        pipeline.start(config)
        print(">> 부팅 성공! 비전 데이터 스트리밍을 시작합니다.")
        
        # 화면 출력을 위한 윈도우 설정
        cv2.namedWindow('Herobot Vision', cv2.WINDOW_AUTOSIZE)

        while True:
            # 프레임 수신 (타임아웃 3초)
            frames = pipeline.wait_for_frames(timeout_ms=3000)
            
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                continue

            # 데이터를 numpy 배열로 변환
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # [시각화 처리]
            # 1. Depth 이미지를 사람이 볼 수 있게 컬러맵 씌우기
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
            
            # 2. RGB 이미지가 320x240으로 작으므로, Depth(640x480) 크기에 맞춰 2배 확대
            color_image_resized = cv2.resize(color_image, (640, 480))

            # 두 영상을 가로로 이어붙이기
            combined_image = np.hstack((color_image_resized, depth_colormap))

            # 화면 출력
            cv2.imshow('Herobot Vision', combined_image)

            # 화면 중앙의 거리값 측정 (예시: 화면 한가운데 픽셀의 깊이)
            center_dist = depth_frame.get_distance(320, 240)
            print(f"현재 중앙 물체와의 거리: {center_dist:.2f} m", end='\r')

            # ESC 키를 누르면 종료
            if cv2.waitKey(1) & 0xFF == 27:
                break

    except RuntimeError as e:
        print(f"\n[에러 발생] {e}")

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()
        print("\n시각 시스템이 안전하게 종료되었습니다.")

if __name__ == "__main__":
    moti_vision_start()