# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an inventory kiosk application built with Python and Flet (Python UI framework). The application is a touch-screen registration system that allows users to:
1. Enter their nickname (max 8 characters)
2. Select an icon from 10 options
3. Receive a QR code label printed via a network-connected barcode printer

The system communicates with a FastAPI backend server to trigger label printing.

## Technology Stack

- **Python**: Primary language
- **Flet**: UI framework for building interactive kiosk interfaces (cross-platform Flutter-based Python framework)
- **requests**: HTTP client for FastAPI server communication
- **Threading**: For timeout monitoring and auto-return functionality
- **Target Platform**: Windows 11 (fullscreen portrait mode)
- **Backend**: FastAPI server at `http://192.168.50.122:8001`

## Running the Application

To run the main kiosk application:
```bash
python main.py
```

This launches the full-screen portrait mode (1080 x 1920) kiosk with all 4 pages.

To run the keyboard test interface:
```bash
python keyboard_test.py
```

This launches a Flet application demonstrating a virtual numeric keypad with input validation (10-character limit).

## Code Architecture

### UI Component Pattern

The codebase follows Flet's declarative UI pattern:

1. **Page Setup**: Configure page properties (title, alignment, colors) in the `main(page: ft.Page)` function
2. **State Management**: UI state stored in widget properties (e.g., `TextField.value`)
3. **Event Handlers**: Click handlers defined as nested functions that update state and call `page.update()`
4. **Component Factory Functions**: Reusable UI elements created via factory functions (e.g., `create_button()`)
5. **Layout Structure**: Nested `Container`, `Column`, and `Row` widgets for positioning

### Application Flow

The main kiosk application ([main.py](main.py)) implements a 4-page registration flow:

1. **Page 1 - Main Menu** ([create_page1](main.py)):
   - Background image: `design/1_Screen_IMG.png`
   - Single clickable button: `design/1_Screen_UI.png` ("시작할게요")
   - Button positioned at bottom center
   - No timeout on this page

2. **Page 2 - Nickname Input** ([create_page2](main.py)):
   - Background image: `design/2_Screen_IMG.png`
   - Text input field (max 8 English characters)
   - Programmatically drawn QWERTY virtual keyboard
   - Keyboard layout:
     - Row 1: Q W E R T Y U I O P (10 keys)
     - Row 2: A S D F G H J K L (9 keys, offset for visual centering)
     - Row 3: Z X C V B N M + Backspace (7 letters + yellow backspace button)
     - Row 4: Extended Space bar + Blue ENTER button
   - Timeout countdown displayed in top-right corner (red badge)
   - **Timeout: 120 seconds** - returns to Page 1 if no input

3. **Page 3 - Icon Selection** ([create_page3](main.py)):
   - Background image: `design/3_Screen_IMG.png`
   - 5x2 grid of 10 icon buttons from `design/IMGButton_PNG2/3_Screen_UI_1.png` through `3_Screen_UI_10.png`
   - Each icon mapped to unique pattern number:
     - Row 1: 13, 05
     - Row 2: 20, 07
     - Row 3: 01, 17
     - Row 4: 18, 02
     - Row 5: 12, 06
   - Upon selection, sends data to FastAPI server
   - Timeout countdown displayed in top-right corner
   - **Timeout: 120 seconds** - returns to Page 1 if no selection

4. **Page 4 - Registration Complete** ([create_page4](main.py)):
   - Displays: `design/4_Screen_View.png`
   - Auto-returns to Page 1 after 10 seconds
   - No timeout countdown displayed

### State Management Pattern

- Uses `ft.Ref` for reactive state variables:
  - `current_page`: Current page number (0-3)
  - `user_name`: User's input nickname
  - `selected_icon`: Selected icon index
  - `last_interaction_time`: Timestamp for timeout tracking
  - `remaining_seconds`: Countdown timer value
  - `timeout_display_page2`, `timeout_display_page3`: Text widgets for countdown display
- Page transitions triggered by user interactions (button clicks, keyboard input)
- Single `update_page()` function handles all page transitions by swapping content in main container
- Timeout monitoring runs in background thread

### Timeout Management

