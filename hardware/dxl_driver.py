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
        # 빠른 조회를 위해 dict로 변환
        self.motors = {m['name']: m for m in self.spec['motors']}
        
        # 2. 다이나믹셀 통신 핸들러
        self.portHandler = PortHandler(self.port_name)
        self.packetHandler = PacketHandler(2.0)
        
        # 3. 제어 테이블 주소 (X-Series 공통)
        self.ADDR_OPERATING_MODE = 11        # ★ 운영 모드 (1:속도, 3:위치)
        self.ADDR_TORQUE_ENABLE = 64
        self.ADDR_GOAL_VELOCITY = 104        # ★ 속도 제어용 목표값
        self.ADDR_PROFILE_ACCELERATION = 108
        self.ADDR_PROFILE_VELOCITY = 112     # 위치 제어용 프로파일 속도
        self.ADDR_GOAL_POSITION = 116        # 위치 제어용 목표값
        
        # 4. 연결 시작
        if not self.portHandler.openPort():
            raise Exception(f"❌ 포트 열기 실패: {self.port_name}")
        if not self.portHandler.setBaudRate(self.baudrate):
            raise Exception(f"❌ 보드레이트 설정 실패: {self.baudrate}")
            
        print(f"✅ [Driver] 하드웨어 연결 성공 ({self.port_name})")
        
        # 5. 모터 모드 설정 및 초기화
        # 주의: 운영 모드를 바꾸려면 토크가 꺼져 있어야 함
        self.enable_torque(False) 
        self.setup_operating_modes() # ★ 바퀴/관절 모드 구분 설정
        self.enable_torque(True)
        
        # 6. 모션 프로파일(부드러움) 적용
        self.set_smooth_motion_profile()

    def setup_operating_modes(self):
        """JSON의 'type'에 따라 운영 모드를 설정합니다."""
        print("⚡ [System] 모터 운영 모드 설정 중...")
        for name, info in self.motors.items():
            motor_id = info['id']
            # type이 'wheel'이면 속도제어(1), 아니면 위치제어(3)
            # Wheel Mode: 1, Position Mode: 3 (Extended Position Mode: 4)
            target_mode = 1 if info.get('type') == 'wheel' else 3
            
            self.packetHandler.write1ByteTxRx(
                self.portHandler, motor_id, self.ADDR_OPERATING_MODE, target_mode
            )
            mode_str = "Velocity" if target_mode == 1 else "Position"
            # 디버깅용 로그 (너무 길면 주석 처리)
            # print(f"   └─ ID {motor_id} ({name}): {mode_str} Mode")

    def enable_torque(self, enable):
        """모든 모터의 토크를 켜거나 끕니다."""
        val = 1 if enable else 0
        for name, info in self.motors.items():
            self.packetHandler.write1ByteTxRx(
                self.portHandler, info['id'], self.ADDR_TORQUE_ENABLE, val
            )

    def set_smooth_motion_profile(self):
        """관절 모터에는 부드러운 움직임을, 바퀴에는 가속도를 설정"""
        # 관절용 설정
        JOINT_VEL = 200  
        JOINT_ACC = 50   
        # 바퀴용 설정 (가속도만 설정, 속도는 명령으로 제어)
        WHEEL_ACC = 50 
        
        for name, info in self.motors.items():
            dxl_id = info['id']
            if info.get('type') == 'wheel':
                # 바퀴는 가속도만 설정 (급출발/급정지 방지)
                self.packetHandler.write4ByteTxRx(
                    self.portHandler, dxl_id, self.ADDR_PROFILE_ACCELERATION, WHEEL_ACC
                )
            else:
                # 관절은 속도와 가속도 모두 프로파일 설정
                self.packetHandler.write4ByteTxRx(
                    self.portHandler, dxl_id, self.ADDR_PROFILE_ACCELERATION, JOINT_ACC
                )
                self.packetHandler.write4ByteTxRx(
                    self.portHandler, dxl_id, self.ADDR_PROFILE_VELOCITY, JOINT_VEL
                )

    def move_joint(self, joint_name, value):
        """
        통합 이동 함수 (에러 체크 기능 추가됨)
        """
        if joint_name not in self.motors:
            print(f"⚠️ 존재하지 않는 모터: {joint_name}")
            return

        info = self.motors[joint_name]
        dxl_id = info['id']
        motor_type = info.get('type', 'joint')

        # 안전 범위 체크
        safe_val = int(max(info['min'], min(value, info['max'])))
        
        # 1. 명령 패킷 전송
        if motor_type == 'wheel':
            dxl_comm_result, dxl_error = self.packetHandler.write4ByteTxRx(
                self.portHandler, dxl_id, self.ADDR_GOAL_VELOCITY, safe_val
            )
        else:
            dxl_comm_result, dxl_error = self.packetHandler.write4ByteTxRx(
                self.portHandler, dxl_id, self.ADDR_GOAL_POSITION, safe_val
            )
            
        # 2. 통신 에러 체크 (케이블 문제 등)
        if dxl_comm_result != COMM_SUCCESS:
            print(f"🚨 [Comm Error] ID:{dxl_id} {self.packetHandler.getTxRxResult(dxl_comm_result)}")
            
        # 3. 하드웨어 에러 체크 (과부하, 과열 등)
        elif dxl_error != 0:
            error_msg = self.packetHandler.getRxPacketError(dxl_error)
            print(f"🔥 [HW Error] ID:{dxl_id} {error_msg} (Torque OFF됨)")
            
            # (선택) 에러 발생 시 자동으로 토크를 다시 켜는 시도
            # self.reboot_motor(dxl_id) # 리부트 기능은 별도 구현 필요

    def go_to_neutral(self):
        """초기화: 관절은 초기 위치로, 바퀴는 정지(0)"""
        print("\n⚡ [System] 로봇 자세 및 바퀴 초기화...")
        self.enable_torque(True)
        
        count = 0
        for name, info in self.motors.items():
            # 바퀴의 neutral은 보통 0 (정지)
            target = info['neutral']
            self.move_joint(name, target)
            if info.get('type') != 'wheel':
                time.sleep(0.05) # 관절만 순차 딜레이 (바퀴는 즉시 멈춤)
            count += 1
        print(f"✅ [System] 초기화 완료 ({count}개 모터)\n")

    def close(self):
        # 종료 시 안전을 위해 바퀴 먼저 정지
        for name, info in self.motors.items():
            if info.get('type') == 'wheel':
                self.move_joint(name, 0)
        
        time.sleep(0.5)
        self.enable_torque(False)
        self.portHandler.closePort()
        print("👋 [Driver] 연결 종료")