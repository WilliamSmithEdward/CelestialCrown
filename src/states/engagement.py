"""Dedicated tactical engagement state for squad clashes."""

from __future__ import annotations

import math
import random
from typing import Callable, Optional

from ._shared import PYGAME_AVAILABLE, pygame
from ..battle import CombatSystem
from ..core.gamestate import GameState, StateType
from ..entities import Unit
from ..strategy import EngagementReport, Squad
from ..strategy.sprite_registry import SpriteRegistry


class EngagementState(GameState):
    """Transient tactical playback state for one squad-vs-squad battle."""

    def __init__(
        self,
        squad_a: Squad,
        squad_b: Squad,
        on_complete: Optional[Callable[[EngagementReport], None]] = None,
    ):
        super().__init__()
        self.state_type = StateType.BATTLE
        self.squad_a = squad_a
        self.squad_b = squad_b
        self.on_complete = on_complete
        self.report: Optional[EngagementReport] = None
        self._elapsed = 0.0
        self._phase = "intro"
        self._action_timer = 0.55
        self._result_timer = 0.0
        self._result_hold = 1.35
        self._finished = False
        self._completion_dispatched = False

        self._start_alive_a = len(self.squad_a.alive_units())
        self._start_alive_b = len(self.squad_b.alive_units())
        self._round_number = 1
        self._max_rounds = 8
        self._turn_order: list[Unit] = []
        self._turn_index = 0

        self._last_actor_id = ""
        self._last_target_id = ""
        self._last_damage = 0
        self._last_hit = False
        self._last_critical = False
        self._combat_log = ["Engagement started."]
        self._anim_t = 0.0
        self._anim_actor_id = ""
        self._anim_target_id = ""

        self._sprites = SpriteRegistry(pygame) if PYGAME_AVAILABLE else None

        if PYGAME_AVAILABLE:
            self.title_font = pygame.font.Font(None, 64)
            self.body_font = pygame.font.Font(None, 34)
            self.small_font = pygame.font.Font(None, 28)
            self.mini_font = pygame.font.Font(None, 24)
        else:
            self.title_font = None
            self.body_font = None
            self.small_font = None
            self.mini_font = None

    def on_enter(self) -> None:
        self._start_round()

    def on_exit(self) -> None:
        pass

    def handle_event(self, event) -> None:
        if not PYGAME_AVAILABLE:
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self._finished:
                self._finish()
            else:
                # Fast-forward animation cadence while iterating combat behavior.
                self._action_timer = min(self._action_timer, 0.06)
        elif event.key == pygame.K_ESCAPE:
            self._finish()

    def _alive_a(self) -> list[Unit]:
        return [unit for unit in self.squad_a.units if unit.is_alive]

    def _alive_b(self) -> list[Unit]:
        return [unit for unit in self.squad_b.units if unit.is_alive]

    def _start_round(self) -> None:
        self._turn_order = sorted(self._alive_a() + self._alive_b(), key=lambda unit: unit.stats.agl, reverse=True)
        self._turn_index = 0
        if self._turn_order:
            self._combat_log.append(f"Round {self._round_number}.")

    def _record(self, line: str) -> None:
        self._combat_log.append(line)
        if len(self._combat_log) > 7:
            self._combat_log = self._combat_log[-7:]

    def _compute_report(self) -> EngagementReport:
        alive_a = self._alive_a()
        alive_b = self._alive_b()
        losses_a = self._start_alive_a - len(alive_a)
        losses_b = self._start_alive_b - len(alive_b)

        if len(alive_a) > len(alive_b):
            winner = self.squad_a.owner
        elif len(alive_b) > len(alive_a):
            winner = self.squad_b.owner
        else:
            winner = self.squad_a.owner if random.random() < 0.5 else self.squad_b.owner

        return EngagementReport(
            squad_a_id=self.squad_a.id,
            squad_b_id=self.squad_b.id,
            winner_owner=winner,
            rounds=self._round_number,
            losses_a=losses_a,
            losses_b=losses_b,
        )

    def _finish_combat(self) -> None:
        if self._finished:
            return
        self.report = self._compute_report()
        self._finished = True
        self._phase = "result"
        self._result_timer = 0.0
        winner = "Player" if self.report.winner_owner == 0 else "Enemy"
        self._record(f"Battle ended. Winner: {winner}.")

    def _step_combat_action(self) -> None:
        alive_a = self._alive_a()
        alive_b = self._alive_b()
        if not alive_a or not alive_b:
            self._finish_combat()
            return

        if self._round_number > self._max_rounds:
            self._finish_combat()
            return

        while self._turn_index < len(self._turn_order) and not self._turn_order[self._turn_index].is_alive:
            self._turn_index += 1

        if self._turn_index >= len(self._turn_order):
            self._round_number += 1
            self._start_round()
            if not self._turn_order:
                self._finish_combat()
            return

        actor = self._turn_order[self._turn_index]
        self._turn_index += 1
        targets = alive_b if actor in alive_a else alive_a
        if not targets:
            self._finish_combat()
            return
        target = random.choice(targets)

        damage, hit, critical = CombatSystem.execute_attack(actor, target)
        actual_damage = 0
        if hit and damage > 0:
            actual_damage = target.take_damage(damage)

        self._last_actor_id = actor.id
        self._last_target_id = target.id
        self._last_damage = actual_damage
        self._last_hit = hit
        self._last_critical = critical
        self._anim_t = 0.26
        self._anim_actor_id = actor.id
        self._anim_target_id = target.id

        if hit:
            suffix = " critical" if critical else ""
            self._record(f"{actor.name} hit {target.name} for {actual_damage}.{suffix}")
        else:
            self._record(f"{actor.name} missed {target.name}.")

        if target.is_dead():
            self._record(f"{target.name} is down.")

        if not self._alive_a() or not self._alive_b():
            self._finish_combat()

    def _finish(self) -> None:
        if self.report is not None and self.on_complete is not None and not self._completion_dispatched:
            self._completion_dispatched = True
            self.on_complete(self.report)
        if self.engine is not None:
            self.engine.pop_state()

    def update(self, delta_time: float) -> None:
        self._elapsed += max(0.0, delta_time)
        self._anim_t = max(0.0, self._anim_t - delta_time)

        if self._phase == "intro":
            if self._elapsed >= 0.35:
                self._phase = "combat"
            return

        if self._phase == "combat":
            self._action_timer -= delta_time
            if self._action_timer <= 0.0:
                self._action_timer = 0.52
                self._step_combat_action()
            return

        if self._phase == "result" and self.report is not None:
            self._result_timer += max(0.0, delta_time)
            if self._result_timer >= self._result_hold:
                self._finish()

    def _draw_unit_card(
        self,
        screen,
        unit: Unit,
        x: int,
        y: int,
        owner: int,
        role_name: str,
        facing_left: bool,
    ) -> None:
        base_w, base_h = 52, 58
        if self._sprites is not None:
            sprite = self._sprites.squad_token(owner, role_name, base_w, base_h).copy()
        else:
            sprite = pygame.Surface((base_w, base_h), pygame.SRCALPHA)
            pygame.draw.circle(sprite, (140, 170, 220), (base_w // 2, base_h // 2), 22)
        if facing_left:
            sprite = pygame.transform.flip(sprite, True, False)

        is_actor = self._anim_t > 0.0 and unit.id == self._anim_actor_id
        is_target = self._anim_t > 0.0 and unit.id == self._anim_target_id
        lunge = int(math.sin((1.0 - self._anim_t / 0.26) * math.pi) * 10) if is_actor else 0
        lunge *= 1 if not facing_left else -1
        shake = int(math.sin((1.0 - self._anim_t / 0.26) * math.pi * 7.0) * 2) if is_target and self._last_hit else 0

        draw_x = x + lunge + shake
        draw_y = y

        if not unit.is_alive:
            sprite.set_alpha(78)
        screen.blit(sprite, (draw_x, draw_y))

        if self.mini_font is not None:
            name = self.mini_font.render(unit.name, True, (234, 236, 246) if unit.is_alive else (124, 126, 138))
            screen.blit(name, (draw_x - 4, draw_y - 24))

            hp_bg = pygame.Rect(draw_x - 2, draw_y + base_h + 4, base_w + 4, 8)
            pygame.draw.rect(screen, (20, 24, 36), hp_bg, border_radius=3)
            hp_ratio = 0.0 if unit.stats.hp <= 0 else max(0.0, min(1.0, unit.current_hp / unit.stats.hp))
            hp_w = int((base_w + 2) * hp_ratio)
            hp_color = (86, 204, 116) if hp_ratio > 0.5 else ((232, 188, 72) if hp_ratio > 0.25 else (220, 92, 92))
            if hp_w > 0:
                pygame.draw.rect(screen, hp_color, (draw_x - 1, draw_y + base_h + 5, hp_w, 6), border_radius=3)

    def render(self, screen) -> None:
        if not PYGAME_AVAILABLE:
            return

        width, height = screen.get_size()
        screen.fill((10, 14, 24))

        arena_rect = pygame.Rect(70, 96, width - 140, height - 250)
        arena = pygame.Surface((arena_rect.width, arena_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(arena, (18, 26, 42, 228), arena.get_rect(), border_radius=18)
        pygame.draw.rect(arena, (178, 166, 122, 110), arena.get_rect(), 2, border_radius=18)
        screen.blit(arena, arena_rect)

        mid_y = arena_rect.top + arena_rect.height // 2 - 70
        left_x = arena_rect.left + 120
        right_x = arena_rect.right - 170

        if self.title_font is not None:
            title = self.title_font.render("Engagement", True, (244, 230, 184))
            screen.blit(title, title.get_rect(center=(width // 2, 48)))

        if self.body_font is not None:
            left_name = self.body_font.render(self.squad_a.name, True, (158, 202, 255))
            right_name = self.body_font.render(self.squad_b.name, True, (255, 164, 164))
            screen.blit(left_name, (arena_rect.left + 26, arena_rect.top + 20))
            screen.blit(right_name, (arena_rect.right - right_name.get_width() - 26, arena_rect.top + 20))

            round_s = self.body_font.render(f"Round {max(1, self._round_number)}", True, (220, 226, 236))
            screen.blit(round_s, round_s.get_rect(center=(width // 2, arena_rect.top + 40)))

        for idx, unit in enumerate(self.squad_a.units):
            self._draw_unit_card(
                screen,
                unit,
                left_x,
                mid_y + idx * 88,
                self.squad_a.owner,
                self.squad_a.role.value,
                facing_left=False,
            )

        for idx, unit in enumerate(self.squad_b.units):
            self._draw_unit_card(
                screen,
                unit,
                right_x,
                mid_y + idx * 88,
                self.squad_b.owner,
                self.squad_b.role.value,
                facing_left=True,
            )

        if self.small_font is not None:
            if self._finished and self.report is not None:
                winner = "Player" if self.report.winner_owner == 0 else "Enemy"
                status = f"Winner: {winner} | Losses {self.report.losses_a}-{self.report.losses_b}"
            elif self._last_actor_id:
                if self._last_hit:
                    tag = "CRIT " if self._last_critical else ""
                    status = f"{tag}Hit for {self._last_damage}"
                else:
                    status = "Miss"
            else:
                status = "Engagement underway..."
            status_s = self.small_font.render(status, True, (216, 224, 236))
            screen.blit(status_s, status_s.get_rect(center=(width // 2, arena_rect.bottom - 24)))

        if self.mini_font is not None:
            log_y = height - 136
            for line in self._combat_log[-3:]:
                surf = self.mini_font.render(line, True, (194, 204, 220))
                screen.blit(surf, (82, log_y))
                log_y += 30

            hint = "Enter/Space: speed up" if not self._finished else "Enter/Space/Esc: return"
            hint_s = self.mini_font.render(hint, True, (156, 176, 202))
            screen.blit(hint_s, (width - hint_s.get_width() - 84, height - 50))