**Configuration Variable** ([main.py:24](main.py#L24)):
```python
TIMEOUT_SECONDS = 120  # 2 minutes - easily adjustable
```

**Features**:
- Monitors Pages 2 and 3 only (not Page 1 or 4)
- Countdown displayed in top-right corner with red background
- Timer resets on any user interaction:
  - Keyboard key press
  - Icon selection
  - Page navigation
- Auto-returns to Page 1 when timeout expires
- Background thread updates display every second

**Implementation** ([main.py:83-102](main.py#L83-L102)):
- `timeout_monitor()`: Background thread checking elapsed time
- `reset_timeout()`: Resets timer to 120 seconds
- `reset_to_start()`: Returns to Page 1 and clears all state
- `update_timeout_display()`: Updates countdown text on both pages

### FastAPI Server Integration

**Configuration** ([main.py:27](main.py#L27)):
```python
FASTAPI_SERVER_URL = "http://192.168.50.122:8001"
```

**Data Transmission** ([main.py:388-405](main.py#L388-L405)):

When user selects an icon on Page 3, the system sends POST request to `/register` endpoint:

```json
{
  "nickname": "UserNick",
  "pattern_number": "13",
  "timestamp": "2025-12-07-14-30"
}
```

- `nickname`: User's input from Page 2 (max 8 characters)
- `pattern_number`: Icon's unique pattern number (13, 05, 20, 07, 01, 17, 18, 02, 12, 06)
- `timestamp`: Current time in `yyyy-mm-dd-hh-mm` format

The FastAPI server receives this data and triggers barcode printer to print QR label.

**Icon Pattern Mapping** ([main.py:30-41](main.py#L30-L41)):
```python
icon_pattern_map = {
    0: "13",  # Row 1 left
    1: "05",  # Row 1 right
    2: "20",  # Row 2 left
    3: "07",  # Row 2 right
    4: "01",  # Row 3 left
    5: "17",  # Row 3 right
    6: "18",  # Row 4 left
    7: "02",  # Row 4 right
    8: "12",  # Row 5 left
    9: "06",  # Row 5 right
}
```

### Current Components

- **QWERTY Keyboard** ([main.py:167-315](main.py#L167-L315)): Full alphabetic keyboard for name input
  - Programmatically drawn with `ft.Container` widgets (not using image overlay)
  - Standard QWERTY layout with visual offset for centering
  - White keys with shadow effects
  - Color-coded special buttons:
    - Yellow backspace button (←)
    - Blue ENTER button
    - White space bar
  - Integrated into Page 2 of main flow
  - Each key calls `on_keyboard_key_press()` and resets timeout

- **Virtual Keyboard Test** ([keyboard_test.py](keyboard_test.py)): Numeric keypad (legacy test file)
  - Uses `ft.Container` with shadow effects for button styling
  - Input validation limiting to 10 characters
  - Color-coded special buttons (red for clear, yellow for backspace, blue for enter)

### Design Assets

The [design/](design/) directory contains UI mockups showing a multi-screen kiosk flow:
- Screen 1-4 mockups showing the intended user journey
- Button assets in both JPG and PNG formats ([design/IMGButton_JPG2/](design/IMGButton_JPG2/), [design/IMGButton_PNG2/](design/IMGButton_PNG2/))

## Important Notes

### Window Configuration

The application runs in fullscreen portrait mode with specific settings ([main.py:10-16](main.py#L10-L16)):
```python
page.window.width = 1080
page.window.height = 1920
page.window.left = 0        # Position at screen origin
page.window.top = 0         # Prevents window background showing
page.window.resizable = False
page.window.title_bar_hidden = True
page.window.frameless = True
```

### Flet API Conventions

- Use `ft.Colors` (capital C) for color constants, not `ft.colors`
- Use `ft.Icons` (capital I) for icon constants
- Update the UI by calling `page.update()` after state changes
- Set `read_only=True` on TextFields when using virtual keyboard input to prevent physical keyboard interference
- Use `ft.Stack` for layered UI elements (background images + interactive components)

### Configuration Variables

Easily adjustable settings at the top of `main()` function:

1. **Timeout Duration** ([main.py:24](main.py#L24)):
   ```python
   TIMEOUT_SECONDS = 120  # Change this to adjust timeout
   ```

2. **Server URL** ([main.py:27](main.py#L27)):
   ```python
   FASTAPI_SERVER_URL = "http://192.168.50.122:8001"
   ```

3. **Icon Pattern Mapping** ([main.py:30-41](main.py#L30-L41)):
   - Modify pattern numbers if icon assignment changes

### Development Considerations

- When building new screens, reference the design mockups in the `design/` directory to maintain UI consistency
- All user interactions on Pages 2 and 3 should call `reset_timeout()` to reset the inactivity timer
- The keyboard is drawn programmatically (not image-based) to allow visual feedback and customization
- Background thread for timeout monitoring is daemon thread - automatically terminates when app closes
- Server communication errors are logged to console but don't block UI

### Troubleshooting

**If timeout doesn't work:**
- Check that `start_timeout_monitor()` is called during initialization
- Verify `current_page.current` values (1 for Page 2, 2 for Page 3)
- Check console for timeout messages

**If server communication fails:**
- Verify FastAPI server is running at `http://192.168.50.122:8001`
- Check network connectivity
- Look for error messages in console output
- Test endpoint with: `curl -X POST http://192.168.50.122:8001/register -H "Content-Type: application/json" -d '{"nickname":"test","pattern_number":"13","timestamp":"2025-01-01-12-00"}'`
