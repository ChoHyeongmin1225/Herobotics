import os
from dynamixel_sdk import * # Uses Dynamixel SDK library

# ==============================================================================
# ⚙️ 설정 (Herobot Hardware Setup)
# ==============================================================================
DEVICENAME          = '/dev/ttyUSB0'    # 포트 이름
BAUDRATE            = 57600     # 통신 속도
PROTOCOL_VERSION    = 2.0       # 프로토콜 버전

# 2XL430 / XC430 / XL330 등 X-Series 공통 주소
ADDR_PRESENT_POSITION = 132     # 현재 위치 주소 (4 Byte)
ADDR_MODEL_NUMBER     = 0       # 모델 번호 주소 (2 Byte)

# 스캔할 ID 범위 (1번부터 20번까지만 스캔해봅니다)
MAX_ID_SCAN         = 20
# ==============================================================================

def main():
    # 1. 포트 핸들러 & 패킷 핸들러 초기화
    portHandler = PortHandler(DEVICENAME)
    packetHandler = PacketHandler(PROTOCOL_VERSION)

    # 2. 포트 열기
    if portHandler.openPort():
        print(f"✅ 포트 열기 성공: {DEVICENAME}")
    else:
        print(f"❌ 포트 열기 실패: {DEVICENAME}")
        print("   - 케이블이 연결되었는지, 포트 번호가 맞는지 확인하세요.")
        exit()

    # 3. 통신 속도 설정
    if portHandler.setBaudRate(BAUDRATE):
        print(f"✅ 보드레이트 설정 성공: {BAUDRATE}")
    else:
        print(f"❌ 보드레이트 설정 실패")
        exit()

    print("\n🔍 다이나믹셀 스캔을 시작합니다 (ID 1 ~ 20)...")
    print("=" * 60)
    print(f"{'ID':<5} | {'모델명':<20} | {'현재 위치 (0~4095)':<15} | {'상태'}")
    print("=" * 60)

    found_count = 0

    # 4. ID 스캔 루프
    for dxl_id in range(1, MAX_ID_SCAN + 1):
        # (1) PING을 보내서 모터가 존재하는지 확인
        model_number, result, error = packetHandler.ping(portHandler, dxl_id)
        
        if result == COMM_SUCCESS:
            # (2) 존재한다면 현재 위치값 읽기
            present_pos, result_pos, error_pos = packetHandler.read4ByteTxRx(
                portHandler, dxl_id, ADDR_PRESENT_POSITION
            )
            
            # 모델명 매핑 (2XL430 확인용)
            model_name = "Unknown"
            if model_number == 1090: model_name = "2XL430-W250" # 예시
            else: model_name = f"Model-{model_number}"

            if result_pos == COMM_SUCCESS:
                print(f"{dxl_id:<5} | {model_name:<20} | {present_pos:<15} | 🟢 연결됨")
                found_count += 1
            else:
                print(f"{dxl_id:<5} | {model_name:<20} | {'ERROR':<15} | ⚠️ 위치 읽기 실패")

    print("=" * 60)
    print(f"🏁 스캔 완료. 총 {found_count}개의 모터를 찾았습니다.\n")
    
    # 포트 닫기
    portHandler.closePort()

if __name__ == '__main__':
    main()