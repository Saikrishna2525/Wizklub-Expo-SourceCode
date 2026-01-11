import pygame
import random
import time
import sys

# --- CONFIGURATION ---
WIDTH = 1200
HEIGHT = 800
SPLIT_X = WIDTH // 2
ROAD_WIDTH = 400
ROAD_MARGIN = (SPLIT_X - ROAD_WIDTH) // 2

# Colors
GREEN = (34, 139, 34)
GRAY = (50, 50, 50)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
RED = (200, 0, 0)
BLUE = (0, 0, 200)
ORANGE = (255, 165, 0)

# Game Constants
TRACK_LENGTH = 10000  # Distance to finish line
MIN_OBSTACLE_GAP = 350
CAR_WIDTH = 40
CAR_HEIGHT = 80
PLAYER_SPEED = 8
FPS = 60

class Obstacle:
    def __init__(self, type, lane_x, start_y, speed_y, speed_x=0):
        self.type = type  # 'cone', 'car_fwd', 'car_bwd'
        self.rel_y = start_y  # Position relative to track start
        self.lane_x = lane_x  # Horizontal center relative to road left
        self.speed_y = speed_y
        self.speed_x = speed_x
        self.width = 30 if type == 'cone' else CAR_WIDTH
        self.height = 30 if type == 'cone' else CAR_HEIGHT
        self.direction_timer = random.randint(30, 90)

    def update(self):
        # Specific behavior for cars (moving directions)
        if self.type != 'cone':
            self.direction_timer -= 1
            if self.direction_timer <= 0:
                self.speed_x = random.uniform(-2, 2)
                self.direction_timer = random.randint(30, 90)
            
            self.lane_x += self.speed_x
            # Keep cars on the road
            self.lane_x = max(20, min(self.lane_x, ROAD_WIDTH - 20))

