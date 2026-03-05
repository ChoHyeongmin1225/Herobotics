import speech_recognition as sr
import time

class VoiceInterface:
    def __init__(self):
        self.r = sr.Recognizer()
        self.mic = sr.Microphone(device_index=0)
        
        # 인식 감도 설정 (Dynamic Energy Threshold)
        self.r.dynamic_energy_threshold = True
        self.r.energy_threshold = 300  # 기본 소음 기준값 (조절 가능)
        self.r.pause_threshold = 0.8   # 말이 0.8초 끊기면 끝난 것으로 간주

        # 초기 소음 측정
        with self.mic as source:
            print("\n🎤 [Voice] 주변 소음 측정 중... (1초간 침묵해주세요)")
            self.r.adjust_for_ambient_noise(source, duration=1)
            print("✅ [Voice] 귀가 열렸습니다. 소음 기준값:", self.r.energy_threshold)

    def wait_for_wake_word(self, target_word="히어로봇"):
        """
        호출어(True) 또는 종료(False)를 감지하는 함수
        """
        target_words = [target_word, "히어로", "로봇"]
        # ★ [추가] 종료 키워드 리스트
        exit_words = ["종료"]
        
        print(f"\n👂 [WakeWord] 저를 불러주세요... (인식 대상: {target_words})")
        
        with self.mic as source:
            self.r.adjust_for_ambient_noise(source, duration=0.5)
        
        while True:
            try:
                with self.mic as source:
                    audio = self.r.listen(source, timeout=None, phrase_time_limit=2)
                
                text = self.r.recognize_google(audio, language='ko-KR')
                print(f"   👂 [DEBUG] 들린 말: '{text}'") 

                # 1. 호출어 확인 -> True 반환 (기존 로직)
                if any(word in text for word in target_words):
                    print(f"⚡ [WakeWord] 호출 감지! (키워드 포함: {text})")
                    return True
                
                # 2. ★ [추가] 종료 명령 확인 -> False 반환
                if any(word in text for word in exit_words):
                    print(f"👋 [WakeWord] 종료 명령 감지! ({text})")
                    return False
                    
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                print("⚠️ [Voice] 인터넷 연결을 확인하세요.")
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ [Voice Error] {e}")

    def listen_command(self):
        """
        명령어를 듣고 텍스트로 반환하는 함수
        """
        print("🎤 [Command] 듣고 있습니다... 말씀하세요!")
        # 삐~ 소리 효과음 재생 코드를 여기에 넣으면 좋습니다.
        
        try:
            with self.mic as source:
                # 5초간 말 안 하면 타임아웃, 말 시작하면 최대 10초까지 듣기
                audio = self.r.listen(source, timeout=5, phrase_time_limit=10)
            
            print("⏳ [Command] 인식 중...")
            text = self.r.recognize_google(audio, language='ko-KR')
            print(f"📝 [User]: \"{text}\"")
            return text
            
        except sr.WaitTimeoutError:
            print("⚠️ [Command] 시간이 초과되었습니다.")
            return None
        except sr.UnknownValueError:
            print("⚠️ [Command] 무슨 말인지 모르겠어요.")
            return None
        except Exception as e:
            print(f"⚠️ [Command Error] {e}")
            return None