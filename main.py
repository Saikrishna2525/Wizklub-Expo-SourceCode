import pygame
import random
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
BLACK = (0, 0, 0)

# Game Constants
TRACK_LENGTH = 10000 
MIN_OBSTACLE_GAP = 350
CAR_WIDTH = 40
CAR_HEIGHT = 80
PLAYER_SPEED = 12
FPS = 60

class Obstacle:
    def __init__(self, type, lane_x, start_y, speed_y, speed_x=0):
        self.type = type
        self.rel_y = start_y
        self.lane_x = lane_x
        self.speed_y = speed_y
        self.speed_x = speed_x
        # Set dimensions based on type
        if type == 'cone': self.width, self.height = 30, 30
        elif type == 'sign': self.width, self.height = 60, 25
        else: self.width, self.height = CAR_WIDTH, CAR_HEIGHT
        self.direction_timer = random.randint(30, 90)

    def update(self):
        # Only traffic cars move horizontally
        if self.type in ['car_fwd', 'car_bwd']:
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
        pygame.display.set_caption("WizKlub Pro Racing - Upgraded")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Agency FB", 28, bold=True)
        self.big_font = pygame.font.SysFont("Agency FB", 100, bold=True)

        self.p1_name = p1_name
        self.p2_name = p2_name
        self.trees = [(random.randint(20, ROAD_MARGIN-20), random.randint(0, HEIGHT)) for _ in range(10)]

        self.preplan_obstacles()
        self.reset_players()
        self.winner = None

    def preplan_obstacles(self):
        self.planned_obstacles = []
        current_y = -800 
        while current_y > -TRACK_LENGTH:
            current_y -= random.randint(MIN_OBSTACLE_GAP, MIN_OBSTACLE_GAP + 200)
            otype = random.choice(['cone', 'sign', 'car_fwd', 'car_bwd'])
            lane_x = random.randint(40, ROAD_WIDTH - 40)

            if otype == 'cone': obs = Obstacle('cone', lane_x, current_y, 0)
            elif otype == 'sign': obs = Obstacle('sign', lane_x, current_y, 0)
            elif otype == 'car_fwd': obs = Obstacle('car_fwd', lane_x, current_y, -2)
            else: obs = Obstacle('car_bwd', lane_x, current_y, 4)
            self.planned_obstacles.append(obs)

    def reset_players(self):
        self.p1_pos = {"x": ROAD_WIDTH // 2, "dist": 0, "invul": 0}
        self.p2_pos = {"x": ROAD_WIDTH // 2, "dist": 0, "invul": 0}
        self.p1_obs = copy.deepcopy(self.planned_obstacles)
        self.p2_obs = copy.deepcopy(self.planned_obstacles)

    def draw_car(self, surface, x, y, color, bwd=False, blinking=False, is_player=False):
        if blinking and (pygame.time.get_ticks() // 100) % 2 == 0: return

        # Main Body
        rect = pygame.Rect(x - CAR_WIDTH//2, y - CAR_HEIGHT//2, CAR_WIDTH, CAR_HEIGHT)
        pygame.draw.rect(surface, color, rect, border_radius=10)

        # Details for Player/Detailed Cars
        # Racing Stripe
        pygame.draw.rect(surface, WHITE, (x-3, y - CAR_HEIGHT//2, 6, CAR_HEIGHT))

        # Windshield
        win_y = y - 22 if not bwd else y + 5
        pygame.draw.rect(surface, (50, 50, 50), (x-15, win_y, 30, 18), border_radius=4)

        # Headlights
        light_y = y - CAR_HEIGHT//2 if not bwd else y + CAR_HEIGHT//2 - 5
        headlight_color = (255, 255, 200) if not bwd else (150, 0, 0)
        pygame.draw.circle(surface, headlight_color, (x-12, light_y + 5), 4)
        pygame.draw.circle(surface, headlight_color, (x+12, light_y + 5), 4)

        # Spoiler (for players)
        if is_player:
            spoiler_y = y + CAR_HEIGHT//2 - 5 if not bwd else y - CAR_HEIGHT//2
            pygame.draw.rect(surface, (20, 20, 20), (x-18, spoiler_y, 36, 6))

    def render_view(self, player_num, pos, obstacles, offset_x):
        # 1. Background
        view_rect = pygame.Rect(offset_x, 0, SPLIT_X, HEIGHT)
        pygame.draw.rect(self.screen, GREEN, view_rect)
        for tx, ty in self.trees:
            tree_y = (ty + pos['dist'] * 0.5) % HEIGHT
            pygame.draw.circle(self.screen, DARK_GREEN, (offset_x + tx, int(tree_y)), 15)
            pygame.draw.circle(self.screen, DARK_GREEN, (offset_x + SPLIT_X - tx, int(tree_y)), 15)

        # 2. Road
        pygame.draw.rect(self.screen, GRAY, (offset_x + ROAD_MARGIN, 0, ROAD_WIDTH, HEIGHT))

        # 3. Lines
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
                elif obs.type == 'sign':
                    # Draw a Construction Sign
                    pygame.draw.rect(self.screen, (101, 67, 33), (obs_x-2, obs_screen_y, 4, 20)) # Post
                    pygame.draw.rect(self.screen, ORANGE, (obs_x-30, obs_screen_y-25, 60, 25), border_radius=3)
                    pygame.draw.rect(self.screen, BLACK, (obs_x-25, obs_screen_y-20, 50, 5)) # Stripes
                    pygame.draw.rect(self.screen, BLACK, (obs_x-25, obs_screen_y-10, 50, 5))
                else:
                    color = RED if obs.type == 'car_bwd' else YELLOW
                    self.draw_car(self.screen, obs_x, obs_screen_y, color, obs.type == 'car_bwd')

        # 5. Player Car
        p_color = BLUE if player_num == 1 else PURPLE
        self.draw_car(self.screen, offset_x + ROAD_MARGIN + pos['x'], HEIGHT - 150, p_color, False, pos['invul'] > 0, True)

        # 6. UPGRADE: Progress Bar (UI)
        bar_width = 20
        bar_height = 300
        bx = offset_x + 20
        by = HEIGHT // 2 - 150
        # Background bar
        pygame.draw.rect(self.screen, (30, 30, 30), (bx, by, bar_width, bar_height), border_radius=5)
        # Fill bar
        fill = (pos['dist'] / TRACK_LENGTH) * bar_height
        pygame.draw.rect(self.screen, GOLD, (bx, by + bar_height - fill, bar_width, fill), border_radius=5)
        # Border
        pygame.draw.rect(self.screen, WHITE, (bx, by, bar_width, bar_height), 2, border_radius=5)

        name = self.p1_name if player_num == 1 else self.p2_name
        txt = self.font.render(f"{name}: {int(pos['dist'])}m", True, WHITE)
        self.screen.blit(txt, (offset_x + 60, 20))

    def traffic_light_countdown(self):
        for i in range(3, 0, -1):
            self.screen.fill(BLACK)
            # Draw simple light box
            box_rect = pygame.Rect(WIDTH//2 - 50, HEIGHT//2 - 150, 100, 300)
            pygame.draw.rect(self.screen, (40, 40, 40), box_rect, border_radius=10)

            # Draw lights
            colors = [RED if i == 3 else (50,0,0), ORANGE if i == 2 else (50,30,0), GREEN if i == 1 else (0,50,0)]
            for idx, c in enumerate(colors):
                pygame.draw.circle(self.screen, c, (WIDTH//2, HEIGHT//2 - 100 + (idx * 100)), 40)

            msg = self.big_font.render(str(i), True, WHITE)
            self.screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 + 180))
            pygame.display.flip()
            pygame.time.delay(1000)

    def check_collision(self, pos, obstacles):
        if pos['invul'] > 0: return False
        p_rect = pygame.Rect(pos['x'] - 15, (HEIGHT-150) - 30, 30, 60)
        for obs in obstacles:
            obs_y = (obs.rel_y + pos['dist']) + (HEIGHT - 150)
            o_rect = pygame.Rect(obs.lane_x - obs.width//2, obs_y - obs.height//2, obs.width, obs.height)
            if p_rect.colliderect(o_rect): return True
        return False

    def run(self):
        self.traffic_light_countdown()
        while True:
            self.screen.fill(BLACK)
            keys = pygame.key.get_pressed()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()

            players = [(self.p1_pos, self.p1_obs, pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s),
                       (self.p2_pos, self.p2_obs, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN)]

            for p, obs_list, left, right, up, down in players:
                if keys[left]: p['x'] -= 7
                if keys[right]: p['x'] += 7
                if keys[up]: p['dist'] += PLAYER_SPEED
                if keys[down]: p['dist'] -= PLAYER_SPEED // 2

                if self.check_collision(p, obs_list):
                    p['dist'] = max(0, p['dist'] - 800)
                    p['invul'] = 90 
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
            win_txt = self.font.render(f"WINNER: {self.winner}", True, WHITE)
            info = self.font.render("Press SPACE to Restart - ESC to Quit", True, GREEN)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
            self.screen.blit(win_txt, (WIDTH//2 - win_txt.get_width()//2, 350))
            self.screen.blit(info, (WIDTH//2 - info.get_width()//2, 600))

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE: 
                        self.reset_players()
                        self.preplan_obstacles()
                        self.run()
                    if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
            pygame.display.flip()

if __name__ == "__main__":
    game = GameState()
    game.run()
