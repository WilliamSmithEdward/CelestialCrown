import pygame

from src.strategy import MapDef, MapRenderer


def test_animated_path_points_include_padding() -> None:
    map_def = MapDef.from_dict(
        {
            "width": 1280,
            "height": 720,
            "layers": [
                {"id": "base", "terrain": "grass", "type": "fill"},
                {
                    "id": "river_main",
                    "terrain": "river",
                    "type": "path",
                    "points": [[180, 60], [260, 160], [310, 300], [380, 420], [460, 520], [560, 640], [680, 720]],
                },
            ],
        }
    )

    renderer = MapRenderer(map_def, pygame)
    renderer.bake(1280, 720)

    pts = renderer._smoothed["river_main"]

    assert min(x for x, _ in pts) >= renderer._pad_x
    assert min(y for _, y in pts) >= renderer._pad_y
    assert max(x for x, _ in pts) <= renderer._pad_x + renderer._map_w
    assert max(y for _, y in pts) <= renderer._pad_y + renderer._map_h


def test_void_background_renders_when_no_bake() -> None:
    map_def = MapDef.from_dict({"width": 1280, "height": 720, "layers": []})
    renderer = MapRenderer(map_def, pygame)
    screen = pygame.Surface((320, 180))

    renderer.render(screen, 0.75)

    px = screen.get_at((4, 4))
    assert (px.r, px.g, px.b) != (0, 0, 0)


def test_shooting_star_spawn_point_is_in_visible_void() -> None:
    map_def = MapDef.from_dict({"width": 1280, "height": 720, "layers": [{"id": "base", "terrain": "grass", "type": "fill"}]})
    renderer = MapRenderer(map_def, pygame)
    renderer.bake(1280, 720)

    # Move camera so part of the map is visible and part is void.
    renderer.set_camera(220.0, 140.0)
    pt = renderer._random_visible_void_point(1280, 720)

    assert pt is not None
    x, y = pt
    map_left = renderer._pad_x - renderer._cam_x
    map_top = renderer._pad_y - renderer._cam_y
    map_right = map_left + renderer._map_w
    map_bottom = map_top + renderer._map_h
    assert not (map_left <= x <= map_right and map_top <= y <= map_bottom)
