"""Map pygame events to high-level input actions."""

from typing import Optional

import pygame

from .actions import InputAction


class InputMapper:
    """Translate keyboard/controller events into input actions."""

    def __init__(self, deadzone: float = 0.45):
        self.deadzone = deadzone
        self._axis_armed = True
        self._controller_motion_event = getattr(pygame, "CONTROLLERAXISMOTION", None)
        self._controller_button_event = getattr(pygame, "CONTROLLERBUTTONDOWN", None)
        self._controller_axis_left_y = getattr(pygame, "CONTROLLER_AXIS_LEFTY", 1)
        self._controller_button_a = getattr(pygame, "CONTROLLER_BUTTON_A", 0)
        self._controller_button_start = getattr(pygame, "CONTROLLER_BUTTON_START", 6)
        self._controller_button_b = getattr(pygame, "CONTROLLER_BUTTON_B", 1)
        self._controller_button_dpad_up = getattr(pygame, "CONTROLLER_BUTTON_DPAD_UP", 11)
        self._controller_button_dpad_down = getattr(pygame, "CONTROLLER_BUTTON_DPAD_DOWN", 12)

    def map_event(self, event: pygame.event.Event) -> Optional[InputAction]:
        """Return an action for the given event, if any."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                return InputAction.NAV_UP
            if event.key == pygame.K_DOWN:
                return InputAction.NAV_DOWN
            if event.key == pygame.K_RETURN:
                return InputAction.CONFIRM
            if event.key == pygame.K_ESCAPE:
                return InputAction.CANCEL

        if event.type == pygame.JOYHATMOTION:
            _, hat_y = event.value
            if hat_y > 0:
                return InputAction.NAV_UP
            if hat_y < 0:
                return InputAction.NAV_DOWN

        if event.type == pygame.JOYAXISMOTION and event.axis == 1:
            return self._axis_to_action(event.value)

        if event.type == pygame.JOYBUTTONDOWN:
            if event.button in (0, 7):
                return InputAction.CONFIRM
            if event.button in (11, 13):
                return InputAction.NAV_UP
            if event.button in (12, 14):
                return InputAction.NAV_DOWN
            if event.button == 1:
                return InputAction.CANCEL

        if self._controller_motion_event is not None and event.type == self._controller_motion_event:
            if event.axis == self._controller_axis_left_y:
                return self._axis_to_action(event.value)

        if self._controller_button_event is not None and event.type == self._controller_button_event:
            if event.button in (self._controller_button_a, self._controller_button_start):
                return InputAction.CONFIRM
            if event.button == self._controller_button_dpad_up:
                return InputAction.NAV_UP
            if event.button == self._controller_button_dpad_down:
                return InputAction.NAV_DOWN
            if event.button == self._controller_button_b:
                return InputAction.CANCEL

        return None

    def _axis_to_action(self, value: float) -> Optional[InputAction]:
        if abs(value) < self.deadzone:
            self._axis_armed = True
            return None
        if self._axis_armed:
            self._axis_armed = False
            return InputAction.NAV_DOWN if value > 0 else InputAction.NAV_UP
        return None
