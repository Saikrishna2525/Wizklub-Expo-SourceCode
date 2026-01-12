import pygame
import random
import time
import sys
import copy

# --- CONFIGURATION ---
WIDTH = 1200
HEIGHT = 800
SPLIT_X = WIDTH // 2
ROAD_WIDTH = 400
ROAD_MARGIN = (SPLIT_X - ROAD_WIDTH) // 2

# Colors
GREEN = (34, 139, 34)
DARK_GREEN = (20, 100, 20)
GRAY = (50, 50, 50)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
RED = (200, 0, 0)
BLUE = (0, 0, 200)
PURPLE = (150, 0, 150)
ORANGE = (255, 165, 0)
GOLD = (255, 215, 0)

# Game Constants
TRACK_LENGTH = 10000 
MIN_OBSTACLE_GAP = 350
CAR_WIDTH = 40
CAR_HEIGHT = 80
PLAYER_SPEED = 10 # Slightly faster for excitement
FPS = 60

class Obstacle:
    def __init__(self, type, lane_x, start_y, speed_y, speed_x=0):
        self.type = type
        self.rel_y = start_y
        self.lane_x = lane_x
        self.speed_y = speed_y
        self.speed_x = speed_x
        self.width = 30 if type == 'cone' else CAR_WIDTH
        self.height = 30 if type == 'cone' else CAR_HEIGHT
        self.direction_timer = random.randint(30, 90)

    def update(self):
        if self.type != 'cone':
            self.direction_timer -= 1
            if self.direction_timer <= 0:
                self.speed_x = random.uniform(-1.5, 1.5)
                self.direction_timer = random.randint(30, 90)
            self.lane_x += self.speed_x
            self.lane_x = max(30, min(self.lane_x, ROAD_WIDTH - 30))

