import pygame

from src.states.battle import BattleState
import src.states.battle as battle_mod


def test_camera_has_scroll_room_after_resource_init() -> None:
    battle = BattleState()
    screen = pygame.Surface((1280, 720))

    battle.render(screen)

    assert battle._cam_max_x > 0
    assert battle._cam_max_y > 0
    assert battle._zoom == 0.95
    assert battle._zoom_target == 0.95


def test_camera_scrolls_while_paused_near_edge(monkeypatch) -> None:
    battle = BattleState()
    screen = pygame.Surface((1280, 720))
    battle.render(screen)
    battle.paused = True

    old_x = battle._cam_x
    monkeypatch.setattr(battle_mod.pygame.mouse, "get_pos", lambda: (1279, 300))

    battle.update(0.25)

    assert battle._scroll_flags[1] is True
    assert battle._cam_x > old_x


def test_scroll_flags_clear_when_mouse_is_centered(monkeypatch) -> None:
    battle = BattleState()
    screen = pygame.Surface((1280, 720))
    battle.render(screen)

    monkeypatch.setattr(battle_mod.pygame.mouse, "get_pos", lambda: (640, 300))

    battle.update(0.05)

    assert battle._scroll_flags == [False, False, False, False]


def test_mouse_wheel_changes_zoom_and_rebakes() -> None:
    battle = BattleState()
    screen = pygame.Surface((1280, 720))
    battle.render(screen)

    old_zoom = battle._zoom
    old_max_x = battle._cam_max_x
    evt = pygame.event.Event(pygame.MOUSEWHEEL, {"x": 0, "y": -1})

    battle.handle_event(evt)
    for _ in range(35):
        battle.update(1.0 / 60.0)

    assert battle._zoom_visual < old_zoom
    assert battle._zoom_target < old_zoom
    assert battle._cam_max_x != old_max_x


def test_edge_scroll_speed_is_fast(monkeypatch) -> None:
    battle = BattleState()
    screen = pygame.Surface((1280, 720))
    battle.render(screen)
    battle._cam_x = 0.0

    monkeypatch.setattr(battle_mod.pygame.mouse, "get_pos", lambda: (1279, 300))
    battle.update(1.0)

    assert battle._cam_x > 300.0


def test_initial_camera_centers_player_base() -> None:
    battle = BattleState()
    screen = pygame.Surface((1280, 720))
    battle.render(screen)

    base = battle.mission.sites["player_base"]
    sx, sy = battle._p(base.x, base.y)
    # Base should start near the viewport center.
    assert abs(sx - 640) <= 8
    assert abs(sy - 333) <= 8
