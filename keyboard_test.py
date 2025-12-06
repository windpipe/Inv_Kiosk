import flet as ft

def main(page: ft.Page):
    page.title = "Kiosk Virtual Keyboard"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#f0f4fa"

    # 1. 입력창
    txt_input = ft.TextField(
        value="",
        text_align=ft.TextAlign.CENTER,
        width=300,
        text_size=30,
        read_only=True,
        border_color="transparent",
        bgcolor="white",
        border_radius=15,
    )

    # 2. 키 입력 로직
    def on_key_click(e):
        key = e.control.data
        
        if key == "CLEAR":
            txt_input.value = ""
        elif key == "BACK":
            txt_input.value = txt_input.value[:-1]
        elif key == "ENTER":
            print(f"전송할 데이터: {txt_input.value}")
            page.snack_bar = ft.SnackBar(ft.Text(f"입력 완료: {txt_input.value}"))
            page.snack_bar.open = True
            txt_input.value = "" 
        else:
            if len(txt_input.value) < 10:
                txt_input.value += str(key)
        
        page.update()

    # 3. 버튼 생성 (수정된 부분: ft.Colors 사용)
    def create_button(text, color="#ffffff", text_color="#333333", data=None):
        return ft.Container(
            content=ft.Text(text, size=24, weight=ft.FontWeight.BOLD, color=text_color),
            width=80,
            height=80,
            bgcolor=color,
            border_radius=10,
            alignment=ft.alignment.center,
            on_click=on_key_click,
            data=data if data else text,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=5,
                # 여기를 수정했습니다: ft.colors -> ft.Colors
                color=ft.Colors.BLUE_GREY_100, 
                offset=ft.Offset(2, 2),
            ),
            ink=True,
        )

    # 4. 레이아웃
    keyboard_layout = ft.Column(
        controls=[
            ft.Row([create_button("1"), create_button("2"), create_button("3")], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([create_button("4"), create_button("5"), create_button("6")], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([create_button("7"), create_button("8"), create_button("9")], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                create_button("C", color="#ff6b6b", text_color="white", data="CLEAR"),
                create_button("0"),
                create_button("←", color="#ffcc00", text_color="white", data="BACK")
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=10),
            ft.Row([
                ft.Container(
                    content=ft.Text("입력 완료", size=20, color="white", weight=ft.FontWeight.BOLD),
                    width=260, height=60, bgcolor="#4dabf7", border_radius=10,
                    alignment=ft.alignment.center, on_click=on_key_click, data="ENTER",
                    shadow=ft.BoxShadow(
                        blur_radius=5, 
                        # 여기도 수정했습니다
                        color=ft.Colors.BLUE_200, 
                        offset=ft.Offset(2, 2)
                    )
                )
            ], alignment=ft.MainAxisAlignment.CENTER)
        ],
        spacing=10
    )

    page.add(
        ft.Column([
            txt_input,
            ft.Container(height=20),
            keyboard_layout
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

ft.app(target=main)