"""
Basket Gift Collection Game
A pygame arcade game: move the basket to catch falling gifts, avoid bombs.

Controls:
    Arrow Keys / WASD - move basket (up/down/left/right)
    Mouse             - move basket freely
    SPACE             - start / restart
    P                 - pause
    M                 - toggle mouse/keyboard control
    ESC               - quit
"""
import os
import sys
import math
import random
import struct
import wave
import pygame

# ---------- Constants ----------
WIDTH, HEIGHT = 800, 600
FPS = 60
TITLE = "Basket Gift Collection"

# Colors
BG_TOP = (20, 30, 60)
BG_BOT = (60, 40, 90)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GOLD = (255, 215, 0)
RED = (220, 60, 60)
GREEN = (80, 200, 120)
BLUE = (80, 160, 240)
PURPLE = (180, 100, 220)
ORANGE = (255, 160, 60)
PINK = (255, 120, 180)
GREY = (120, 120, 130)
DARK = (30, 30, 40)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIGHSCORE_FILE = os.path.join(BASE_DIR, "highscore.txt")
SOUND_DIR = os.path.join(BASE_DIR, "_sounds")

# ---------- Sound helpers ----------
def _ensure_sound_dir():
    try:
        os.makedirs(SOUND_DIR, exist_ok=True)
    except Exception:
        pass

def _write_wav(path, freq, duration, volume=0.35, wave_type="sine"):
    sample_rate = 22050
    n = int(sample_rate * duration)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n):
            t = i / sample_rate
            env = max(0.0, 1.0 - (i / n) ** 0.6)
            if wave_type == "sine":
                val = math.sin(2 * math.pi * freq * t)
            elif wave_type == "square":
                val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            else:
                val = random.uniform(-1, 1)
            sample = int(32767 * volume * env * val)
            sample = max(-32768, min(32767, sample))
            frames += struct.pack("<h", sample)
        w.writeframes(frames)

SOUNDS = {}

def load_sounds():
    global SOUNDS
    if not pygame.mixer.get_init():
        return
    _ensure_sound_dir()
    specs = {
        "collect": (660, 0.08, "sine"),
        "big": (880, 0.12, "sine"),
        "golden": (1200, 0.18, "sine"),
        "bomb": (180, 0.25, "square"),
        "levelup": (520, 0.2, "sine"),
        "gameover": (220, 0.4, "square"),
    }
    for name, (f, d, wt) in specs.items():
        path = os.path.join(SOUND_DIR, name + ".wav")
        try:
            if not os.path.exists(path):
                _write_wav(path, f, d, wave_type=wt)
            SOUNDS[name] = pygame.mixer.Sound(path)
        except Exception:
            SOUNDS[name] = None

def play(name):
    s = SOUNDS.get(name)
    if s is not None:
        try:
            s.play()
        except Exception:
            pass

# ---------- Background music ----------
MUSIC_FILE = os.path.join(SOUND_DIR, "bgm.wav")

NOTES = {
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23,
    "G4": 392.00, "A4": 440.00, "B4": 493.88, "C5": 523.25,
}

# A simple cheerful looping melody (note, duration in beats)
MELODY = [
    ("C4", 1), ("E4", 1), ("G4", 1), ("C5", 2),
    ("B4", 1), ("G4", 1), ("E4", 1), ("C4", 2),
    ("D4", 1), ("F4", 1), ("A4", 1), ("G4", 2),
    ("E4", 1), ("C4", 1), ("D4", 1), ("G4", 2),
]

