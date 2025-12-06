import flet as ft
import time
import threading
import requests
from datetime import datetime
import subprocess
import re
import traceback

def check_and_connect_wifi():
    """현재 WiFi SSID 확인하고 INVEN2가 아니면 연결"""
    try:
        # 현재 연결된 WiFi SSID 확인
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True,
            text=True,
            encoding='cp949',
            errors='replace'  # 인코딩 오류 시 문자 대체
        )

        # stdout가 None이거나 비어있는 경우 처리
        if not result.stdout:
            print("WiFi 정보를 가져올 수 없습니다")
            return

        # SSID 추출
        current_ssid = None
        for line in result.stdout.split('\n'):
            if 'SSID' in line and 'BSSID' not in line:
                # "    SSID                   : INVEN2" 형식에서 SSID 추출
                match = re.search(r':\s*(.+)', line)
                if match:
                    current_ssid = match.group(1).strip()
                    break

        print(f"현재 WiFi SSID: {current_ssid}")

        # INVEN2가 아니면 연결 시도
        if current_ssid != "INVEN2":
            print("INVEN2로 WiFi 연결 시도...")
            connect_result = subprocess.run(
                ['netsh', 'wlan', 'connect', 'name=INVEN2'],
                capture_output=True,
                text=True,
                encoding='cp949',
                errors='replace'
            )

            if connect_result.stdout and ("연결 요청이 완료되었습니다" in connect_result.stdout or "successfully" in connect_result.stdout.lower()):
                print("INVEN2 연결 성공")
                time.sleep(2)  # 연결 대기
            else:
                print(f"INVEN2 연결 실패: {connect_result.stdout if connect_result.stdout else 'stdout 없음'}")
        else:
            print("이미 INVEN2에 연결되어 있습니다")

    except Exception as e:
        print(f"WiFi 체크 오류: {e}")
        traceback.print_exc()

