"""
game.py
=======
The Game class: owns the pygame window, the state machine, the fixed-timestep
simulation loop, and all the screens (menu, level select, HUD, pause, complete,
dead).

Why a fixed timestep?
---------------------
Ghost recordings and replays must be frame-locked to be deterministic. We run
physics + ghost ticks on a fixed 60 Hz accumulator. Rendering uses the real
frame delta for smoothness but the simulation never drifts, so the ghost you
see always matches the run you made.
"""

from __future__ import annotations

import math
import sys
from enum import Enum, auto

import pygame

from . import constants as C
from .background import Background
from .camera import Camera
from .ghost import GhostManager
from .hud import HUD
from .level import load_all_levels
from .particles import ParticleSystem
from .player import Player
from .save_system import SaveSystem
from .sound import SoundManager


class State(Enum):
    MENU = auto()
    LEVEL_SELECT = auto()
    PLAYING = auto()
    PAUSED = auto()
    LEVEL_COMPLETE = auto()
    DEAD = auto()
    WIN = auto()


# Fixed simulation step (seconds). 1/60 keeps us locked to the recording rate.
FIXED_DT = 1.0 / C.FPS
# Catch up cap so a stalled frame doesn't spiral into a thousand-step catch-up.
MAX_STEPS_PER_FRAME = 5