def generate_music():
    if not pygame.mixer.get_init():
        return
    _ensure_sound_dir()
    if os.path.exists(MUSIC_FILE):
        return
    try:
        sample_rate = 22050
        bpm = 120
        beat = 60.0 / bpm
        # build list of (freq, duration_seconds)
        seq = []
        for note, beats in MELODY:
            seq.append((NOTES[note], beats * beat))
        # add a second pass for length
        seq2 = []
        for note, beats in MELODY:
            seq2.append((NOTES[note] * 1.0, beats * beat))
        seq = seq + seq2
        total = sum(d for _, d in seq)
        n = int(sample_rate * total)
        frames = bytearray()
        idx = 0
        t_in_note = 0
        cur_freq = seq[0][0]
        cur_dur = seq[0][1]
        for i in range(n):
            t = i / sample_rate
            if t_in_note >= cur_dur:
                idx += 1
                if idx >= len(seq):
                    idx = 0
                    t_in_note = 0
                cur_freq, cur_dur = seq[idx]
                t_in_note = 0
            t_in_note += 1.0 / sample_rate
            # envelope per note
            note_pos = t_in_note / cur_dur
            env = 1.0
            if note_pos < 0.05:
                env = note_pos / 0.05
            elif note_pos > 0.85:
                env = (1.0 - note_pos) / 0.15
            env = max(0.0, min(1.0, env))
            val = math.sin(2 * math.pi * cur_freq * t)
            # soft harmony
            val += 0.3 * math.sin(2 * math.pi * cur_freq * 2 * t)
            val = val / 1.3
            sample = int(32767 * 0.25 * env * val)
            sample = max(-32768, min(32767, sample))
            frames += struct.pack("<h", sample)
        with wave.open(MUSIC_FILE, "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(frames)
    except Exception:
        pass

def start_music():
    if not pygame.mixer.get_init():
        return
    generate_music()
    if os.path.exists(MUSIC_FILE):
        try:
            pygame.mixer.music.load(MUSIC_FILE)
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

def stop_music():
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass

def pause_music():
    try:
        pygame.mixer.music.pause()
    except Exception:
        pass

def resume_music():
    try:
        pygame.mixer.music.unpause()
    except Exception:
        pass
# ---------- Utility ----------
def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def draw_text(surf, text, size, color, x, y, anchor="center", bold=False):
    font = pygame.font.SysFont("segoeui,arial", size, bold=bold)
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if anchor == "center":
        rect.center = (x, y)
    elif anchor == "topleft":
        rect.topleft = (x, y)
    elif anchor == "topright":
        rect.topright = (x, y)
    elif anchor == "midleft":
        rect.midleft = (x, y)
    surf.blit(rendered, rect)
    return rect

def draw_gradient(surf, top, bot):
    h = surf.get_height()
    for y in range(h):
        t = y / h
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (surf.get_width(), y))