def main(page: ft.Page):
    # WiFi 체크 및 연결 (백그라운드에서 비동기 실행)
    threading.Thread(target=check_and_connect_wifi, daemon=True).start()

    # 페이지 설정 - 세로모드 키오스크 (1080 x 1920)
    page.title = "Fantasy Inventory Kiosk"
    page.window.width = 1080
    page.window.height = 1920
    page.window.left = 0
    page.window.top = 0
    page.window.resizable = False
    page.window.title_bar_hidden = True
    page.window.frameless = True
    page.padding = 0
    page.spacing = 0
    page.bgcolor = "#f5f5f5"

    # ==================== 설정 변수 ====================

    # 타임아웃 설정 (초 단위) - 중간 페이지에서 이 시간 동안 입력이 없으면 시작 페이지로 복귀
    TIMEOUT_SECONDS = 120  # 2분

    # FastAPI 서버 URL
    FASTAPI_SERVER_URL = "http://192.168.50.122:8001"

    # 아이콘 인덱스 → 패턴 번호 매핑 (5x2 그리드, 위에서부터 왼쪽→오른쪽)
    icon_pattern_map = {
        0: "13",  # 1행 왼쪽
        1: "05",  # 1행 오른쪽
        2: "20",  # 2행 왼쪽
        3: "07",  # 2행 오른쪽
        4: "01",  # 3행 왼쪽
        5: "17",  # 3행 오른쪽
        6: "18",  # 4행 왼쪽
        7: "02",  # 4행 오른쪽
        8: "12",  # 5행 왼쪽
        9: "06",  # 5행 오른쪽
    }

    # ==================== 상태 관리 ====================

    current_page = ft.Ref[int]()
    current_page.current = 0
    user_name = ft.Ref[str]()
    user_name.current = ""
    selected_icon = ft.Ref[int]()

    # 타임아웃 관리
    last_interaction_time = ft.Ref[float]()
    last_interaction_time.current = time.time()
    timeout_thread_running = ft.Ref[bool]()
    timeout_thread_running.current = False
    remaining_seconds = ft.Ref[int]()
    remaining_seconds.current = TIMEOUT_SECONDS
    timeout_display_page2 = ft.Ref[ft.Text]()  # 페이지 2 카운트다운 표시
    timeout_display_page3 = ft.Ref[ft.Text]()  # 페이지 3 카운트다운 표시

    # 중복 클릭 방지
    processing_selection = ft.Ref[bool]()
    processing_selection.current = False

    # ==================== 타임아웃 관리 ====================

    def reset_timeout():
        """사용자 상호작용 시 타임아웃 타이머 리셋"""
        last_interaction_time.current = time.time()
        remaining_seconds.current = TIMEOUT_SECONDS

    def update_timeout_display_safe():
        """타임아웃 디스플레이 업데이트 (스레드 안전)"""
        try:
            if timeout_display_page2.current:
                timeout_display_page2.current.value = f"{remaining_seconds.current}초"
            if timeout_display_page3.current:
                timeout_display_page3.current.value = f"{remaining_seconds.current}초"
            page.update()
        except Exception as e:
            print(f"타임아웃 디스플레이 업데이트 오류: {e}")
            traceback.print_exc()

    def reset_to_start():
        """시작 페이지로 초기화"""
        processing_selection.current = False
        current_page.current = 0
        user_name.current = ""
        selected_icon.current = None
        last_interaction_time.current = time.time()
        remaining_seconds.current = TIMEOUT_SECONDS
        try:
            update_page()
        except Exception as e:
            print(f"페이지 리셋 오류: {e}")
            traceback.print_exc()

    def timeout_monitor():
        """백그라운드에서 타임아웃 체크 (페이지 2, 3에서만 동작)"""
        while timeout_thread_running.current:
            time.sleep(1)  # 1초마다 체크

            try:
                # 페이지 2 또는 3에서만 타임아웃 체크
                if current_page.current in [1, 2]:
                    elapsed = time.time() - last_interaction_time.current
                    remaining = int(TIMEOUT_SECONDS - elapsed)

                    if remaining >= 0:
                        remaining_seconds.current = remaining
                        # 스레드 안전하게 UI 업데이트
                        page.run_task(update_timeout_display_safe)

                    if elapsed >= TIMEOUT_SECONDS:
                        print(f"타임아웃 발생: {elapsed:.1f}초 경과. 시작 페이지로 복귀")
                        page.run_task(reset_to_start)
                else:
                    # 페이지 1, 4에서는 타이머 리셋
                    remaining_seconds.current = TIMEOUT_SECONDS
            except Exception as e:
                print(f"타임아웃 모니터 오류: {e}")
                traceback.print_exc()

    def start_timeout_monitor():
        """타임아웃 모니터 스레드 시작"""
        if not timeout_thread_running.current:
            timeout_thread_running.current = True
            thread = threading.Thread(target=timeout_monitor, daemon=True)
            thread.start()

    # ==================== 공통 컴포넌트 ====================

    # 브레드크럼 네비게이션
    def create_breadcrumb():
        steps = ["등록시작", "이니셜등록", "아이콘선택", "등록완료"]
        current = current_page.current

        breadcrumb_items = []
        for i, step in enumerate(steps):
            color = "#7c8db5" if i <= current else "#d0d5e0"
            breadcrumb_items.append(ft.Text(step, size=14, color=color, weight=ft.FontWeight.W_500))
            if i < len(steps) - 1:
                breadcrumb_items.append(ft.Text(" > ", size=14, color="#d0d5e0"))

        return ft.Container(
            content=ft.Row(breadcrumb_items, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.only(top=20, bottom=20),
        )

    # ==================== Page 1: 메인 메뉴 ====================

    def on_start_click(e):
        reset_timeout()
        processing_selection.current = False  # 리셋
        current_page.current = 1
        user_name.current = ""  # 초기화
        update_page()

    def create_page1():
        # 배경 이미지와 버튼을 스택으로 배치
        return ft.Container(
            content=ft.Stack([
                # 배경 이미지
                ft.Image(
                    src="design/1_Screen_IMG.png",
                    width=1080,
                    height=1920,
                    fit=ft.ImageFit.FILL,
                ),
                # 버튼 이미지를 하단에 배치
                ft.Container(
                    content=ft.Image(
                        src="design/1_Screen_UI.png",
                        width=600,
                        height=80,
                        fit=ft.ImageFit.CONTAIN,
                    ),
                    left=240,  # (1080-600)/2 = 중앙 정렬
                    bottom=150,
                    on_click=on_start_click,
                ),
            ]),
            width=1080,
            height=1920,
        )

    # ==================== Page 2: 이니셜 등록 ====================

    def on_keyboard_key_press(key):
        reset_timeout()  # 키보드 입력 시 타임아웃 리셋
        if key == "ENTER":
            if user_name.current:
                current_page.current = 2
                update_page()
        elif key == "BACK":
            if user_name.current:
                user_name.current = user_name.current[:-1]
                name_input.current.value = user_name.current
                page.update()
        else:
            # 최대 8자 제한
            if len(user_name.current) < 8:
                user_name.current += key
                name_input.current.value = user_name.current
                page.update()

    name_input = ft.Ref[ft.TextField]()

    def create_page2():
        # 배경 이미지와 코드로 그린 키보드를 스택으로 배치

        # QWERTY 키보드 레이아웃
        keys_layout = [
            # 첫 번째 행 (QWERTYUIOP)
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            # 두 번째 행 (ASDFGHJKL)
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            # 세 번째 행 (ZXCVBNM)
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
        ]

        keyboard_buttons = []

        # 키보드 시작 위치와 크기
        key_start_x = 30
        key_start_y = 1030
        key_width = 95
        key_height = 95
        key_spacing = 8
        row_spacing = 10

        # 키 버튼 생성 함수
        def create_key_button(letter, x, y, width=key_width, height=key_height):
            return ft.Container(
                content=ft.Text(letter, size=24, color="#333333", weight=ft.FontWeight.BOLD),
                left=x,
                top=y,
                width=width,
                height=height,
                bgcolor="white",
                border_radius=10,
                alignment=ft.alignment.center,
                on_click=lambda e, key=letter: on_keyboard_key_press(key),
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=3,
                    color=ft.Colors.BLUE_GREY_100,
                    offset=ft.Offset(0, 2),
                ),
            )

        # 각 행의 키 버튼 생성
        for row_idx, row in enumerate(keys_layout):
            # 두 번째 행(ASDFGHJKL)은 약간 오른쪽으로 시프트하여 중앙 정렬
            offset_x = 0
            if row_idx == 1:  # A 행
                offset_x = 50
            elif row_idx == 2:  # Z 행
                offset_x = 100

            for col_idx, letter in enumerate(row):
                x = key_start_x + offset_x + (col_idx * (key_width + key_spacing))
                y = key_start_y + (row_idx * (key_height + row_spacing))
                keyboard_buttons.append(create_key_button(letter, x, y))

        # 세 번째 행 - 백스페이스 버튼 (ZXCVBNM 다음)
        backspace_x = key_start_x + 100 + (7 * (key_width + key_spacing))
        backspace_y = key_start_y + (2 * (key_height + row_spacing))
        keyboard_buttons.append(
            ft.Container(
                content=ft.Text("←", size=28, color="white", weight=ft.FontWeight.BOLD),
                left=backspace_x,
                top=backspace_y,
                width=key_width * 2 + key_spacing,
                height=key_height,
                bgcolor="#ffcc00",
                border_radius=10,
                alignment=ft.alignment.center,
                on_click=lambda e: on_keyboard_key_press("BACK"),
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=3,
                    color=ft.Colors.BLUE_GREY_100,
                    offset=ft.Offset(0, 2),
                ),
            )
        )

        # 네 번째 행 - 스페이스바와 ENTER 버튼
        space_bar_x = 30
        space_bar_y = key_start_y + (3 * (key_height + row_spacing))
        space_bar_width = 785

        enter_x = space_bar_x + space_bar_width + key_spacing
        enter_width = 225

        keyboard_buttons.append(
            ft.Container(
                content=ft.Text("SPACE", size=20, color="#666666", weight=ft.FontWeight.BOLD),
                left=space_bar_x,
                top=space_bar_y,
                width=space_bar_width,
                height=key_height,
                bgcolor="white",
                border_radius=10,
                alignment=ft.alignment.center,
                on_click=lambda e: on_keyboard_key_press(" "),
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=3,
                    color=ft.Colors.BLUE_GREY_100,
                    offset=ft.Offset(0, 2),
                ),
            )
        )

        keyboard_buttons.append(
            ft.Container(
                content=ft.Text("ENTER", size=20, color="white", weight=ft.FontWeight.BOLD),
                left=enter_x,
                top=space_bar_y,
                width=enter_width,
                height=key_height,
                bgcolor="#4dabf7",
                border_radius=10,
                alignment=ft.alignment.center,
                on_click=lambda e: on_keyboard_key_press("ENTER"),
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=3,
                    color=ft.Colors.BLUE_200,
                    offset=ft.Offset(0, 2),
                ),
            )
        )

        # 입력창과 버튼 위치
        input_x = 185
        input_y = 500
        input_width = 700

        button_x = 285
        button_y = 635
        button_width = 500

        return ft.Container(
            content=ft.Stack([
                # 배경 이미지
                ft.Image(
                    src="design/2_Screen_IMG.png",
                    width=1080,
                    height=1920,
                    fit=ft.ImageFit.FILL,
                ),
                # 입력창
                ft.Container(
                    content=ft.TextField(
                        ref=name_input,
                        value=user_name.current,
                        text_align=ft.TextAlign.CENTER,
                        text_size=32,
                        border_color="#b8c5e0",
                        bgcolor="white",
                        border_radius=30,
                        read_only=True,
                        height=80,
                    ),
                    left=input_x,
                    top=input_y,
                    width=input_width,
                ),
                # "이름 첫글자 쓰기" 버튼
                ft.Container(
                    content=ft.Container(
                        content=ft.Text("이름 첫글자 쓰기", size=24, color="white", weight=ft.FontWeight.BOLD),
                        bgcolor="#a8c5e8",
                        border_radius=38,
                        alignment=ft.alignment.center,
                    ),
                    left=button_x,
                    top=button_y,
                    width=button_width,
                    height=75,
                ),
                # 타임아웃 카운트다운 표시 (우측 상단)
                ft.Container(
                    content=ft.Text(
                        ref=timeout_display_page2,
                        value=f"{remaining_seconds.current}초",
                        size=32,
                        color="white",
                        weight=ft.FontWeight.BOLD,
                    ),
                    right=20,
                    top=20,
                    bgcolor="#ff5252",
                    padding=ft.padding.all(15),
                    border_radius=10,
                ),
                # 코드로 그린 키보드 버튼들
                *keyboard_buttons,
            ]),
            width=1080,
            height=1920,
        )

    # ==================== Page 3: 아이콘 선택 ====================

    def send_to_server(nickname, pattern_number, timestamp):
        """FastAPI 서버로 QR 발급 데이터 전송"""
        try:
            data = {
                "nickname": nickname,
                "pattern_number": pattern_number,
                "timestamp": timestamp
            }
            response = requests.post(
                f"{FASTAPI_SERVER_URL}/register",
                json=data,
                timeout=5
            )
            response.raise_for_status()
            print(f"서버 전송 성공: {data}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"서버 전송 실패: {e}")
            return False

    def on_icon_select(index):
        # 중복 클릭 방지
        if processing_selection.current:
            print("이미 처리 중입니다. 중복 클릭 무시")
            return

        processing_selection.current = True
        reset_timeout()  # 아이콘 선택 시 타임아웃 리셋
        selected_icon.current = index

        # 패턴 번호 가져오기
        pattern_number = icon_pattern_map.get(index, "00")

        # 타임스탬프 생성 (yyyy-mm-dd-hh-mm)
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")

        print(f"아이콘 선택: {index}, 패턴: {pattern_number}, 닉네임: {user_name.current}")

        # FastAPI 서버로 데이터 전송 (별도 스레드에서)
        def send_data():
            send_to_server(user_name.current, pattern_number, timestamp)

        threading.Thread(target=send_data, daemon=True).start()

        # 페이지 전환
        current_page.current = 3
        update_page()

    def create_page3():
        # 배경 이미지 위에 10개의 아이콘 버튼 배치
        # 5행 2열 그리드 형태로 배치
        icon_buttons = []

        # 아이콘 위치 계산 (5행 2열)
        start_x = 90  # 왼쪽 열 시작 위치
        start_y = 330  # 첫 행 시작 위치
        spacing_x = 540  # 열 간격
        spacing_y = 220  # 행 간격
        button_size = 360  # 버튼 크기

        for i in range(10):
            row = i // 2  # 행 번호 (0-4)
            col = i % 2   # 열 번호 (0-1)

            icon_buttons.append(
                ft.Container(
                    content=ft.Image(
                        src=f"design/IMGButton_PNG2/3_Screen_UI_{i+1}.png",
                        width=button_size,
                        height=button_size,
                        fit=ft.ImageFit.CONTAIN,
                    ),
                    left=start_x + (col * spacing_x),
                    top=start_y + (row * spacing_y),
                    width=button_size,
                    height=button_size,
                    on_click=lambda e, idx=i: on_icon_select(idx),
                )
            )

        return ft.Container(
            content=ft.Stack([
                # 배경 이미지
                ft.Image(
                    src="design/3_Screen_IMG.png",
                    width=1080,
                    height=1920,
                    fit=ft.ImageFit.FILL,
                ),
                # 타임아웃 카운트다운 표시 (우측 상단)
                ft.Container(
                    content=ft.Text(
                        ref=timeout_display_page3,
                        value=f"{remaining_seconds.current}초",
                        size=32,
                        color="white",
                        weight=ft.FontWeight.BOLD,
                    ),
                    right=20,
                    top=20,
                    bgcolor="#ff5252",
                    padding=ft.padding.all(15),
                    border_radius=10,
                ),
                # 10개의 아이콘 버튼들
                *icon_buttons,
            ]),
            width=1080,
            height=1920,
        )

    # ==================== Page 4: 등록 완료 ====================

    def on_page4_click(e):
        """Page 4에서 화면 터치 시 즉시 첫 화면으로"""
        print("Page 4 클릭 감지 - 첫 화면으로 복귀")
        reset_to_start()

    def create_page4():
        # 4페이지 디자인 이미지 표시 (클릭 시 즉시 첫 화면으로)
        return ft.Container(
            content=ft.Image(
                src="design/4_Screen_View.png",
                width=1080,
                height=1920,
                fit=ft.ImageFit.FILL,
            ),
            width=1080,
            height=1920,
            on_click=on_page4_click,
        )

    # ==================== 페이지 전환 ====================

    content_container = ft.Ref[ft.Container]()

    def update_page():
        pages = [create_page1(), create_page2(), create_page3(), create_page4()]
        content_container.current.content = pages[current_page.current]
        page.update()

        # Page 4에 도달하면 10초 후 자동으로 Page 1로 돌아가기
        if current_page.current == 3:
            def auto_return():
                time.sleep(10)  # 10초 대기
                processing_selection.current = False  # 리셋
                current_page.current = 0
                user_name.current = ""  # 상태 초기화
                selected_icon.current = None
                try:
                    page.run_task(update_page)
                except Exception as e:
                    print(f"자동 복귀 오류: {e}")
                    traceback.print_exc()

            threading.Thread(target=auto_return, daemon=True).start()

    # 초기 화면 설정
    page.add(
        ft.Container(
            ref=content_container,
            content=create_page1(),
            width=1080,
            height=1920,
        )
    )

    # 타임아웃 모니터 시작
    start_timeout_monitor()

ft.app(target=main)