class GameState:
    def __init__(self, p1_name="Player 1", p2_name="Player 2"):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("WizKlub Pro Racing - Expo Edition")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Agency FB", 28, bold=True)
        self.big_font = pygame.font.SysFont("Agency FB", 80, bold=True)
        
        self.p1_name = p1_name
        self.p2_name = p2_name
        
        # --- MOD: Parallax Scenery ---
        self.trees = [(random.randint(20, ROAD_MARGIN-20), random.randint(0, HEIGHT)) for _ in range(10)]
        
        self.preplan_obstacles()
        self.reset_players()
        self.winner = None

    def preplan_obstacles(self):
        self.planned_obstacles = []
        current_y = -800 
        while current_y > -TRACK_LENGTH:
            current_y -= random.randint(MIN_OBSTACLE_GAP, MIN_OBSTACLE_GAP + 200)
            otype = random.choice(['cone', 'car_fwd', 'car_bwd'])
            lane_x = random.randint(40, ROAD_WIDTH - 40)
            if otype == 'cone': obs = Obstacle('cone', lane_x, current_y, 0)
            elif otype == 'car_fwd': obs = Obstacle('car_fwd', lane_x, current_y, -2)
            else: obs = Obstacle('car_bwd', lane_x, current_y, 4)
            self.planned_obstacles.append(obs)

    def reset_players(self):
        self.p1_pos = {"x": ROAD_WIDTH // 2, "dist": 0, "invul": 0}
        self.p2_pos = {"x": ROAD_WIDTH // 2, "dist": 0, "invul": 0}
        self.p1_obs = copy.deepcopy(self.planned_obstacles)
        self.p2_obs = copy.deepcopy(self.planned_obstacles)

    def draw_car(self, surface, x, y, color, bwd=False, blinking=False):
        if blinking and (pygame.time.get_ticks() // 100) % 2 == 0: return # Mod: Blinking on hit
        rect = pygame.Rect(x - CAR_WIDTH//2, y - CAR_HEIGHT//2, CAR_WIDTH, CAR_HEIGHT)
        pygame.draw.rect(surface, color, rect, border_radius=8)
        # Detail: Roof
        pygame.draw.rect(surface, (20, 20, 20), (x-12, y-10, 24, 25), border_radius=4)
        # Windows
        win_y = y - 22 if not bwd else y + 5
        pygame.draw.rect(surface, (135, 206, 235), (x-14, win_y, 28, 15), border_radius=2)

    def render_view(self, player_num, pos, obstacles, offset_x):
        # 1. Draw Grass & Parallax Trees (Mod)
        view_rect = pygame.Rect(offset_x, 0, SPLIT_X, HEIGHT)
        pygame.draw.rect(self.screen, GREEN, view_rect)
        for tx, ty in self.trees:
            tree_y = (ty + pos['dist'] * 0.5) % HEIGHT # Move slower than road
            pygame.draw.circle(self.screen, DARK_GREEN, (offset_x + tx, int(tree_y)), 15)
            pygame.draw.circle(self.screen, DARK_GREEN, (offset_x + SPLIT_X - tx, int(tree_y)), 15)

        # 2. Draw Road
        pygame.draw.rect(self.screen, GRAY, (offset_x + ROAD_MARGIN, 0, ROAD_WIDTH, HEIGHT))
        
        # 3. Animated Road Lines
        lane_offset = pos['dist'] % 100
        for y in range(-100, HEIGHT + 100, 100):
            pygame.draw.rect(self.screen, WHITE, (offset_x + SPLIT_X//2 - 5, y + lane_offset, 10, 50))
        
        # 4. Obstacles
        for obs in obstacles:
            obs_screen_y = (obs.rel_y + pos['dist']) + (HEIGHT - 150)
            if -100 < obs_screen_y < HEIGHT + 100:
                obs_x = offset_x + ROAD_MARGIN + obs.lane_x
                if obs.type == 'cone':
                    pygame.draw.polygon(self.screen, ORANGE, [(obs_x, obs_screen_y-15), (obs_x-15, obs_screen_y+15), (obs_x+15, obs_screen_y+15)])
                else:
                    color = RED if obs.type == 'car_bwd' else YELLOW
                    self.draw_car(self.screen, obs_x, obs_screen_y, color, obs.type == 'car_bwd')

        # 5. Player Car (with blink mod)
        p_color = BLUE if player_num == 1 else PURPLE
        self.draw_car(self.screen, offset_x + ROAD_MARGIN + pos['x'], HEIGHT - 150, p_color, False, pos['invul'] > 0)
        
        # 6. UI MOD: Progress Bar
        progress_h = 400
        bar_x = offset_x + 30
        bar_y = HEIGHT // 2 - 200
        pygame.draw.rect(self.screen, WHITE, (bar_x, bar_y, 10, progress_h), 1)
        fill_h = (pos['dist'] / TRACK_LENGTH) * progress_h
        pygame.draw.rect(self.screen, GOLD, (bar_x, bar_y + progress_h - fill_h, 10, fill_h))

        name = self.p1_name if player_num == 1 else self.p2_name
        txt = self.font.render(f"{name}: {int(pos['dist'])}m", True, WHITE)
        self.screen.blit(txt, (offset_x + 60, 20))

    def check_collision(self, pos, obstacles):
        if pos['invul'] > 0: return False
        p_rect = pygame.Rect(pos['x'] - 15, (HEIGHT-150) - 30, 30, 60) # Tightened hitbox
        for obs in obstacles:
            obs_y = (obs.rel_y + pos['dist']) + (HEIGHT - 150)
            o_rect = pygame.Rect(obs.lane_x - obs.width//2, obs_y - obs.height//2, obs.width, obs.height)
            if p_rect.colliderect(o_rect): return True
        return False

    def run(self):
        while True:
            self.screen.fill((0, 0, 0))
            keys = pygame.key.get_pressed()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()

            # Player Logic
            players = [(self.p1_pos, self.p1_obs, pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s),
                       (self.p2_pos, self.p2_obs, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN)]

            for p, obs_list, left, right, up, down in players:
                if keys[left]: p['x'] -= 7
                if keys[right]: p['x'] += 7
                if keys[up]: p['dist'] += PLAYER_SPEED
                if keys[down]: p['dist'] -= PLAYER_SPEED // 2
                
                # Mod: Soft Penalty instead of Reset
                if self.check_collision(p, obs_list):
                    p['dist'] = max(0, p['dist'] - 600)
                    p['invul'] = 90 # 1.5 seconds invulnerability
                if p['invul'] > 0: p['invul'] -= 1

                p['x'] = max(30, min(p['x'], ROAD_WIDTH - 30))
                p['dist'] = max(0, p['dist'])
                
                if p['dist'] >= TRACK_LENGTH:
                    self.winner = self.p1_name if p == self.p1_pos else self.p2_name
                    self.show_leaderboard()
                    return

            for o in self.p1_obs: o.update()
            for o in self.p2_obs: o.update()

            self.render_view(1, self.p1_pos, self.p1_obs, 0)
            self.render_view(2, self.p2_pos, self.p2_obs, SPLIT_X)
            pygame.draw.line(self.screen, WHITE, (SPLIT_X, 0), (SPLIT_X, HEIGHT), 4)

            pygame.display.flip()
            self.clock.tick(FPS)

    def show_leaderboard(self):
        while True:
            self.screen.fill((10, 10, 15))
            title = self.big_font.render("RACE FINISHED", True, GOLD)
            win_txt = self.big_font.render(f"1st: {self.winner}", True, WHITE)
            info = self.font.render("Press SPACE to Restart - ESC to Quit", True, GREEN)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
            self.screen.blit(win_txt, (WIDTH//2 - win_txt.get_width()//2, 350))
            self.screen.blit(info, (WIDTH//2 - info.get_width()//2, 600))

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE: self.reset_players(); self.preplan_obstacles(); self.run()
                    if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
            pygame.display.flip()

if __name__ == "__main__":
    game = GameState()
    game.run()