class GameState:
    def __init__(self, p1_name="Player 1", p2_name="Player 2"):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Multiplayer Pro Racing")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 64, bold=True)
        
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.preplan_obstacles()
        self.reset_players()
        self.winner = None
        self.start_time = time.time()

    def preplan_obstacles(self):
        """Generates a fixed list of obstacles for the entire track."""
        self.planned_obstacles = []
        current_y = -800 # Start spawning above view
        
        while current_y > -TRACK_LENGTH:
            current_y -= random.randint(MIN_OBSTACLE_GAP, MIN_OBSTACLE_GAP + 200)
            type = random.choice(['cone', 'car_fwd', 'car_bwd'])
            lane_x = random.randint(40, ROAD_WIDTH - 40)
            
            if type == 'cone':
                obs = Obstacle('cone', lane_x, current_y, 0)
            elif type == 'car_fwd':
                obs = Obstacle('car_fwd', lane_x, current_y, -2) # Moves with traffic
            else:
                obs = Obstacle('car_bwd', lane_x, current_y, 4)  # Moves against traffic
                
            self.planned_obstacles.append(obs)

    def reset_players(self):
        # Each player has their own scroll position and car X
        self.p1_pos = {"x": ROAD_WIDTH // 2, "dist": 0}
        self.p2_pos = {"x": ROAD_WIDTH // 2, "dist": 0}
        # Deep copy obstacles for each player so they can be modified independently if needed
        import copy
        self.p1_obs = copy.deepcopy(self.planned_obstacles)
        self.p2_obs = copy.deepcopy(self.planned_obstacles)

    def draw_car(self, surface, x, y, color, is_enemy=False, bwd=False):
        # Custom drawing to avoid "white background" issues with external images
        rect = pygame.Rect(x - CAR_WIDTH//2, y - CAR_HEIGHT//2, CAR_WIDTH, CAR_HEIGHT)
        pygame.draw.rect(surface, color, rect, border_radius=8)
        # Windows
        win_y = y - 20 if not bwd else y + 5
        pygame.draw.rect(surface, (135, 206, 235), (x-15, win_y, 30, 15), border_radius=2)
        # Wheels
        for wx, wy in [(x-22, y-30), (x+15, y-30), (x-22, y+15), (x+15, y+15)]:
            pygame.draw.rect(surface, (20, 20, 20), (wx, wy, 8, 15))

    def draw_cone(self, surface, x, y):
        pygame.draw.polygon(surface, ORANGE, [(x, y-15), (x-15, y+15), (x+15, y+15)])
        pygame.draw.rect(surface, WHITE, (x-8, y, 16, 5))

    def render_view(self, player_num, pos, obstacles, offset_x):
        # 1. Draw Grass
        view_rect = pygame.Rect(offset_x, 0, SPLIT_X, HEIGHT)
        pygame.draw.rect(self.screen, GREEN, view_rect)
        
        # 2. Draw Road
        road_rect = pygame.Rect(offset_x + ROAD_MARGIN, 0, ROAD_WIDTH, HEIGHT)
        pygame.draw.rect(self.screen, GRAY, road_rect)
        
        # 3. Draw Road Markings (animated by distance)
        lane_offset = pos['dist'] % 100
        for y in range(-100, HEIGHT + 100, 100):
            pygame.draw.rect(self.screen, WHITE, (offset_x + SPLIT_X//2 - 5, y + lane_offset, 10, 50))
        
        # 4. Draw Obstacles
        # Obstacles rel_y is negative (distance from start). 
        # Current viewport bottom is at pos['dist'].
        for obs in obstacles:
            # Calculate screen Y based on player's progress
            # 0 distance = car at HEIGHT-150
            obs_screen_y = (obs.rel_y + pos['dist']) + (HEIGHT - 150)
            
            if -100 < obs_screen_y < HEIGHT + 100:
                obs_x = offset_x + ROAD_MARGIN + obs.lane_x
                if obs.type == 'cone':
                    self.draw_cone(self.screen, obs_x, obs_screen_y)
                else:
                    color = RED if obs.type == 'car_bwd' else YELLOW
                    self.draw_car(self.screen, obs_x, obs_screen_y, color, True, obs.type == 'car_bwd')

        # 5. Draw Player Car
        self.draw_car(self.screen, offset_x + ROAD_MARGIN + pos['x'], HEIGHT - 150, BLUE if player_num == 1 else (150, 0, 150))
        
        # 6. UI Overlay
        name = self.p1_name if player_num == 1 else self.p2_name
        txt = self.font.render(f"{name}: {int(pos['dist'])}m / {TRACK_LENGTH}m", True, WHITE)
        self.screen.blit(txt, (offset_x + 20, 20))
        
        # Split line
        if player_num == 1:
            pygame.draw.line(self.screen, WHITE, (SPLIT_X, 0), (SPLIT_X, HEIGHT), 5)

    def check_collision(self, pos, obstacles):
        p_rect = pygame.Rect(pos['x'] - CAR_WIDTH//2, (HEIGHT-150) - CAR_HEIGHT//2, CAR_WIDTH, CAR_HEIGHT)
        for obs in obstacles:
            obs_screen_y = (obs.rel_y + pos['dist']) + (HEIGHT - 150)
            o_rect = pygame.Rect(obs.lane_x - obs.width//2, obs_screen_y - obs.height//2, obs.width, obs.height)
            if p_rect.colliderect(o_rect):
                return True
        return False

    def run(self):
        running = True
        while running:
            self.screen.fill((0, 0, 0))
            keys = pygame.key.get_pressed()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            # --- Player 1 Logic (WASD) ---
            if keys[pygame.K_a]: self.p1_pos['x'] -= 7
            if keys[pygame.K_d]: self.p1_pos['x'] += 7
            if keys[pygame.K_w]: self.p1_pos['dist'] += PLAYER_SPEED
            if keys[pygame.K_s]: self.p1_pos['dist'] -= PLAYER_SPEED // 2
            
            # --- Player 2 Logic (Arrows) ---
            if keys[pygame.K_LEFT]: self.p2_pos['x'] -= 7
            if keys[pygame.K_RIGHT]: self.p2_pos['x'] += 7
            if keys[pygame.K_UP]: self.p2_pos['dist'] += PLAYER_SPEED
            if keys[pygame.K_DOWN]: self.p2_pos['dist'] -= PLAYER_SPEED // 2

            # Updates & Boundary
            for p in [self.p1_pos, self.p2_pos]:
                p['x'] = max(20, min(p['x'], ROAD_WIDTH - 20))
                p['dist'] = max(0, p['dist'])
                if p['dist'] >= TRACK_LENGTH:
                    self.winner = self.p1_name if p == self.p1_pos else self.p2_name
                    self.show_leaderboard()
                    return

            # Update obstacle internal movements
            for obs in self.p1_obs: obs.update()
            for obs in self.p2_obs: obs.update()

            # Collision Check
            if self.check_collision(self.p1_pos, self.p1_obs):
                self.p1_pos = {"x": ROAD_WIDTH // 2, "dist": 0}
            if self.check_collision(self.p2_pos, self.p2_obs):
                self.p2_pos = {"x": ROAD_WIDTH // 2, "dist": 0}

            # Render
            self.render_view(1, self.p1_pos, self.p1_obs, 0)
            self.render_view(2, self.p2_pos, self.p2_obs, SPLIT_X)

            pygame.display.flip()
            self.clock.tick(FPS)

    def show_leaderboard(self):
        # Transition to Leaderboard Window
        waiting = True
        runner_up = self.p2_name if self.winner == self.p1_name else self.p1_name
        
        while waiting:
            self.screen.fill((20, 20, 20))
            
            title = self.big_font.render("LEADERBOARD", True, YELLOW)
            win_txt = self.big_font.render(f"WINNER: {self.winner}", True, WHITE)
            run_txt = self.font.render(f"Runner Up: {runner_up}", True, GRAY)
            info = self.font.render("Press SPACE to play again or ESC to quit", True, GREEN)

            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
            self.screen.blit(win_txt, (WIDTH//2 - win_txt.get_width()//2, 300))
            self.screen.blit(run_txt, (WIDTH//2 - run_txt.get_width()//2, 450))
            self.screen.blit(info, (WIDTH//2 - info.get_width()//2, 650))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        waiting = False
                        self.reset_players()
                        self.preplan_obstacles()
                        self.run()
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

            pygame.display.flip()
            self.clock.tick(15)

if __name__ == "__main__":
    game = GameState()
    game.run()