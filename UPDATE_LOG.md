# Update Log - 2025-12-07

## Version 1.1.1 - Error Logging & WiFi Fixes (2025-12-07)

### 버그 수정

#### 오류 로깅 개선
- **전체 스택 트레이스 출력**
  - 모든 예외 처리에 `traceback.print_exc()` 추가
  - 빈 오류 메시지 대신 상세한 디버깅 정보 제공
  - 타임아웃 모니터, 자동 복귀, WiFi 체크 등 모든 백그라운드 작업 포함

#### WiFi 연결 인코딩 문제 해결
- **UnicodeDecodeError 수정**
  - `subprocess.run()`에 `errors='replace'` 파라미터 추가
  - cp949 인코딩 실패 시 문자 대체로 처리
  - `stdout` None 체크 추가

- **안정성 개선**
  - WiFi 정보를 가져올 수 없을 때 조기 종료
  - SSID 추출 실패 시 안전한 처리

### 수정된 오류들
1. ✅ `UnicodeDecodeError: 'cp949' codec can't decode byte 0xec`
2. ✅ `WiFi 체크 오류: 'NoneType' object has no attribute 'split'`
3. ✅ 타임아웃 모니터 빈 오류 메시지
4. ✅ 자동 복귀 빈 오류 메시지

### 기술적 세부사항
```python
# WiFi 인코딩 문제 해결
result = subprocess.run(
    ['netsh', 'wlan', 'show', 'interfaces'],
    encoding='cp949',
    errors='replace'  # 인코딩 오류 시 문자 대체
)

# 전체 트레이스 출력
except Exception as e:
    print(f"오류: {e}")
    traceback.print_exc()  # 상세한 스택 트레이스
```

---

## Version 1.1.0 - Stability & UX Improvements

### 주요 변경사항

#### 1. 프로그램 안정성 개선 (Freeze 방지)
- **스레드 안전성 강화**
  - 모든 백그라운드 스레드에서 `page.run_task()` 사용으로 UI 업데이트 안전성 확보
  - `timeout_monitor()`, `auto_return()` 함수에서 스레드 안전한 UI 업데이트 적용

- **예외 처리 강화**
  - 모든 백그라운드 작업에 try-except 블록 추가
  - 오류 발생 시 콘솔 로그 출력 및 프로그램 계속 실행

- **네트워크 타임아웃 설정**
  - FastAPI 서버 요청에 5초 timeout 설정
  - 네트워크 지연으로 인한 hang 방지

#### 2. 중복 인쇄 방지
- **중복 클릭 차단 메커니즘**
  - `processing_selection` 플래그 추가
  - 아이콘 선택 처리 중 추가 클릭 무시
  - Page 1 복귀 시 자동 플래그 리셋

- **서버 전송 비동기화**
  - `send_to_server()` 함수를 별도 데몬 스레드에서 실행
  - UI 블로킹 없이 서버 통신 처리

#### 3. UX 개선
- **Page 4 즉시 복귀 기능**
  - 등록 완료 화면(Page 4)에서 화면 터치 시 즉시 첫 화면으로 복귀
  - 10초 자동 복귀 타이머는 그대로 유지
  - 사용자가 급하게 다음 등록을 시작할 수 있도록 개선

#### 4. WiFi 자동 연결
- **INVEN2 WiFi 자동 연결**
  - 프로그램 시작 시 현재 WiFi SSID 확인
  - INVEN2가 아닐 경우 자동으로 INVEN2에 연결 시도
  - 백그라운드 스레드로 실행하여 프로그램 시작 지연 없음

- **연결 상태 로깅**
  - 현재 SSID 콘솔 출력
  - 연결 성공/실패 상태 로그

### 기술적 세부사항

#### Thread Safety
```python
# Before (위험)
def timeout_monitor():
    page.update()  # 백그라운드 스레드에서 직접 호출

# After (안전)
def timeout_monitor():
    page.run_task(update_timeout_display_safe)  # 메인 스레드 큐에 추가
```

#### Duplicate Prevention
```python
# 중복 클릭 방지 로직
def on_icon_select(index):
    if processing_selection.current:
        print("이미 처리 중입니다. 중복 클릭 무시")
        return

    processing_selection.current = True
    # ... 처리 로직
```

#### WiFi Auto-Connect
```python
def check_and_connect_wifi():
    # netsh 명령어로 현재 SSID 확인
    result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], ...)

    if current_ssid != "INVEN2":
        # INVEN2로 자동 연결
        subprocess.run(['netsh', 'wlan', 'connect', 'name=INVEN2'], ...)
```

### 파일 변경 내역

#### 수정된 파일
- `main.py`
  - WiFi 자동 연결 기능 추가 (line 9-51)
  - 스레드 안전성 개선 (line 120-167)
  - 중복 클릭 방지 (line 109-111, 474-496)
  - Page 4 즉시 복귀 (line 567-571)

#### 새로 생성된 파일
- `.gitignore` - Python/IDE/OS 임시 파일 제외
- `UPDATE_LOG.md` - 업데이트 이력 문서

#### 백업 파일
- `main_backup.py` - 이전 버전 백업

### 테스트 체크리스트

- [x] 프로그램 시작 시 WiFi INVEN2 연결 확인
- [x] Page 2에서 120초 타임아웃 작동 확인
- [x] Page 3에서 120초 타임아웃 작동 확인
- [x] 아이콘 선택 시 중복 클릭 무시 확인
- [x] Page 4에서 화면 터치 시 즉시 복귀 확인
- [x] Page 4에서 10초 자동 복귀 확인
- [x] FastAPI 서버 통신 (성공/실패) 확인
- [x] 장시간 실행 시 메모리 누수 없음 확인

### 알려진 제한사항

1. **WiFi 연결**
   - INVEN2가 Windows에 저장된 프로필이어야 함
   - 관리자 권한 없이는 새 WiFi 프로필 추가 불가

2. **네트워크 요구사항**
   - FastAPI 서버(`192.168.50.122:8001`)에 접근 가능해야 함
   - 서버 응답 시간 5초 이내 권장

### 다음 버전 계획

- [ ] 오프라인 모드 지원 (서버 미연결 시 로컬 큐잉)
- [ ] 관리자 패널 (통계, 설정 변경)
- [ ] 다국어 지원
- [ ] 사용자 피드백 애니메이션

---

## 커밋 히스토리

### v1.1.0 (2025-12-07)
- Add WiFi auto-connect and stability improvements
- Fix program freeze issues with thread-safe UI updates
- Add duplicate click prevention for icon selection
- Add instant return on Page 4 tap
- Improve error handling and logging

### v1.0.0 (2025-12-07)
- Initial release
- 4-page registration flow
- QWERTY virtual keyboard
- Timeout management (120s)
- FastAPI server integration
- Icon pattern mapping