# ---------- Basket ----------
class Basket:
    def __init__(self):
        self.w = 120
        self.h = 24
        self.x = WIDTH // 2
        self.y = HEIGHT - 80
        self.speed = 320
        self.vx = 0
        self.vy = 0
        self.target_x = self.x
        self.target_y = self.y
        self.color = (210, 150, 90)
        self.rim = (160, 100, 60)

    def update(self, dt, keys, mouse_x, mouse_y, use_mouse):
        if use_mouse:
            self.target_x = clamp(mouse_x, self.w // 2, WIDTH - self.w // 2)
            self.target_y = clamp(mouse_y, self.h // 2 + 20, HEIGHT - self.h // 2)
            self.x = lerp(self.x, self.target_x, min(1.0, dt * 12))
            self.y = lerp(self.y, self.target_y, min(1.0, dt * 12))
        else:
            self.vx = 0
            self.vy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vx -= self.speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vx += self.speed
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.vy -= self.speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.vy += self.speed
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.x = clamp(self.x, self.w // 2, WIDTH - self.w // 2)
            self.y = clamp(self.y, self.h // 2 + 20, HEIGHT - self.h // 2)

    def rect(self):
        return pygame.Rect(self.x - self.w // 2, self.y - self.h // 2, self.w, self.h)

    def draw(self, surf, offset=(0, 0)):
        ox, oy = offset
        r = self.rect()
        r = r.move(ox, oy)
        pygame.draw.rect(surf, self.color, r, border_radius=8)
        rim_rect = pygame.Rect(r.x, r.y, r.w, 6)
        pygame.draw.rect(surf, self.rim, rim_rect, border_radius=4)
        pygame.draw.arc(surf, self.rim, (r.x + r.w // 4, r.y - 14, r.w // 2, 20), math.pi, 2 * math.pi, 3)
        pygame.draw.rect(surf, (255, 255, 255), (r.x + 4, r.y + 2, r.w - 8, 4), border_radius=2)


# ---------- Falling items ----------
ITEM_TYPES = [
    ("small", BLUE, 1, 40, 22),
    ("medium", GREEN, 3, 25, 28),
    ("large", PURPLE, 5, 12, 36),
    ("golden", GOLD, 10, 5, 30),
    ("bomb", RED, 0, 18, 30),
]


class FallingItem:
    def __init__(self, level):
        weights = [t[3] for t in ITEM_TYPES]
        idx = random.choices(range(len(ITEM_TYPES)), weights=weights, k=1)[0]
        self.kind, self.color, self.points, _, self.size = ITEM_TYPES[idx]
        self.is_bomb = (self.kind == "bomb")
        self.x = random.randint(40, WIDTH - 40)
        self.y = -40
        base_speed = random.uniform(120, 180) + level * 18
        self.speed = base_speed + (0 if self.is_bomb else random.uniform(-20, 40))
        self.rot = random.uniform(0, 360)
        self.rot_speed = random.uniform(-90, 90)
        self.sway = random.uniform(-30, 30)
        self.sway_phase = random.uniform(0, math.pi * 2)

    def update(self, dt, t):
        self.y += self.speed * dt
        self.x += math.sin(t + self.sway_phase) * self.sway * dt
        self.x = clamp(self.x, 20, WIDTH - 20)
        self.rot += self.rot_speed * dt

    def rect(self):
        s = self.size
        return pygame.Rect(self.x - s // 2, self.y - s // 2, s, s)

    def draw(self, surf, offset=(0, 0)):
        ox, oy = offset
        cx = int(self.x + ox)
        cy = int(self.y + oy)
        s = self.size
        if self.is_bomb:
            pygame.draw.circle(surf, (40, 40, 50), (cx, cy), s // 2)
            pygame.draw.circle(surf, (80, 80, 90), (cx - 4, cy - 4), s // 4)
            pygame.draw.line(surf, (200, 150, 60), (cx, cy - s // 2), (cx + 6, cy - s // 2 - 8), 2)
            pygame.draw.circle(surf, ORANGE, (cx + 6, cy - s // 2 - 8), 3)
        elif self.kind == "golden":
            self._draw_star(surf, (cx, cy), s // 2, GOLD)
        else:
            r = pygame.Rect(cx - s // 2, cy - s // 2, s, s)
            pygame.draw.rect(surf, self.color, r, border_radius=6)
            pygame.draw.rect(surf, (255, 255, 255), (cx - 3, r.y, 6, s))
            pygame.draw.rect(surf, (255, 255, 255), (r.x, cy - 3, s, 6))
            pygame.draw.circle(surf, (255, 255, 255), (cx - 6, cy - 6), 3)
            pygame.draw.circle(surf, (255, 255, 255), (cx + 6, cy - 6), 3)

    def _draw_star(self, surf, center, radius, color):
        cx, cy = center
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * (math.pi / 5)
            r = radius if i % 2 == 0 else radius // 2
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, (255, 240, 150), pts, 2)

    def off_screen(self):
        return self.y > HEIGHT + 40


# ---------- Particles ----------
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "color", "life", "maxlife", "size")

    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        ang = random.uniform(0, math.pi * 2)
        spd = random.uniform(60, 220)
        self.vx = math.cos(ang) * spd
        self.vy = math.sin(ang) * spd - random.uniform(40, 120)
        self.color = color
        self.life = random.uniform(0.4, 0.9)
        self.maxlife = self.life
        self.size = random.randint(2, 5)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 320 * dt
        self.vx *= 0.98
        self.life -= dt

    def draw(self, surf, offset=(0, 0)):
        if self.life <= 0:
            return
        ox, oy = offset
        alpha = int(255 * (self.life / self.maxlife))
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
        surf.blit(s, (self.x - self.size + ox, self.y - self.size + oy))

# ---------- Game ----------
class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("segoeui,arial", 64, bold=True)
        self.font_med = pygame.font.SysFont("segoeui,arial", 32, bold=True)
        self.font_small = pygame.font.SysFont("segoeui,arial", 22)
        load_sounds()
        self.highscore = self._load_highscore()
        self.reset()
        self.state = "menu"
        self.shake = 0
        self.shake_offset = (0, 0)
        self.use_mouse = True
        self.menu_time = 0

    def _load_highscore(self):
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                return int(f.read().strip() or 0)
        except Exception:
            return 0

    def _save_highscore(self):
        try:
            with open(HIGHSCORE_FILE, "w") as f:
                f.write(str(self.highscore))
        except Exception:
            pass

    def reset(self):
        self.basket = Basket()
        self.items = []
        self.particles = []
        self.score = 0
        self.lives = 3
        self.level = 1
        self.spawn_timer = 0
        self.spawn_interval = 0.9
        self.time_played = 0
        self.flash = 0
        self.combo = 0
        self.combo_timer = 0

    def spawn_item(self):
        self.items.append(FallingItem(self.level))

    def start(self):
        self.reset()
        self.state = "playing"
        start_music()

    def update(self, dt):
        if self.state == "menu":
            self.menu_time += dt
            return
        if self.state != "playing":
            for p in self.particles:
                p.update(dt)
            self.particles = [p for p in self.particles if p.life > 0]
            return
        self.time_played += dt
        keys = pygame.key.get_pressed()
        mouse_x, mouse_y = pygame.mouse.get_pos()
        self.basket.update(dt, keys, mouse_x, mouse_y, self.use_mouse)

        new_level = 1 + int(self.score / 25)
        if new_level > self.level:
            self.level = new_level
            self.spawn_interval = max(0.28, 0.9 - (self.level - 1) * 0.07)
            play("levelup")

        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self.spawn_item()
            if self.level >= 4 and random.random() < 0.25:
                self.spawn_item()

        basket_rect = self.basket.rect()
        for item in list(self.items):
            item.update(dt, self.time_played)
            if item.rect().colliderect(basket_rect):
                if item.is_bomb:
                    self.lives -= 1
                    self.flash = 0.4
                    self.shake = 0.35
                    play("bomb")
                    self.combo = 0
                    for _ in range(25):
                        self.particles.append(Particle(item.x, item.y, (220, 80, 60)))
                    if self.lives <= 0:
                        self.game_over()
                else:
                    pts = item.points
                    self.combo += 1
                    self.combo_timer = 2.0
                    bonus = pts + (self.combo // 3)
                    self.score += bonus
                    color = item.color
                    play("golden" if item.kind == "golden" else ("big" if pts >= 5 else "collect"))
                    for _ in range(12 + pts * 2):
                        self.particles.append(Particle(item.x, item.y, color))
                self.items.remove(item)
                continue
            if item.off_screen():
                self.items.remove(item)

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0

        if self.flash > 0:
            self.flash -= dt
        if self.shake > 0:
            self.shake -= dt
            self.shake_offset = (random.uniform(-6, 6) * self.shake, random.uniform(-6, 6) * self.shake)
        else:
            self.shake_offset = (0, 0)

    def game_over(self):
        self.state = "gameover"
        play("gameover")
        stop_music()
        if self.score > self.highscore:
            self.highscore = self.score
            self._save_highscore()

    def draw(self):
        ox, oy = self.shake_offset
        self.screen.fill(BG_TOP)
        draw_gradient(self.screen, BG_TOP, BG_BOT)
        # decorative twinkling stars
        for i in range(40):
            sx = (i * 97 + int(self.menu_time * 10)) % WIDTH
            sy = (i * 53) % (HEIGHT // 2)
            r = 1 if i % 3 else 2
            pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy), r)

        if self.state == "menu":
            self._draw_menu()
        elif self.state in ("playing", "paused"):
            for item in self.items:
                item.draw(self.screen, (ox, oy))
            self.basket.draw(self.screen, (ox, oy))
            for p in self.particles:
                p.draw(self.screen, (ox, oy))
            self._draw_hud()
            if self.state == "paused":
                self._draw_paused()
        elif self.state == "gameover":
            for item in self.items:
                item.draw(self.screen, (ox, oy))
            self.basket.draw(self.screen, (ox, oy))
            for p in self.particles:
                p.draw(self.screen, (ox, oy))
            self._draw_gameover()

        if self.flash > 0:
            fl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fl.fill((220, 60, 60, int(120 * self.flash / 0.4)))
            self.screen.blit(fl, (0, 0))

        pygame.display.flip()

    def _draw_menu(self):
        draw_text(self.screen, "Basket Gift Collection", 52, GOLD, WIDTH // 2, 120, bold=True)
        draw_text(self.screen, "Catch the gifts, avoid the bombs!", 22, WHITE, WIDTH // 2, 175)
        lines = [
            "Controls:",
            "  Arrow Keys / WASD  - move basket (4 dir)",
            "  Mouse              - move basket freely",
            "  SPACE - start game",
            "  P - pause     M - toggle mouse/keys     ESC - quit",
            "",
            "Gifts:  blue=1   green=3   purple=5   gold=10",
            "Bombs:  lose a life (3 lives total)",
            "Combos give bonus points!",
        ]
        y = 230
        for ln in lines:
            draw_text(self.screen, ln, 19, (220, 220, 230), WIDTH // 2, y)
            y += 24
        draw_text(self.screen, f"High Score: {self.highscore}", 26, GOLD, WIDTH // 2, 490, bold=True)
        if (int(self.menu_time * 2) % 2 == 0):
            draw_text(self.screen, "Press SPACE or Click to Start", 24, (120, 220, 160), WIDTH // 2, 540, bold=True)

    def _draw_hud(self):
        draw_text(self.screen, f"Score: {self.score}", 28, WHITE, 20, 18, anchor="topleft", bold=True)
        draw_text(self.screen, f"Level: {self.level}", 22, (200, 220, 255), 20, 52, anchor="topleft")
        for i in range(self.lives):
            pygame.draw.circle(self.screen, RED, (WIDTH - 30 - i * 34, 34), 12)
            pygame.draw.circle(self.screen, (255, 120, 120), (WIDTH - 30 - i * 34 - 3, 30), 4)
        if self.combo >= 3:
            draw_text(self.screen, f"Combo x{self.combo}!", 22, GOLD, WIDTH // 2, 28, bold=True)
        # mode indicator
        mode = "Mouse" if self.use_mouse else "Keys"
        draw_text(self.screen, f"Mode: {mode}", 16, (180, 180, 200), WIDTH - 20, HEIGHT - 24, anchor="topright")

    def _draw_paused(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, "PAUSED", 64, WHITE, WIDTH // 2, HEIGHT // 2 - 20, bold=True)
        draw_text(self.screen, "Press P to resume", 22, (200, 200, 200), WIDTH // 2, HEIGHT // 2 + 30)

    def _draw_gameover(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, "GAME OVER", 64, RED, WIDTH // 2, HEIGHT // 2 - 80, bold=True)
        draw_text(self.screen, f"Score: {self.score}", 36, WHITE, WIDTH // 2, HEIGHT // 2 - 10)
        draw_text(self.screen, f"High Score: {self.highscore}", 28, GOLD, WIDTH // 2, HEIGHT // 2 + 30)
        draw_text(self.screen, "Press SPACE to play again  |  ESC to quit", 22, (200, 200, 200), WIDTH // 2, HEIGHT // 2 + 90)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_SPACE:
                if self.state in ("menu", "gameover"):
                    self.start()
            if event.key == pygame.K_p:
                if self.state == "playing":
                    self.state = "paused"
                    pause_music()
                elif self.state == "paused":
                    self.state = "playing"
                    resume_music()
            if event.key == pygame.K_m:
                self.use_mouse = not self.use_mouse
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.state in ("menu", "gameover"):
                self.start()
        return True

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            for event in pygame.event.get():
                if not self.handle_event(event):
                    running = False
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
