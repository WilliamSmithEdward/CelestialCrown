"""Main game engine - handles initialization, state management, and main loop"""

from typing import TYPE_CHECKING, Optional
import os
import ctypes

try:
    import pygame  # type: ignore
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

if TYPE_CHECKING:
    import pygame  # type: ignore

from .gamestate import GameState
from ..config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE, DISPLAY_MODE,
    COLOR_BLACK
)


class GameEngine:
    """Main game engine responsible for game loop and state management"""

    @staticmethod
    def _get_monitor_refresh_rate() -> int:
        """Best-effort monitor refresh rate detection on Windows."""
        class DEVMODEW(ctypes.Structure):
            _fields_ = [
                ("dmDeviceName", ctypes.c_wchar * 32),
                ("dmSpecVersion", ctypes.c_ushort),
                ("dmDriverVersion", ctypes.c_ushort),
                ("dmSize", ctypes.c_ushort),
                ("dmDriverExtra", ctypes.c_ushort),
                ("dmFields", ctypes.c_ulong),
                ("dmOrientation", ctypes.c_short),
                ("dmPaperSize", ctypes.c_short),
                ("dmPaperLength", ctypes.c_short),
                ("dmPaperWidth", ctypes.c_short),
                ("dmScale", ctypes.c_short),
                ("dmCopies", ctypes.c_short),
                ("dmDefaultSource", ctypes.c_short),
                ("dmPrintQuality", ctypes.c_short),
                ("dmColor", ctypes.c_short),
                ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short),
                ("dmCollate", ctypes.c_short),
                ("dmFormName", ctypes.c_wchar * 32),
                ("dmLogPixels", ctypes.c_ushort),
                ("dmBitsPerPel", ctypes.c_ulong),
                ("dmPelsWidth", ctypes.c_ulong),
                ("dmPelsHeight", ctypes.c_ulong),
                ("dmDisplayFlags", ctypes.c_ulong),
                ("dmDisplayFrequency", ctypes.c_ulong),
                ("dmICMMethod", ctypes.c_ulong),
                ("dmICMIntent", ctypes.c_ulong),
                ("dmMediaType", ctypes.c_ulong),
                ("dmDitherType", ctypes.c_ulong),
                ("dmReserved1", ctypes.c_ulong),
                ("dmReserved2", ctypes.c_ulong),
                ("dmPanningWidth", ctypes.c_ulong),
                ("dmPanningHeight", ctypes.c_ulong),
            ]

        if os.name != "nt":
            return 0

        ENUM_CURRENT_SETTINGS = -1
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        try:
            ok = ctypes.windll.user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm))
            if ok and 30 <= int(dm.dmDisplayFrequency) <= 360:
                return int(dm.dmDisplayFrequency)
        except Exception:
            return 0
        return 0
    
    def __init__(self):
        """Initialize the game engine"""
        if not PYGAME_AVAILABLE:
            raise ImportError(
                "Pygame is not installed. Install it with: pip install pygame\n"
                "Note: Python 3.14 may not have pygame wheels. Use Python 3.11-3.13 for full support."
            )
        
        # Keep window centered when using windowed mode.
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        pygame.init()
        self.use_vsync = True
        self.target_fps = FPS
        monitor_refresh = self._get_monitor_refresh_rate()
        self.aspect_ratio = SCREEN_WIDTH / SCREEN_HEIGHT

        if DISPLAY_MODE == "fullscreen":
            try:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN, vsync=1)
            except TypeError:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        else:
            # Use desktop bounds so the window is not cut off by the taskbar.
            desktop_info = pygame.display.Info()
            desktop_w = desktop_info.current_w
            desktop_h = desktop_info.current_h
            taskbar_safety_margin = 72

            max_w = min(SCREEN_WIDTH, max(1024, desktop_w - 120))
            max_h = min(SCREEN_HEIGHT, max(720, desktop_h - taskbar_safety_margin))

            # Preserve the game's native aspect ratio in windowed mode.
            if max_w / max_h > self.aspect_ratio:
                window_h = max_h
                window_w = int(window_h * self.aspect_ratio)
            else:
                window_w = max_w
                window_h = int(window_w / self.aspect_ratio)

            # RESIZABLE keeps the standard OS title bar (minimize/maximize/close).
            try:
                self.screen = pygame.display.set_mode((window_w, window_h), pygame.RESIZABLE, vsync=1)
            except TypeError:
                self.screen = pygame.display.set_mode((window_w, window_h), pygame.RESIZABLE)

            # In windowed mode, pace updates to monitor refresh when known.
            if monitor_refresh > 0:
                self.target_fps = monitor_refresh
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.is_paused = False
        self.render_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.controllers: dict[int, pygame.joystick.JoystickType] = {}
        self.controller_device_added_event = getattr(pygame, "CONTROLLERDEVICEADDED", None)
        self.controller_device_removed_event = getattr(pygame, "CONTROLLERDEVICEREMOVED", None)
        self._init_controllers()
        
        # State management
        self.current_state: Optional[GameState] = None
        self.state_stack: list[GameState] = []
        
        # Frame tracking
        self.frame_count = 0
        self.delta_time = 0.0
        self.smoothed_delta_time = 1.0 / max(30, self.target_fps)

    def _init_controllers(self) -> None:
        """Initialize connected game controllers and enable hot-plug support."""
        try:
            pygame.joystick.init()
            for device_index in range(pygame.joystick.get_count()):
                joystick = pygame.joystick.Joystick(device_index)
                joystick.init()
                self.controllers[joystick.get_instance_id()] = joystick
        except Exception:
            self.controllers = {}

    def _add_controller(self, device_index: int) -> None:
        """Register a newly connected controller."""
        try:
            joystick = pygame.joystick.Joystick(device_index)
            joystick.init()
            self.controllers[joystick.get_instance_id()] = joystick
        except Exception:
            pass

    def _remove_controller(self, instance_id: int) -> None:
        """Forget a disconnected controller instance."""
        joystick = self.controllers.pop(instance_id, None)
        if joystick is not None:
            try:
                joystick.quit()
            except Exception:
                pass
        
    def change_state(self, new_state: GameState) -> None:
        """Replace current state with a new one"""
        if self.current_state:
            self.current_state.on_exit()
        self.current_state = new_state
        self.current_state.on_enter()
        
    def push_state(self, new_state: GameState) -> None:
        """Push state onto stack (pause current, activate new)"""
        if self.current_state:
            self.current_state.on_pause()
            self.state_stack.append(self.current_state)
        self.current_state = new_state
        self.current_state.on_enter()
        
    def pop_state(self) -> None:
        """Pop state from stack (resume previous state)"""
        if self.current_state:
            self.current_state.on_exit()
        
        if self.state_stack:
            self.current_state = self.state_stack.pop()
            self.current_state.on_resume()
        else:
            self.running = False
            
    def handle_events(self) -> None:
        """Handle all pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                # Do not recreate display mode on every drag step; this can freeze on some systems.
                # Pygame 2 keeps the resizable display surface live-updated.
                pass
            elif event.type == pygame.WINDOWSIZECHANGED:
                pass
            elif event.type == pygame.JOYDEVICEADDED:
                self._add_controller(event.device_index)
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._remove_controller(event.instance_id)
            elif self.controller_device_added_event is not None and event.type == self.controller_device_added_event:
                device_index = getattr(event, "device_index", None)
                if device_index is not None:
                    self._add_controller(device_index)
            elif self.controller_device_removed_event is not None and event.type == self.controller_device_removed_event:
                instance_id = getattr(event, "instance_id", None)
                if instance_id is not None:
                    self._remove_controller(instance_id)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    
            # Pass event to current state
            if self.current_state:
                self.current_state.handle_event(event)
                
    def update(self) -> None:
        """Update game logic"""
        if not self.is_paused and self.current_state:
            self.current_state.update(self.delta_time)
            
    def render(self) -> None:
        """Render frame"""
        # Letterbox to preserve game aspect ratio in any window size.
        window_w, window_h = self.screen.get_size()
        if window_w <= 0 or window_h <= 0:
            return

        scale = min(window_w / SCREEN_WIDTH, window_h / SCREEN_HEIGHT)
        target_w = max(1, int(SCREEN_WIDTH * scale))
        target_h = max(1, int(SCREEN_HEIGHT * scale))
        offset_x = (window_w - target_w) // 2
        offset_y = (window_h - target_h) // 2

        # Render directly at target size to avoid expensive per-frame full-scene scaling.
        target_size = (target_w, target_h)
        if self.render_surface.get_size() != target_size:
            self.render_surface = pygame.Surface(target_size)

        self.render_surface.fill(COLOR_BLACK)
        if self.current_state:
            self.current_state.render(self.render_surface)

        self.screen.fill(COLOR_BLACK)
        self.screen.blit(self.render_surface, (offset_x, offset_y))

        pygame.display.flip()
        
    def run(self) -> None:
        """Main game loop"""
        while self.running:
            if self.use_vsync:
                # When vsync is active, avoid an additional software cap to reduce pacing jitter.
                raw_dt = self.clock.tick(0) / 1000.0
            elif self.target_fps > 0:
                raw_dt = self.clock.tick_busy_loop(self.target_fps) / 1000.0
            else:
                raw_dt = self.clock.tick() / 1000.0

            # Clamp large spikes for smoother animation after focus changes.
            raw_dt = min(raw_dt, 1.0 / 20.0)

            # Low-pass filter frame time to reduce visible jitter.
            alpha = 0.35
            self.smoothed_delta_time = (1.0 - alpha) * self.smoothed_delta_time + alpha * raw_dt
            self.delta_time = self.smoothed_delta_time
            
            self.handle_events()
            self.update()
            self.render()
            
            self.frame_count += 1
            
        self.quit()
        
    def quit(self) -> None:
        """Clean up and exit"""
        for instance_id in list(self.controllers.keys()):
            self._remove_controller(instance_id)
        try:
            pygame.joystick.quit()
        except Exception:
            pass
        pygame.quit()
