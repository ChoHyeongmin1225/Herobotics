import json
import time
from dynamixel_sdk import *

class DxlDriver:
    def __init__(self, spec_path="config/hardware_spec.json"):
        # 1. 스펙 파일 로드
        with open(spec_path, 'r', encoding='utf-8') as f:
            self.spec = json.load(f)
        
        self.port_name = self.spec['robot_info']['port']
        self.baudrate = self.spec['robot_info']['default_baudrate']
        self.motors = {m['name']: m for m in self.spec['motors']}
        
        # 2. 다이나믹셀 통신 설정
        self.portHandler = PortHandler(self.port_name)
        self.packetHandler = PacketHandler(2.0)
        
        # 3. 주소값 정의 (X-Series 공통)
        self.ADDR_TORQUE_ENABLE = 64
        self.ADDR_GOAL_POSITION = 116
        self.ADDR_PROFILE_ACCELERATION = 108 # ★ 가속도 주소
        self.ADDR_PROFILE_VELOCITY = 112     # ★ 속도 주소
        
        # 4. 연결 시작
        if not self.portHandler.openPort():
            raise Exception(f"❌ 포트 열기 실패: {self.port_name}")
        if not self.portHandler.setBaudRate(self.baudrate):
            raise Exception(f"❌ 보드레이트 설정 실패: {self.baudrate}")
            
        print(f"✅ [Driver] 하드웨어 연결 성공 ({self.port_name})")
        
        # 5. 초기 설정 (토크 켜고 -> 부드러운 모션 세팅)
        self.enable_torque(True)
        self.set_smooth_motion_profile() # ★ 부드러움 적용

    def enable_torque(self, enable):
        for name, info in self.motors.items():
            self.packetHandler.write1ByteTxRx(
                self.portHandler, info['id'], self.ADDR_TORQUE_ENABLE, 1 if enable else 0
            )

    def set_smooth_motion_profile(self):
        """모든 모터에 가속도와 속도 제한을 걸어 부드럽게 만듦"""
        # Velocity(속도): 0 ~ 32767 (약 100~300 추천)
        # Acceleration(가속도): 0 ~ 32767 (약 20~100 추천)
        
        DEFAULT_VELOCITY = 200  # 낮을수록 천천히 움직임
        DEFAULT_ACCEL = 50      # 낮을수록 부드럽게 출발/정지 (S-Curve)
        
        print(f"⚡ [Settings] 모션 프로파일 적용 (Vel: {DEFAULT_VELOCITY}, Acc: {DEFAULT_ACCEL})")
        
        for name, info in self.motors.items():
            # 가속도 설정
            self.packetHandler.write4ByteTxRx(
                self.portHandler, info['id'], self.ADDR_PROFILE_ACCELERATION, DEFAULT_ACCEL
            )
            # 속도 설정
            self.packetHandler.write4ByteTxRx(
                self.portHandler, info['id'], self.ADDR_PROFILE_VELOCITY, DEFAULT_VELOCITY
            )

    def move_joint(self, joint_name, goal_position):
        if joint_name not in self.motors:
            print(f"⚠️ 존재하지 않는 관절: {joint_name}")
            return

        motor_info = self.motors[joint_name]
        dxl_id = motor_info['id']
        
        # 안전 범위 체크
        safe_pos = max(motor_info['min'], min(goal_position, motor_info['max']))
        
        self.packetHandler.write4ByteTxRx(
            self.portHandler, dxl_id, self.ADDR_GOAL_POSITION, int(safe_pos)
        )

    def go_to_neutral(self):
        print("\n⚡ [System] 로봇을 초기 자세로 정렬합니다...")
        self.enable_torque(True)
        self.set_smooth_motion_profile() # 초기화 때도 부드럽게
        
        count = 0
        for name, info in self.motors.items():
            self.move_joint(name, info['neutral'])
            time.sleep(0.05) # 약간의 시차
            count += 1
        print(f"✅ [System] 초기화 완료 ({count}개 관절)\n")

    def close(self):
        self.enable_torque(False)
        self.portHandler.closePort()
        print("👋 [Driver] 연결 종료")