class Game:
    """Top-level controller. Construct once, call run()."""

    def __init__(self) -> None:
        pygame.init()
        flags = pygame.SCALED
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), flags, vsync=1)
        pygame.display.set_caption("EchoRunner")
        self.clock = pygame.time.Clock()

        # Systems
        self.save = SaveSystem()
        self.sound = SoundManager()
        self.hud = HUD()
        self.background = Background()
        self.particles = ParticleSystem()

        # Fonts for menus — robust Font that falls back to freetype if needed.
        from .fonts import Font
        self.font_title = Font(72, bold=True)
        self.font_h1 = Font(44, bold=True)
        self.font_btn = Font(28, bold=True)
        self.font_body = Font(22)
        self.font_small = Font(18)

        # Content
        self.levels = load_all_levels()
        self.state: State = State.MENU

        # Per-run state
        self.player = Player(0, 0)
        self.camera = Camera()
        self.ghost_mgr: GhostManager | None = None
        self.current_level_index: int = 0
        self.run_time: float = 0.0
        self._accumulator: float = 0.0
        self._death_timer: float = 0.0
        self._complete_timer: float = 0.0
        self._level_time: float = 0.0
        self._death_flash: float = 0.0
        self._total_deaths: int = 0  # deaths on current level
        self._ghost_hum_playing: bool = False  # track proximity hum state

        # Time dilation (visual slow-mo; physics stays at fixed 60Hz)
        self._time_scale: float = 1.0
        self._time_scale_timer: float = 0.0

        # Screen transition (fade to black between states)
        self._fade_alpha: float = 0.0      # 0 = invisible, 255 = full black
        self._fade_direction: int = 0       # +1 = fading in, -1 = fading out, 0 = idle
        self._fade_callback = None           # callable when fade-out completes

        # Input edges
        self._jump_held = False
        self._jump_buffer_event = False

        # Menu navigation
        self._menu_selection = 0
        self._ls_selection = 0

        # Fullscreen toggle
        self._fullscreen = False

    # ====================================================================
    #  Main loop
    # ====================================================================
    def run(self) -> None:
        self.sound.start_music()
        running = True
        while running:
            dt = min(self.clock.tick(C.FPS) / 1000.0, 1.0 / 30.0)
            running = self.handle_events()
            self.update(dt)
            self.render()
        self.sound.stop_music()

    def quit(self) -> None:
        pygame.quit()

    # ====================================================================
    #  Events
    # ====================================================================
    def handle_events(self) -> bool:
        self._jump_buffer_event = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    self._jump_buffer_event = True
                    self._jump_held = True
                if self.state == State.MENU:
                    if not self._menu_keydown(event):
                        return False
                elif self.state == State.LEVEL_SELECT:
                    self._level_select_keydown(event)
                elif self.state == State.PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        self.state = State.PAUSED
                        self.sound.stop_music()
                elif self.state == State.PAUSED:
                    self._paused_keydown(event)
                elif self.state == State.LEVEL_COMPLETE:
                    self._complete_keydown(event)
                elif self.state == State.DEAD:
                    pass
                elif self.state == State.WIN:
                    if event.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
                        self.state = State.MENU
            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    self._jump_held = False
        return True

    # ====================================================================
    #  Update
    # ====================================================================
    def update(self, dt: float) -> None:
        self._level_time += dt
        # Advance time dilation
        self._update_time_dilation(dt)
        # Effective dt for particles and visual systems (slowed by time dilation)
        visual_dt = dt * self._time_scale

        if self.state == State.PLAYING:
            self._update_playing(dt)
            self.particles.update(visual_dt)
            self.camera.update(
                self.player.rect.centerx, self.player.rect.centery,
                self.levels[self.current_level_index].width_px,
                self.levels[self.current_level_index].height_px,
                dt, self.player.facing,
            )
        elif self.state == State.DEAD:
            self._death_timer -= dt
            self._death_flash = max(0.0, self._death_flash - dt * 2.5)
            self.player.advance_death_anim(dt)
            self.particles.update(visual_dt)
            # Camera keeps shaking during death
            if self.camera:
                self.camera.update(
                    self.player.rect.centerx, self.player.rect.centery,
                    self.levels[self.current_level_index].width_px,
                    self.levels[self.current_level_index].height_px,
                    dt, self.player.facing,
                )
            if self._death_timer <= 0:
                self._start_run(self.current_level_index)
        elif self.state == State.LEVEL_COMPLETE:
            self._complete_timer += dt
            self.particles.update(visual_dt)
        # screen transition
        self._update_fade(dt)

    def _update_time_dilation(self, dt: float) -> None:
        if self._time_scale_timer > 0.0:
            self._time_scale_timer -= dt
            if self._time_scale_timer <= 0.0:
                self._time_scale = 1.0

    def _update_playing(self, dt: float) -> None:
        """Fixed-timestep simulation. dt here is the real frame delta."""
        self._accumulator += dt
        steps = 0
        keys = pygame.key.get_pressed()
        level = self.levels[self.current_level_index]

        while self._accumulator >= FIXED_DT and steps < MAX_STEPS_PER_FRAME:
            self._accumulator -= FIXED_DT
            steps += 1
            self.run_time += FIXED_DT
            # Update every moving platform exactly once.
            deltas = []
            for mp in level.moving_platforms:
                dx, dy = mp.update(FIXED_DT, self._level_time)
                if self._standing_on(self.player.rect, mp.rect):
                    deltas.append((dx, dy))

            inp = self.player.capture_input(keys, self._jump_buffer_event, self._jump_held)
            self._jump_buffer_event = False
            was_grounded = self.player.on_ground
            self.player.update(FIXED_DT, inp, level.platforms(), deltas)

            # ---- juice reactions to per-tick player signals ----
            if self.player.just_landed:
                self.sound.play("land")
                self.camera.add_shake(C.SHAKE_LAND[0])
                self.particles.dust_landing(self.player.rect.centerx,
                                            self.player.rect.bottom)
            if self.player.just_jumped:
                self.sound.play("jump", pitch_var=2.0)  # ±2 semitones variation
                self.particles.dust_jump(self.player.rect.centerx,
                                        self.player.rect.bottom)
            if self.player.just_bonked:
                self.sound.play("bonk")

            # running dust + footstep
            if self.player.on_ground and abs(self.player.vx) > 150:
                if self._level_time % 0.12 < FIXED_DT:
                    self.particles.run_dust(self.player.rect.centerx,
                                           self.player.rect.bottom,
                                           self.player.facing)
                    self.sound.play("footstep", pitch_var=3.0)

            # ghost shimmer particles
            if self.ghost_mgr:
                self.ghost_mgr.update(FIXED_DT)
                pcx = self.player.rect.centerx
                pcy = self.player.rect.centery
                for g in self.ghost_mgr.ghosts:
                    if not g.is_finished() and g.emit_shimmer:
                        gx, gy = g.current_pos()
                        if abs(gx - pcx) < 120 and abs(gy - pcy) < 120:
                            if self._level_time % 0.15 < FIXED_DT:
                                self.particles.ghost_shimmer(
                                    gx + C.PLAYER_SIZE // 2,
                                    gy + C.PLAYER_SIZE // 2,
                                    g.color)

            # ---- collisions / outcomes ----
            if self.ghost_mgr and self.ghost_mgr.check_collision(self.player.rect):
                self._die()
                return
            for hz in level.hazards():
                if self.player.rect.colliderect(hz):
                    self._die()
                    return
            if self.player.rect.colliderect(level.exit_rect()):
                self._complete_level()
                return
            if self.player.rect.top > level.height_px + 200:
                self._die()
                return

    @staticmethod
    def _standing_on(player_rect: pygame.Rect, plat_rect: pygame.Rect) -> bool:
        if abs(player_rect.bottom - plat_rect.top) > 4:
            return False
        return player_rect.right > plat_rect.left and player_rect.left < plat_rect.right

    # ====================================================================
    #  Run lifecycle
    # ====================================================================
    def _start_run(self, level_index: int) -> None:
        self.current_level_index = level_index
        level = self.levels[level_index]
        spawn_x, spawn_y = level.spawn_pos()
        self.player.respawn(spawn_x, spawn_y)
        self.camera.reset()
        self.run_time = 0.0
        self._accumulator = 0.0
        self._death_flash = 0.0
        self._total_deaths = 0
        self._ghost_hum_playing = False
        self._time_scale = 1.0
        self._time_scale_timer = 0.0
        self._jump_held = False
        self._jump_buffer_event = False
        self.particles.clear()
        self.ghost_mgr = GhostManager(self.save, level.id)
        self.ghost_mgr.load()
        self.ghost_mgr.start_replay()
        self.state = State.PLAYING
        if self.sound.music_enabled:
            self.sound.start_music()

    def _die(self) -> None:
        self.sound.play("death")
        self.ghost_mgr.save_ghost(self.player.current_recording, completed=False,
                                  completion_time=None)
        self._total_deaths += 1
        # ---- JUICE ----
        self.player.start_death()
        self._death_timer = C.DEATH_RESTART_DELAY
        self._death_flash = 1.0
        self.camera.add_shake(C.SHAKE_DEATH[0])
        self.particles.death_burst(self.player.rect.centerx,
                                   self.player.rect.centery)
        self._time_scale = C.TIME_SCALE_DEATH
        self._time_scale_timer = C.TIME_SCALE_DEATH_DUR
        self.state = State.DEAD

    def _complete_level(self) -> None:
        self.sound.play("complete")
        self.ghost_mgr.save_ghost(self.player.current_recording, completed=True,
                                  completion_time=self.run_time)
        best = self.save.get_best_time(self.levels[self.current_level_index].id)
        is_new_best = False
        if best is None or self.run_time < best:
            self.save.set_best_time(self.levels[self.current_level_index].id, self.run_time)
            best = self.run_time
            is_new_best = True
        # ---- JUICE ----
        self.camera.add_shake(C.SHAKE_COMPLETE[0])
        ex = self.levels[self.current_level_index].exit_rect()
        self.particles.complete_sparkle(ex.centerx, ex.centery)
        self._time_scale = C.TIME_SCALE_COMPLETE
        self._time_scale_timer = C.TIME_SCALE_COMPLETE_DUR

        if self.current_level_index + 1 < len(self.levels):
            self.save.unlock_next(self.current_level_index + 1)
            self.sound.play("unlock")
        else:
            self.state = State.WIN
            return
        self._complete_timer = 0.0
        self._last_run_best = best
        self._last_run_new_best = is_new_best
        self.state = State.LEVEL_COMPLETE

    # ====================================================================
    #  Screen transitions
    # ====================================================================
    def _start_fade(self, callback=None) -> None:
        self._fade_alpha = 0.0
        self._fade_direction = -1  # fade out first
        self._fade_callback = callback

    def _update_fade(self, dt: float) -> None:
        if self._fade_direction == 0:
            return
        speed = 255.0 / (C.SCREEN_FADE_TIME / 2.0)  # per second
        if self._fade_direction < 0:
            self._fade_alpha = min(255.0, self._fade_alpha + speed * dt)
            if self._fade_alpha >= 255.0:
                self._fade_direction = 1  # start fading back in
                if self._fade_callback:
                    self._fade_callback()
                    self._fade_callback = None
        else:
            self._fade_alpha = max(0.0, self._fade_alpha - speed * dt)
            if self._fade_alpha <= 0.0:
                self._fade_direction = 0

    # ====================================================================
    #  Menu input handlers
    # ====================================================================
    def _menu_keydown(self, event) -> bool:
        if event.key in (pygame.K_UP, pygame.K_w):
            self._menu_selection = (self._menu_selection - 1) % 2
            self.sound.play("menu")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._menu_selection = (self._menu_selection + 1) % 2
            self.sound.play("menu")
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self._menu_selection == 0:
                self._start_fade(lambda: setattr(self, 'state', State.LEVEL_SELECT))
                self.sound.play("menu")
            else:
                return False
        elif event.key == pygame.K_ESCAPE:
            return False
        return True

    def _level_select_keydown(self, event) -> None:
        if not self.levels:
            return
        unlocked = self.save.load_progress()["unlocked_levels"]
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._ls_selection = max(0, self._ls_selection - 1)
            self.sound.play("menu")
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._ls_selection = min(len(self.levels) - 1, self._ls_selection + 1)
            self.sound.play("menu")
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._ls_selection = max(0, self._ls_selection - 3)
            self.sound.play("menu")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._ls_selection = min(len(self.levels) - 1, self._ls_selection + 3)
            self.sound.play("menu")
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self._ls_selection + 1 <= unlocked:
                idx = self._ls_selection
                self._start_fade(lambda: self._start_run(idx))
        elif event.key == pygame.K_c:
            lvl = self.levels[self._ls_selection]
            self.save.clear_ghosts(lvl.id)
            self.sound.play("menu")
        elif event.key == pygame.K_ESCAPE:
            self._start_fade(lambda: setattr(self, 'state', State.MENU))

    def _paused_keydown(self, event) -> None:
        if event.key == pygame.K_ESCAPE or event.key == pygame.K_p:
            self.state = State.PLAYING
            if self.sound.music_enabled:
                self.sound.start_music()
        elif event.key == pygame.K_r:
            self._start_run(self.current_level_index)
        elif event.key == pygame.K_c:
            lvl = self.levels[self.current_level_index]
            self.save.clear_ghosts(lvl.id)
            self._start_run(self.current_level_index)
        elif event.key == pygame.K_q:
            self._start_fade(lambda: setattr(self, 'state', State.MENU))
        elif event.key == pygame.K_m:
            self.sound.toggle_music()
        elif event.key == pygame.K_n:
            self.sound.toggle_sound()

    def _complete_keydown(self, event) -> None:
        if self._complete_timer < 0.3:
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            nxt = self.current_level_index + 1
            if nxt < len(self.levels):
                self._start_fade(lambda: self._start_run(nxt))
            else:
                self.state = State.WIN
        elif event.key == pygame.K_ESCAPE:
            self._start_fade(lambda: setattr(self, 'state', State.LEVEL_SELECT))

    # ====================================================================
    #  Rendering
    # ====================================================================
    def render(self) -> None:
        if self.state == State.MENU:
            self._render_menu()
        elif self.state == State.LEVEL_SELECT:
            self._render_level_select()
        elif self.state in (State.PLAYING, State.PAUSED, State.DEAD, State.LEVEL_COMPLETE):
            self._render_game()
            if self.state == State.PAUSED:
                self._render_pause()
            elif self.state == State.DEAD:
                self._render_death()
            elif self.state == State.LEVEL_COMPLETE:
                self._render_complete()
        elif self.state == State.WIN:
            self._render_win()
        # screen fade overlay (always on top)
        if self._fade_alpha > 1:
            fade_surf = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
            fade_surf.set_alpha(int(self._fade_alpha))
            fade_surf.fill((0, 0, 0))
            self.screen.blit(fade_surf, (0, 0))
        pygame.display.flip()

    def _render_game(self) -> None:
        level = self.levels[self.current_level_index]
        cx = self.camera.render_x
        cy = self.camera.render_y
        self.background.draw(self.screen, cx)
        level.draw(self.screen, cx, cy, t=self._level_time)
        if self.ghost_mgr:
            self.ghost_mgr.draw(self.screen, cx, cy)
        self.player.draw(self.screen, cx, cy)
        self.particles.draw(self.screen, cx, cy)
        # ghost proximity warning
        ghost_near = False
        if self.ghost_mgr and self.ghost_mgr.active_count() > 0:
            dist = self.ghost_mgr.nearest_ghost_dist(
                self.player.rect.centerx, self.player.rect.centery)
            ghost_near = dist < 2500  # ~50px squared
        # ghost proximity hum
        if ghost_near and not self._ghost_hum_playing:
            self.sound.play("ghost_hum")
            self._ghost_hum_playing = True
        elif not ghost_near:
            self._ghost_hum_playing = False
        self.hud.draw(self.screen, self.run_time,
                      self.save.get_best_time(level.id),
                      self.ghost_mgr.count() if self.ghost_mgr else 0,
                      fps=self.clock.get_fps(),
                      deaths=self._total_deaths,
                      ghost_near=ghost_near)

    def _render_menu(self) -> None:
        self.background.draw(self.screen, 0)
        # breathing title
        pulse = 0.95 + 0.05 * math.sin(self._level_time * 2.5)
        title_str = "ECHORUNNER"
        title = self.font_title.render(title_str, True, C.COLOR_ACCENT)
        # scale the title surface by the pulse factor
        tw, th = title.get_size()
        sw = max(1, int(tw * pulse))
        sh = max(1, int(th * pulse))
        scaled = pygame.transform.smoothscale(title, (sw, sh))
        self.screen.blit(scaled, ((C.SCREEN_W - sw) // 2, 160))

        sub = self.font_body.render("Race your own echoes. Survive yourself.", True,
                                    C.COLOR_TEXT_DIM)
        self.screen.blit(sub, ((C.SCREEN_W - sub.get_width()) // 2, 260))

        items = ["PLAY", "QUIT"]
        for i, label in enumerate(items):
            sel = (i == self._menu_selection)
            color = C.COLOR_ACCENT if sel else C.COLOR_TEXT
            txt = self.font_btn.render(label, True, color)
            x = (C.SCREEN_W - txt.get_width()) // 2
            y = 380 + i * 60
            if sel:
                # pulsing arrow
                arrow_pulse = int(3 * math.sin(self._level_time * 5))
                pygame.draw.polygon(self.screen, C.COLOR_ACCENT,
                                    [(x - 32 + arrow_pulse, y + 12),
                                     (x - 14, y + 22),
                                     (x - 32 + arrow_pulse, y + 32)])
                # underline glow
                uw = txt.get_width() + 20
                glow_a = int(40 + 30 * math.sin(self._level_time * 4))
                glow = pygame.Surface((uw, 4), pygame.SRCALPHA)
                glow.fill((*C.COLOR_ACCENT, glow_a))
                self.screen.blit(glow, (x - 10, y + txt.get_height() + 4))
            self.screen.blit(txt, (x, y))

        hint = self.font_small.render("Arrow keys / Enter to choose   |   F11 fullscreen",
                                      True, C.COLOR_TEXT_DIM)
        self.screen.blit(hint, ((C.SCREEN_W - hint.get_width()) // 2, C.SCREEN_H - 40))

    def _render_level_select(self) -> None:
        self.background.draw(self.screen, 0)
        title = self.font_h1.render("SELECT LEVEL", True, C.COLOR_TEXT)
        self.screen.blit(title, (60, 40))

        if not self.levels:
            msg = self.font_body.render("No levels found in levels/ directory.",
                                        True, C.COLOR_DANGER)
            self.screen.blit(msg, (60, 140))
            return

        unlocked = self.save.load_progress()["unlocked_levels"]
        card_w, card_h = 240, 180
        cols = 3
        start_x, start_y = 60, 140
        for i, level in enumerate(self.levels):
            col = i % cols
            row = i // cols
            x = start_x + col * (card_w + 30)
            y = start_y + row * (card_h + 30)
            is_unlocked = (i + 1) <= unlocked
            is_sel = (i == self._ls_selection)
            # selected card scales up slightly
            scale = 1.04 if is_sel else 1.0
            bw = int(card_w * scale)
            bh = int(card_h * scale)
            bx = x - (bw - card_w) // 2
            by = y - (bh - card_h) // 2
            base = C.COLOR_PANEL if is_unlocked else (18, 18, 30)
            border = C.COLOR_ACCENT if is_sel else (60, 60, 90)
            if is_sel:
                # glow border
                glow = pygame.Surface((bw + 12, bh + 12), pygame.SRCALPHA)
                ga = int(30 + 20 * math.sin(self._level_time * 4))
                pygame.draw.rect(glow, (*C.COLOR_ACCENT, ga),
                                 (0, 0, bw + 12, bh + 12), border_radius=14)
                self.screen.blit(glow, (bx - 6, by - 6))
            pygame.draw.rect(self.screen, base, (bx, by, bw, bh), border_radius=10)
            pygame.draw.rect(self.screen, border, (bx, by, bw, bh), 3, border_radius=10)

            name = self.font_btn.render(level.name, True,
                                        C.COLOR_TEXT if is_unlocked else C.COLOR_TEXT_DIM)
            self.screen.blit(name, (bx + 16, by + 16))
            num = self.font_small.render(f"LEVEL {i + 1}", True, C.COLOR_TEXT_DIM)
            self.screen.blit(num, (bx + 16, by + 54))

            if is_unlocked:
                best = self.save.get_best_time(level.id)
                gc = self.save.get_ghost_count(level.id)
                bt = self.font_small.render(f"Best: {self._fmt(best)}", True, C.COLOR_ACCENT)
                self.screen.blit(bt, (bx + 16, by + 90))
                gt = self.font_small.render(f"Echoes: {gc}", True, C.COLOR_TEXT)
                self.screen.blit(gt, (bx + 16, by + 116))
            else:
                cx2, cy2 = bx + card_w // 2, by + card_h // 2
                pygame.draw.rect(self.screen, (70, 70, 95),
                                 (cx2 - 18, cy2 - 4, 36, 30), border_radius=4)
                pygame.draw.arc(self.screen, (70, 70, 95),
                                (cx2 - 12, cy2 - 26, 24, 30), math.pi, 2 * math.pi, 3)

        hint = self.font_small.render(
            "Arrows: choose   Enter: play   C: clear echoes   Esc: back",
            True, C.COLOR_TEXT_DIM)
        self.screen.blit(hint, (60, C.SCREEN_H - 40))

    def _render_pause(self) -> None:
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        title = self.font_h1.render("PAUSED", True, C.COLOR_TEXT)
        self.screen.blit(title, ((C.SCREEN_W - title.get_width()) // 2, 180))
        lines = [
            "Esc / P  — Resume",
            "R        — Restart run",
            "C        — Clear echoes (this level)",
            "M        — Toggle music",
            "N        — Toggle sound",
            "Q        — Quit to menu",
        ]
        for i, ln in enumerate(lines):
            t = self.font_body.render(ln, True, C.COLOR_TEXT)
            self.screen.blit(t, ((C.SCREEN_W - t.get_width()) // 2, 280 + i * 36))

    def _render_death(self) -> None:
        # red vignette (edges only, not full-screen like before)
        flash = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        flash.fill((255, 60, 80, int(140 * self._death_flash)))
        self.screen.blit(flash, (0, 0))
        # text slides in from above
        slide = min(1.0, self._death_flash * 2)  # 0→1 as flash decays
        offset_y = int(-40 * (1.0 - slide))
        t = self.font_h1.render("CAUGHT BY AN ECHO", True, C.COLOR_DANGER)
        self.screen.blit(t, ((C.SCREEN_W - t.get_width()) // 2,
                             C.SCREEN_H // 2 - 40 + offset_y))

    def _render_complete(self) -> None:
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        level = self.levels[self.current_level_index]
        # spring-scale title
        t = min(1.0, self._complete_timer / 0.5)
        # elastic overshoot: 1.15 at peak, settles to 1.0
        scale = 1.0 + 0.15 * math.sin(t * math.pi) * (1.0 - t)
        title = self.font_h1.render(f"{level.name} COMPLETE", True, C.COLOR_ACCENT)
        tw, th = title.get_size()
        sw = max(1, int(tw * scale))
        sh = max(1, int(th * scale))
        scaled = pygame.transform.smoothscale(title, (sw, sh))
        self.screen.blit(scaled, ((C.SCREEN_W - sw) // 2, 180))

        best = getattr(self, "_last_run_best", None)
        nb = getattr(self, "_last_run_new_best", False)
        time_txt = self.font_btn.render(f"Your time: {self._fmt(self.run_time)}",
                                        True, C.COLOR_TEXT)
        self.screen.blit(time_txt, ((C.SCREEN_W - time_txt.get_width()) // 2, 270))
        if nb:
            # flash "NEW BEST" with golden glow
            pulse = 0.7 + 0.3 * math.sin(self._complete_timer * 6)
            nb_color = (255, int(200 * pulse), 60)
            best_label = "NEW BEST! "
        else:
            nb_color = C.COLOR_TEXT_DIM
            best_label = "Best: "
        best_txt = self.font_body.render(
            best_label + self._fmt(best), True, nb_color)
        self.screen.blit(best_txt, ((C.SCREEN_W - best_txt.get_width()) // 2, 320))

        if self._complete_timer > 0.3:
            hint = self.font_body.render(
                "Enter: Next level    Esc: Level select", True, C.COLOR_TEXT)
            self.screen.blit(hint, ((C.SCREEN_W - hint.get_width()) // 2, 420))

    def _render_win(self) -> None:
        self.background.draw(self.screen, 0)
        pulse = 0.95 + 0.05 * math.sin(self._level_time * 2)
        title = self.font_title.render("ALL LEVELS CLEARED", True, C.COLOR_ACCENT)
        tw, th = title.get_size()
        sw, sh = max(1, int(tw * pulse)), max(1, int(th * pulse))
        scaled = pygame.transform.smoothscale(title, (sw, sh))
        self.screen.blit(scaled, ((C.SCREEN_W - sw) // 2, 200))
        sub = self.font_body.render("You raced every echo — and won.",
                                    True, C.COLOR_TEXT_DIM)
        self.screen.blit(sub, ((C.SCREEN_W - sub.get_width()) // 2, 300))
        hint = self.font_body.render("Press Enter to return to menu", True, C.COLOR_TEXT)
        self.screen.blit(hint, ((C.SCREEN_W - hint.get_width()) // 2, 400))

    # ====================================================================
    #  Helpers
    # ====================================================================
    @staticmethod
    def _fmt(seconds: float | None) -> str:
        from .hud import format_time
        return format_time(seconds)

    def _toggle_fullscreen(self) -> None:
        self._fullscreen = not self._fullscreen
        flags = pygame.SCALED | (pygame.FULLSCREEN if self._fullscreen else 0)
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), flags, vsync=1)
