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
        self.motors = {m['name']: m for m in self.spec['motors']} # 이름으로 모터 찾기 편하게 변환
        
        # 2. 다이나믹셀 통신 설정
        self.portHandler = PortHandler(self.port_name)
        self.packetHandler = PacketHandler(2.0) # 프로토콜 2.0
        
        # 3. 연결 시작
        if not self.portHandler.openPort():
            raise Exception(f"❌ 포트 열기 실패: {self.port_name}")
        if not self.portHandler.setBaudRate(self.baudrate):
            raise Exception(f"❌ 보드레이트 설정 실패: {self.baudrate}")
            
        print(f"✅ [Driver] 하드웨어 연결 성공 ({self.port_name})")
        self.enable_torque(True)

    def enable_torque(self, enable):
        """모든 모터 토크 켜기/끄기"""
        for name, info in self.motors.items():
            self.packetHandler.write1ByteTxRx(
                self.portHandler, info['id'], 64, 1 if enable else 0 # 64: Torque Enable 주소
            )
        print(f"⚡ [Driver] 토크 {'ON' if enable else 'OFF'}")

    def move_joint(self, joint_name, goal_position):
        """이름으로 모터 제어하기 (예: move_joint('head_pan', 2048))"""
        if joint_name not in self.motors:
            print(f"⚠️ 존재하지 않는 관절 이름: {joint_name}")
            return

        motor_info = self.motors[joint_name]
        dxl_id = motor_info['id']
        
        # 안전 범위 체크 (Min/Max Limit)
        safe_pos = max(motor_info['min'], min(goal_position, motor_info['max']))
        
        # 명령 전송
        result, error = self.packetHandler.write4ByteTxRx(
            self.portHandler, dxl_id, 116, int(safe_pos) # 116: Goal Position 주소
        )
        
        if result != COMM_SUCCESS:
            print(f"❌ 모터 통신 에러 (ID {dxl_id}): {self.packetHandler.getTxRxResult(result)}")

    def close(self):
        self.enable_torque(False)
        self.portHandler.closePort()
        print("👋 [Driver] 연결 종료")