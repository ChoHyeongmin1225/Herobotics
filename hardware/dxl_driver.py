import json
import time
from dynamixel_sdk import *

class DxlDriver:
    def __init__(self, spec_path="config/hardware_spec.json"):
        # 1. 스펙 로드
        with open(spec_path, 'r', encoding='utf-8') as f:
            self.spec = json.load(f)
        
        self.port_name = self.spec['robot_info']['port']
        self.baudrate = self.spec['robot_info']['default_baudrate']
        self.motors = {m['name']: m for m in self.spec['motors']}
        
        # 2. 통신 핸들러
        self.portHandler = PortHandler(self.port_name)
        self.packetHandler = PacketHandler(2.0)

        # ★ [추가] SyncWrite 핸들러 (동시 제어용)
        # 주소 116(Goal Position)에 4바이트씩 씀
        self.ADDR_GOAL_POSITION = 116
        self.ADDR_GOAL_VELOCITY = 104
        self.groupSyncWritePos = GroupSyncWrite(self.portHandler, self.packetHandler, self.ADDR_GOAL_POSITION, 4)
        
        # 주소 정의
        self.ADDR_OPERATING_MODE = 11
        self.ADDR_TORQUE_ENABLE = 64
        self.ADDR_PROFILE_ACCELERATION = 108
        self.ADDR_PROFILE_VELOCITY = 112

        # 3. 연결
        if not self.portHandler.openPort():
            raise Exception(f"❌ 포트 열기 실패: {self.port_name}")
        if not self.portHandler.setBaudRate(self.baudrate):
            raise Exception(f"❌ 보드레이트 설정 실패: {self.baudrate}")
            
        print(f"✅ [Driver] 하드웨어 연결 성공 ({self.port_name})")
        
        # 4. 초기화
        self.enable_torque(False) 
        self.setup_operating_modes()
        self.enable_torque(True)
        
        # ★ 초기에는 '아주 느린 모드'로 설정 (안전 복귀용)
        self.set_motion_profile(velocity=50, accel=10) 

    def setup_operating_modes(self):
        """운영 모드 설정 (Wheel:1, Joint:3)"""
        for name, info in self.motors.items():
            motor_id = info['id']
            target_mode = 1 if info.get('type') == 'wheel' else 3
            self.packetHandler.write1ByteTxRx(
                self.portHandler, motor_id, self.ADDR_OPERATING_MODE, target_mode
            )

    def enable_torque(self, enable):
        val = 1 if enable else 0
        for name, info in self.motors.items():
            self.packetHandler.write1ByteTxRx(
                self.portHandler, info['id'], self.ADDR_TORQUE_ENABLE, val
            )

    def set_motion_profile(self, velocity=200, accel=50):
        """
        ★ 모터의 움직임 성질을 실시간으로 변경하는 함수
        - velocity (속도): 클수록 빠름 (기본 200, 초기화시 50 추천)
        - accel (가속도): 클수록 급출발/급정지 (기본 50, 부드러움 원하면 10~20)
        """
        # 바퀴용 가속도
        WHEEL_ACC = 50 
        
        for name, info in self.motors.items():
            dxl_id = info['id']
            if info.get('type') == 'wheel':
                self.packetHandler.write4ByteTxRx(
                    self.portHandler, dxl_id, self.ADDR_PROFILE_ACCELERATION, WHEEL_ACC
                )
            else:
                self.packetHandler.write4ByteTxRx(
                    self.portHandler, dxl_id, self.ADDR_PROFILE_ACCELERATION, int(accel)
                )
                self.packetHandler.write4ByteTxRx(
                    self.portHandler, dxl_id, self.ADDR_PROFILE_VELOCITY, int(velocity)
                )
        print(f"⚡ [Settings] 모션 프로파일 변경 (Vel:{velocity}, Acc:{accel})")

    def move_joint(self, joint_name, value, velocity=None):
        """
        통합 이동 함수 (속도 제어 추가됨)
        - velocity: 이 동작을 수행할 속도 (0 ~ 1000). None이면 기본값 사용.
        """
        if joint_name not in self.motors:
            print(f"⚠️ 존재하지 않는 모터: {joint_name}")
            return

        info = self.motors[joint_name]
        dxl_id = info['id']
        motor_type = info.get('type', 'joint')

        # 안전 범위 체크
        safe_val = int(max(info['min'], min(value, info['max'])))
        
        # ★ [추가] 동작별 속도 설정 (이 동작만 느리게/빠르게 하고 싶을 때)
        if velocity is not None and motor_type != 'wheel':
            # 속도 프로파일 변경 (Goal Velocity 아님! Profile Velocity임)
            self.packetHandler.write4ByteTxRx(
                self.portHandler, dxl_id, self.ADDR_PROFILE_VELOCITY, int(velocity)
            )
        
        # 명령 패킷 전송
        if motor_type == 'wheel':
            dxl_comm_result, dxl_error = self.packetHandler.write4ByteTxRx(
                self.portHandler, dxl_id, self.ADDR_GOAL_VELOCITY, safe_val
            )
        else:
            dxl_comm_result, dxl_error = self.packetHandler.write4ByteTxRx(
                self.portHandler, dxl_id, self.ADDR_GOAL_POSITION, safe_val
            )
            
        if dxl_comm_result != COMM_SUCCESS:
            print(f"🚨 [Comm Error] ID:{dxl_id} {self.packetHandler.getTxRxResult(dxl_comm_result)}")
        elif dxl_error != 0:
            error_msg = self.packetHandler.getRxPacketError(dxl_error)
            print(f"🔥 [HW Error] ID:{dxl_id} {error_msg}")

    def go_to_neutral(self):
        """
        ★ 안정화된 초기화 함수
        1. 모션 프로파일을 '느리게' 변경
        2. SyncWrite로 모든 관절 동시 명령 전송 (딜레이 없음)
        """
        print("\n⚡ [System] 로봇 자세 초기화 (Slow & Sync Mode)...")
        
        # 1. 천천히 움직이도록 설정 (덜컹거림 방지)
        self.set_motion_profile(velocity=40, accel=10) 
        self.enable_torque(True)
        
        # 2. SyncWrite 패킷 생성
        self.groupSyncWritePos.clearParam()
        
        target_motor_count = 0
        for name, info in self.motors.items():
            if info.get('type') == 'wheel':
                self.move_joint(name, 0) # 바퀴는 즉시 정지
                continue
                
            # 관절 모터만 동시 제어 리스트에 추가
            motor_id = info['id']
            target_pos = info['neutral']
            
            # 4바이트 분해 (Low Byte -> High Byte)
            param_goal_position = [
                DXL_LOBYTE(DXL_LOWORD(target_pos)),
                DXL_HIBYTE(DXL_LOWORD(target_pos)),
                DXL_LOBYTE(DXL_HIWORD(target_pos)),
                DXL_HIBYTE(DXL_HIWORD(target_pos))
            ]
            
            if self.groupSyncWritePos.addParam(motor_id, param_goal_position):
                target_motor_count += 1

        # 3. 전송 (모든 모터 동시 출발)
        results = self.groupSyncWritePos.txPacket()
        if results != COMM_SUCCESS:
            print(f"⚠️ SyncWrite 실패: {self.packetHandler.getTxRxResult(results)}")
            
        print(f"✅ [System] {target_motor_count}개 관절 동시 이동 명령 전송")
        
        # 4. 이동 시간 확보 후 정상 속도로 복귀
        time.sleep(2.0) # 천천히 이동하니까 충분히 기다림
        self.set_motion_profile(velocity=200, accel=50) # 다시 빠릿빠릿하게

    def close(self):
        for name, info in self.motors.items():
            if info.get('type') == 'wheel':
                self.move_joint(name, 0)
        time.sleep(0.5)
        self.enable_torque(False)
        self.portHandler.closePort()
        print("👋 [Driver] 연결 종료")