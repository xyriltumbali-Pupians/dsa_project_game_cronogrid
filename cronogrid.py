import sys
import pygame
import heapq
import os
import math

try:
    # Initialize Pygame
    pygame.init()

    # Constants (RPG Window Layout)
    WIDTH, HEIGHT = 1150, 720
    GRID_SIZE = 10
    TILE_SIZE = 54
    GRID_OFFSET_X = 60
    GRID_OFFSET_Y = 60

    # RPG Color Palette & Arena Theme
    BG_ARENA = (55, 40, 65)
    PANEL_BG = (24, 32, 48)
    PANEL_BORDER = (200, 200, 220)
    WHITE = (255, 255, 255)
    RED = (220, 50, 50)
    GREEN = (50, 200, 50)
    YELLOW = (255, 215, 0)
    ORANGE = (255, 140, 0)
    BLUE = (64, 142, 255)
    PINK = (255, 105, 180)

    # Overworld Themes with Level Requirements & Detailed Terrain Types
    MAP_THEMES = {
        1: {
            "name": "Enchanted Forest",
            "required_level": 1,
            "bg_grass": (45, 110, 65),
            "bg_alt": (40, 98, 58),
            "obstacle_type": "tree",
            "obstacle_color": (24, 64, 38),
            "trunk_color": (102, 51, 14),
            "enemy_name": "Wild Skeleton",
            "enemy_lvl": 4,
            "enemy_hp": 50,
            "enemy_atk": 12,
            "obstacles": [(3, 3), (3, 4), (5, 2), (6, 7), (2, 7), (7, 2), (1, 5), (8, 5)]
        },
        2: {
            "name": "Shadow Dungeons",
            "required_level": 6,
            "bg_grass": (50, 50, 70),
            "bg_alt": (40, 40, 55),
            "obstacle_type": "mountain",
            "obstacle_color": (70, 70, 95),
            "mountain_shadow": (35, 35, 50),
            "enemy_name": "Dark Phantom",
            "enemy_lvl": 6,
            "enemy_hp": 80,
            "enemy_atk": 18,
            "obstacles": [(2, 2), (2, 3), (2, 4), (7, 5), (7, 6), (4, 7), (5, 7), (5, 2)]
        },
        3: {
            "name": "Volcanic Realm",
            "required_level": 8,
            "bg_grass": (90, 40, 30),
            "bg_alt": (75, 30, 20),
            "obstacle_type": "volcano",
            "obstacle_color": (50, 20, 15),
            "lava_color": (255, 100, 0),
            "enemy_name": "Inferno Dragon",
            "enemy_lvl": 8,
            "enemy_hp": 120,
            "enemy_atk": 25,
            "obstacles": [(4, 4), (4, 5), (5, 4), (5, 5), (1, 8), (8, 1), (2, 2), (7, 7)]
        }
    }

    FONT = pygame.font.SysFont("georgia", 14)
    FONT_BOLD = pygame.font.SysFont("georgia", 15, bold=True)
    FONT_TITLE = pygame.font.SysFont("georgia", 20, bold=True)
    FONT_FX = pygame.font.SysFont("georgia", 24, bold=True)


    # 1. Pathfinder Class
    class Pathfinder:
        @staticmethod
        def search(grid_matrix, start, goal):
            rows, cols = len(grid_matrix), len(grid_matrix[0])
            def heuristic(a, b):
                return abs(a[0] - b[0]) + abs(a[1] - b[1])

            open_set = []
            heapq.heappush(open_set, (0, start))
            came_from = {}
            g_score = {start: 0}
            f_score = {start: heuristic(start, goal)}

            while open_set:
                current = heapq.heappop(open_set)[1]
                if current == goal:
                    path = []
                    while current in came_from:
                        path.append(current)
                        current = came_from[current]
                    path.reverse()
                    return path

                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    neighbor = (current[0] + dx, current[1] + dy)
                    if 0 <= neighbor[0] < cols and 0 <= neighbor[1] < rows:
                        if grid_matrix[neighbor[1]][neighbor[0]] == 1:
                            continue
                        tentative_g = g_score[current] + 1
                        if neighbor not in g_score or tentative_g < g_score[neighbor]:
                            came_from[neighbor] = current
                            g_score[neighbor] = tentative_g
                            f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                            heapq.heappush(open_set, (f_score[neighbor], neighbor))
            return []


    # 2. GridMap Class
    class GridMap:
        def __init__(self, size, obstacles):
            self.size = size
            self.matrix = [[0 for _ in range(size)] for _ in range(size)]
            for ox, oy in obstacles:
                self.matrix[oy][ox] = 1

        def is_obstacle(self, x, y):
            return self.matrix[y][x] == 1


    # 3. Unit Class (Integrated Sprite Sheet Slicer + Single Image Fallback)
    class Unit:
        def __init__(self, name, x, y, is_player=True, gender="Male", level=5, max_hp=60, attack=16):
            self.name = name
            self.x = x
            self.y = y
            self.pixel_x = GRID_OFFSET_X + x * TILE_SIZE
            self.pixel_y = GRID_OFFSET_Y + y * TILE_SIZE
            
            self.is_player = is_player
            self.gender = gender
            self.max_hp = max_hp
            self.hp = self.max_hp
            self.attack_power = attack
            self.level = level
            
            self.is_moving = False
            self.is_attacking = False
            self.attack_timer = 0
            self.skill_type = "Slash"
            self.target_pixel_x = self.pixel_x
            self.target_pixel_y = self.pixel_y
            self.move_speed = 4

            # Animation & Sprite Sheet Settings
            self.walk_frame = 0
            self.animation_timer = 0
            self.sprite_sheet = None
            self.static_image = None
            self.frame_width = 32   # Adjust to match your sprite sheet cell width
            self.frame_height = 32  # Adjust to match your sprite sheet cell height

            script_dir = os.path.dirname(os.path.abspath(__file__))

            if is_player:
                sheet_name = "male_knight_sheet.png" if gender == "Male" else "female_knight_sheet.png"
                fallback_name = "male_knight.png" if gender == "Male" else "female_knight.png"
            else:
                sheet_name = "skeleton_sheet.png"
                fallback_name = "skeleton.png"

            sheet_path = os.path.join(script_dir, sheet_name)
            fallback_path = os.path.join(script_dir, fallback_name)

            # 1st Priority: Load animated sprite sheet if available
            if os.path.exists(sheet_path):
                try:
                    self.sprite_sheet = pygame.image.load(sheet_path).convert_alpha()
                except Exception as e:
                    print(f"[ERROR Loading Sheet] {e}")
            # 2nd Priority: Load single static image if sprite sheet isn't present
            elif os.path.exists(fallback_path):
                try:
                    self.static_image = pygame.image.load(fallback_path).convert_alpha()
                except Exception as e:
                    print(f"[ERROR Loading Image] {e}")

        def get_current_frame(self, size):
            """Returns a scaled sprite frame from the sheet, or scales the static image."""
            if self.sprite_sheet:
                row = 1 if self.is_moving else 0
                col = self.walk_frame if self.is_moving else 0
                rect = pygame.Rect(col * self.frame_width, row * self.frame_height, self.frame_width, self.frame_height)
                try:
                    frame_image = self.sprite_sheet.subsurface(rect)
                    return pygame.transform.scale(frame_image, size)
                except ValueError:
                    # Fallback if sprite sheet dimensions are smaller than expected
                    return pygame.transform.scale(self.sprite_sheet, size)
            elif self.static_image:
                return pygame.transform.scale(self.static_image, size)
            return None

        def set_position(self, x, y):
            self.x = x
            self.y = y
            self.pixel_x = GRID_OFFSET_X + x * TILE_SIZE
            self.pixel_y = GRID_OFFSET_Y + y * TILE_SIZE
            self.target_pixel_x = self.pixel_x
            self.target_pixel_y = self.pixel_y

        def start_moving_to(self, x, y):
            self.x = x
            self.y = y
            self.target_pixel_x = GRID_OFFSET_X + x * TILE_SIZE
            self.target_pixel_y = GRID_OFFSET_Y + y * TILE_SIZE
            self.is_moving = True

        def trigger_attack_animation(self, skill="Slash"):
            self.is_attacking = True
            self.attack_timer = 20
            self.skill_type = skill

        def update_animation(self):
            if self.is_attacking:
                self.attack_timer -= 1
                if self.attack_timer <= 0:
                    self.is_attacking = False

            if self.is_moving:
                self.animation_timer += 1
                if self.animation_timer >= 6:
                    self.walk_frame = (self.walk_frame + 1) % 4
                    self.animation_timer = 0

                if self.pixel_x < self.target_pixel_x:
                    self.pixel_x = min(self.pixel_x + self.move_speed, self.target_pixel_x)
                elif self.pixel_x > self.target_pixel_x:
                    self.pixel_x = max(self.pixel_x - self.move_speed, self.target_pixel_x)
                if self.pixel_y < self.target_pixel_y:
                    self.pixel_y = min(self.pixel_y + self.move_speed, self.target_pixel_y)
                elif self.pixel_y > self.target_pixel_y:
                    self.pixel_y = max(self.pixel_y - self.move_speed, self.target_pixel_y)
                
                if self.pixel_x == self.target_pixel_x and self.pixel_y == self.target_pixel_y:
                    self.is_moving = False
                    self.walk_frame = 0


    # 4. Floating Text FX Class
    class FloatingText:
        def __init__(self, text, x, y, color):
            self.text = text
            self.x = x
            self.y = y
            self.color = color
            self.timer = 75

        def update(self):
            self.y -= 0.8
            self.timer -= 1


    # 5. Main Game Engine
    class ChronoGridGame:
        def __init__(self):
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
            pygame.display.set_caption("ChronoGrid: Multi-Map Portal RPG")
            self.clock = pygame.time.Clock()

            self.game_state = "SELECTION"
            self.selected_gender = "Male"
            self.selected_skill = "Slash"
            self.current_map_id = 1

            self.grid_map = None
            self.player = None
            self.enemy = None
            self.units = []
            self.command_log = ["[SYSTEM] I-explore ang mundo at palakasin ang mandirigma!"]
            self.floating_texts = []
            self.current_state = "PLAYER_TURN"
            self.winner = None
            self.screen_flash_timer = 0

            self.undo_stack = []

        def init_game(self, gender):
            self.selected_gender = gender
            self.player = Unit("Paladin Knight" if gender == "Male" else "Valkyrie Knight", 1, 1, is_player=True, gender=gender, level=5, max_hp=60, attack=16)
            self.load_map(1)
            self.game_state = "OVERWORLD"

        def load_map(self, map_id):
            self.current_map_id = map_id
            theme = MAP_THEMES[map_id]
            self.grid_map = GridMap(GRID_SIZE, theme["obstacles"])
            self.enemy = Unit(theme["enemy_name"], 8, 8, is_player=False, level=theme["enemy_lvl"], max_hp=theme["enemy_hp"], attack=theme["enemy_atk"])
            if self.player:
                self.player.set_position(1, 1)
            self.units = [self.player, self.enemy]
            self.winner = None
            self.undo_stack.clear()
            self.command_log = [f"[SYSTEM] Lumipat sa {theme['name']}!"]

        def enter_battle_scene(self):
            self.game_state = "BATTLE"
            theme = MAP_THEMES[self.current_map_id]
            self.command_log.append(f"[BATTLE] Sagupaan laban sa {theme['enemy_name']}!")
            self.player.pixel_x = 185
            self.player.pixel_y = 310
            self.enemy.pixel_x = 735
            self.enemy.pixel_y = 135
            self.current_state = "PLAYER_TURN"

        def respawn_or_next_map(self, next_map_id):
            target_theme = MAP_THEMES[next_map_id]
            if self.player.level < target_theme["required_level"]:
                self.command_log.append(f"[BABALA] Kailangan mo ng Level {target_theme['required_level']} para makapasok dito!")
                return
            self.load_map(next_map_id)
            self.game_state = "OVERWORLD"

        def perform_move(self, new_x, new_y):
            old_x, old_y = self.player.x, self.player.y
            self.undo_stack.append((old_x, old_y))
            self.player.start_moving_to(new_x, new_y)
            self.command_log.append(f"Lumipat sa ({new_x}, {new_y})")

        def undo_last_move(self):
            if self.game_state == "OVERWORLD" and self.undo_stack and not self.player.is_moving:
                prev_x, prev_y = self.undo_stack.pop()
                self.player.set_position(prev_x, prev_y)
                self.command_log.append(f"[UNDO] Bumalik sa posisyong ({prev_x}, {prev_y})")
            elif self.game_state == "BATTLE":
                self.command_log.append("[UNDO] Hindi pwede mag-undo habang nasa Battle Arena!")
            else:
                self.command_log.append("[UNDO] Walang nakaraang galaw para i-undo.")

        def run(self):
            while True:
                if self.game_state == "SELECTION":
                    self.handle_selection_events()
                    self.render_selection_screen()
                elif self.game_state == "OVERWORLD":
                    self.handle_overworld_events()
                    self.update_overworld()
                    self.render_overworld()
                elif self.game_state == "BATTLE":
                    self.handle_battle_events()
                    self.update_battle()
                    self.render_battle()
                self.clock.tick(60)

        def handle_selection_events(self):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1 or event.key == pygame.K_m:
                        self.init_game("Male")
                    elif event.key == pygame.K_2 or event.key == pygame.K_f:
                        self.init_game("Female")
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = pygame.mouse.get_pos()
                    if 300 <= pos[0] <= 520 and 280 <= pos[1] <= 490:
                        self.init_game("Male")
                    elif 620 <= pos[0] <= 840 and 280 <= pos[1] <= 490:
                        self.init_game("Female")

        def render_selection_screen(self):
            self.screen.fill((20, 24, 33))
            title = FONT_TITLE.render("CHRONOGRID: LEVEL-LOCKED PORTALS", True, YELLOW)
            sub = FONT.render("Pumili ng iyong Mandirigma:", True, WHITE)
            self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 120))
            self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 170))

            male_rect = pygame.Rect(300, 280, 220, 210)
            pygame.draw.rect(self.screen, PANEL_BG, male_rect, border_radius=12)
            pygame.draw.rect(self.screen, PANEL_BORDER, male_rect, 2, border_radius=12)
            self.screen.blit(FONT_BOLD.render("MALE PALADIN", True, BLUE), (340, 320))

            female_rect = pygame.Rect(620, 280, 220, 210)
            pygame.draw.rect(self.screen, PANEL_BG, female_rect, border_radius=12)
            pygame.draw.rect(self.screen, PANEL_BORDER, female_rect, 2, border_radius=12)
            self.screen.blit(FONT_BOLD.render("FEMALE VALKYRIE", True, PINK), (655, 320))

            pygame.display.flip()

        def handle_overworld_events(self):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_u:
                        self.undo_last_move()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = pygame.mouse.get_pos()
                    undo_btn = pygame.Rect(650, 395, 430, 38)
                    if undo_btn.collidepoint(pos):
                        self.undo_last_move()
                        return

                    if 650 <= pos[0] <= 1080:
                        for m_id in MAP_THEMES.keys():
                            p_btn = pygame.Rect(650, 185 + (m_id - 1) * 62, 430, 48)
                            if p_btn.collidepoint(pos):
                                self.respawn_or_next_map(m_id)
                                return

                    if not self.player.is_moving:
                        gx = (pos[0] - GRID_OFFSET_X) // TILE_SIZE
                        gy = (pos[1] - GRID_OFFSET_Y) // TILE_SIZE
                        if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
                            if not self.grid_map.is_obstacle(gx, gy):
                                path = Pathfinder.search(self.grid_map.matrix, (self.player.x, self.player.y), (gx, gy))
                                if path:
                                    self.perform_move(path[-1][0], path[-1][1])

        def update_overworld(self):
            self.player.update_animation()
            self.enemy.update_animation()
            if not self.enemy.is_moving and pygame.time.get_ticks() % 120 == 0:
                path = Pathfinder.search(self.grid_map.matrix, (self.enemy.x, self.enemy.y), (self.player.x, self.player.y))
                if len(path) > 1:
                    self.enemy.start_moving_to(path[0][0], path[0][1])
            if self.player.x == self.enemy.x and self.player.y == self.enemy.y:
                self.enter_battle_scene()

        def render_overworld(self):
            self.screen.fill((20, 24, 33))
            theme = MAP_THEMES[self.current_map_id]
            
            for y in range(GRID_SIZE):
                for x in range(GRID_SIZE):
                    rect = pygame.Rect(
                        GRID_OFFSET_X + x * TILE_SIZE,
                        GRID_OFFSET_Y + y * TILE_SIZE,
                        TILE_SIZE - 2,
                        TILE_SIZE - 2
                    )
                    if self.grid_map.is_obstacle(x, y):
                        center_x, center_y = rect.centerx, rect.centery
                        if theme["obstacle_type"] == "tree":
                            pygame.draw.rect(self.screen, theme["obstacle_color"], rect)
                            pygame.draw.rect(self.screen, theme["trunk_color"], (center_x - 5, center_y + 4, 10, 16))
                            pygame.draw.circle(self.screen, (20, 80, 35), (center_x, center_y - 4), 18)
                        elif theme["obstacle_type"] == "mountain":
                            pygame.draw.rect(self.screen, theme["obstacle_color"], rect)
                            points = [(rect.centerx, rect.top + 4), (rect.left + 4, rect.bottom - 4), (rect.right - 4, rect.bottom - 4)]
                            pygame.draw.polygon(self.screen, (90, 90, 120), points)
                        else:
                            pygame.draw.rect(self.screen, theme["obstacle_color"], rect)
                            pygame.draw.ellipse(self.screen, theme["lava_color"], (center_x - 16, center_y - 8, 32, 16))
                    else:
                        tile_col = theme["bg_grass"] if (x + y) % 2 == 0 else theme["bg_alt"]
                        pygame.draw.rect(self.screen, tile_col, rect)

            # Render Units using Sprite Sheet Frames
            tile_sprite_size = (TILE_SIZE - 8, TILE_SIZE - 8)
            for u in self.units:
                rect = pygame.Rect(u.pixel_x + 4, u.pixel_y + 4, tile_sprite_size[0], tile_sprite_size[1])
                bob_offset = int(math.sin(u.walk_frame * math.pi) * 3) if u.is_moving else 0
                char_rect = pygame.Rect(rect.x, rect.y + bob_offset, rect.width, rect.height)

                current_sprite = u.get_current_frame(tile_sprite_size)
                if current_sprite:
                    self.screen.blit(current_sprite, char_rect.topleft)
                else:
                    pygame.draw.ellipse(self.screen, BLUE if u.is_player else RED, char_rect)

            sidebar = pygame.Rect(630, 60, 470, 600)
            pygame.draw.rect(self.screen, PANEL_BG, sidebar, border_radius=10)
            pygame.draw.rect(self.screen, PANEL_BORDER, sidebar, 2, border_radius=10)
            self.screen.blit(FONT_TITLE.render(f"MAP: {theme['name'].upper()}", True, YELLOW), (650, 75))
            self.screen.blit(FONT.render(f"Lvl: {self.player.level} | Kalaban: {theme['enemy_name']}", True, WHITE), (650, 110))

            self.screen.blit(FONT_BOLD.render("🔒 Portals:", True, GREEN), (650, 155))
            for m_id, m_data in MAP_THEMES.items():
                p_btn = pygame.Rect(650, 182 + (m_id - 1) * 60, 430, 48)
                is_active = (self.current_map_id == m_id)
                can_enter = self.player.level >= m_data["required_level"]
                
                btn_color = (60, 120, 80) if is_active else ((50, 50, 70) if can_enter else (70, 40, 40))
                pygame.draw.rect(self.screen, btn_color, p_btn, border_radius=6)
                pygame.draw.rect(self.screen, YELLOW if is_active else PANEL_BORDER, p_btn, 2, border_radius=6)
                
                status_txt = f"Portal {m_id}: {m_data['name']}" if can_enter else f"Locked: {m_data['name']} (Lvl {m_data['required_level']})"
                self.screen.blit(FONT_BOLD.render(status_txt, True, WHITE if can_enter else (180, 140, 140)), (p_btn.x + 12, p_btn.y + 14))

            undo_btn = pygame.Rect(650, 395, 430, 38)
            pygame.draw.rect(self.screen, (100, 70, 40), undo_btn, border_radius=6)
            pygame.draw.rect(self.screen, YELLOW, undo_btn, 2, border_radius=6)
            self.screen.blit(FONT_BOLD.render("↩️ [U] Undo Last Move (Ibalik ang Galaw)", True, WHITE), (undo_btn.x + 12, undo_btn.y + 10))

            log_y = 445
            for msg in self.command_log[-5:]:
                self.screen.blit(FONT.render(msg, True, (225, 225, 225)), (650, log_y))
                log_y += 22

            pygame.display.flip()

        def handle_battle_events(self):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = pygame.mouse.get_pos()
                    if self.winner:
                        for idx, (p_id, p_data) in enumerate(MAP_THEMES.items()):
                            p_btn = pygame.Rect(650, 460 + idx * 55, 430, 45)
                            if p_btn.collidepoint(pos):
                                if self.player.level >= p_data["required_level"]:
                                    self.respawn_or_next_map(p_id)
                                else:
                                    self.command_log.append(f"Kailangan mo ng Level {p_data['required_level']}!")
                    else:
                        if self.current_state == "PLAYER_TURN" and not self.player.is_moving:
                            if 650 <= pos[0] <= 855:
                                if 430 <= pos[1] <= 480:
                                    self.execute_battle_attack("Slash")
                                elif 490 <= pos[1] <= 540:
                                    self.execute_battle_attack("Heavy")
                            elif 875 <= pos[0] <= 1080:
                                if 430 <= pos[1] <= 480:
                                    self.execute_battle_attack("Heal")
                                elif 490 <= pos[1] <= 540:
                                    self.game_state = "OVERWORLD"

        def execute_battle_attack(self, skill):
            dmg = 0
            self.screen_flash_timer = 12
            self.player.trigger_attack_animation(skill)

            if skill == "Slash":
                dmg = self.player.attack_power
                self.command_log.append(f"{self.player.name} Slash! -{dmg} HP")
                self.floating_texts.append(FloatingText(f"⚔️ -{dmg}", self.enemy.pixel_x + 20, self.enemy.pixel_y, RED))
            elif skill == "Heavy":
                dmg = int(self.player.attack_power * 1.5)
                self.command_log.append(f"{self.player.name} Heavy Strike! -{dmg} HP")
                self.floating_texts.append(FloatingText(f"💥 -{dmg} CRIT", self.enemy.pixel_x + 20, self.enemy.pixel_y, ORANGE))
            elif skill == "Heal":
                heal_amt = 25
                self.player.hp = min(self.player.max_hp, self.player.hp + heal_amt)
                self.command_log.append(f"{self.player.name} Holy Heal! +{heal_amt} HP")
                self.floating_texts.append(FloatingText(f"✨ +{heal_amt} HEAL", self.player.pixel_x + 20, self.player.pixel_y, GREEN))
                self.current_state = "ENEMY_TURN"
                return

            self.enemy.hp -= dmg
            if self.enemy.hp <= 0:
                self.enemy.hp = 0
                self.winner = "PLAYER"
                self.player.level += 1
                self.player.attack_power += 3
                self.player.max_hp += 15
                self.player.hp = self.player.max_hp
                self.command_log.append(f"[VICTORY] Level Up! Lvl {self.player.level} na ikaw!")
            else:
                self.current_state = "ENEMY_TURN"

        def update_battle(self):
            for u in self.units:
                u.update_animation()
            if self.screen_flash_timer > 0:
                self.screen_flash_timer -= 1
            for fx in self.floating_texts[:]:
                fx.update()
                if fx.timer <= 0:
                    self.floating_texts.remove(fx)

            if self.current_state == "ENEMY_TURN" and not self.winner:
                enemy_dmg = self.enemy.attack_power
                self.player.hp -= enemy_dmg
                self.screen_flash_timer = 12
                self.enemy.trigger_attack_animation("Slash")
                self.command_log.append(f"{self.enemy.name} umatak! -{enemy_dmg} HP")
                self.floating_texts.append(FloatingText(f"💀 -{enemy_dmg}", self.player.pixel_x + 20, self.player.pixel_y, RED))
                if self.player.hp <= 0:
                    self.player.hp = 0
                    self.winner = "ENEMY"
                    self.command_log.append("[DEFEAT] Natalo ka sa laban!")
                self.current_state = "PLAYER_TURN"

        def render_battle(self):
            self.screen.fill(BG_ARENA)
            theme = MAP_THEMES[self.current_map_id]

            banner = pygame.Rect(120, 15, 420, 40)
            pygame.draw.rect(self.screen, (45, 30, 55), banner, border_radius=8)
            pygame.draw.rect(self.screen, YELLOW, banner, 2, border_radius=8)
            title_surf = FONT_BOLD.render(f"🏟️ ARENA: {theme['name'].upper()} 🏟️", True, YELLOW)
            self.screen.blit(title_surf, (banner.centerx - title_surf.get_width()//2, banner.y + 10))

            p_platform = pygame.Rect(120, 390, 260, 90)
            pygame.draw.ellipse(self.screen, (150, 130, 110), p_platform)

            e_platform = pygame.Rect(670, 210, 240, 80)
            pygame.draw.ellipse(self.screen, (150, 130, 110), e_platform)

            battle_sprite_size = (74, 74)
            for u in self.units:
                offset_x = int(math.sin(u.attack_timer * 0.4) * 16) if u.is_attacking else 0
                px = u.pixel_x + (offset_x if u.is_player else -offset_x)
                py = u.pixel_y

                current_sprite = u.get_current_frame(battle_sprite_size)
                if current_sprite:
                    self.screen.blit(current_sprite, (px, py))
                else:
                    pygame.draw.ellipse(self.screen, BLUE if u.is_player else RED, (px, py, 74, 74))

            e_box = pygame.Rect(650, 40, 380, 95)
            pygame.draw.rect(self.screen, PANEL_BG, e_box, border_radius=10)
            pygame.draw.rect(self.screen, PANEL_BORDER, e_box, 2, border_radius=10)
            self.screen.blit(FONT_BOLD.render(f"{self.enemy.name}", True, WHITE), (670, 55))
            self.screen.blit(FONT.render(f"LVL {self.enemy.level}", True, YELLOW), (930, 55))
            pygame.draw.rect(self.screen, (50, 50, 50), (670, 85, 340, 12))
            e_hp_w = int(340 * max(0, self.enemy.hp / self.enemy.max_hp))
            pygame.draw.rect(self.screen, GREEN if e_hp_w > 100 else RED, (670, 85, e_hp_w, 12))

            p_box = pygame.Rect(120, 260, 380, 110)
            pygame.draw.rect(self.screen, PANEL_BG, p_box, border_radius=10)
            pygame.draw.rect(self.screen, PANEL_BORDER, p_box, 2, border_radius=10)
            self.screen.blit(FONT_BOLD.render(f"{self.player.name}", True, WHITE), (140, 275))
            self.screen.blit(FONT.render(f"LVL {self.player.level}", True, YELLOW), (400, 275))
            self.screen.blit(FONT.render(f"HP: {self.player.hp} / {self.player.max_hp}", True, WHITE), (140, 302))
            pygame.draw.rect(self.screen, (50, 50, 50), (140, 330, 340, 12))
            p_hp_w = int(340 * max(0, self.player.hp / self.player.max_hp))
            pygame.draw.rect(self.screen, GREEN if p_hp_w > 100 else RED, (140, 330, p_hp_w, 12))

            for fx in self.floating_texts:
                text_surf = FONT_FX.render(fx.text, True, fx.color)
                self.screen.blit(text_surf, (fx.x, fx.y))

            if self.screen_flash_timer > 0:
                flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                flash.fill((255, 50, 50, 80))
                self.screen.blit(flash, (0, 0))

            menu_box = pygame.Rect(630, 410, 470, 270)
            pygame.draw.rect(self.screen, PANEL_BG, menu_box, border_radius=10)
            pygame.draw.rect(self.screen, PANEL_BORDER, menu_box, 2, border_radius=10)

            if self.winner:
                self.screen.blit(FONT_BOLD.render("✨ PUMILI NG PORTAL NA PUPUNTAHAN:", True, YELLOW), (650, 425))
                for idx, (p_id, p_data) in enumerate(MAP_THEMES.items()):
                    p_btn = pygame.Rect(650, 455 + idx * 52, 430, 45)
                    can_enter = self.player.level >= p_data["required_level"]
                    pygame.draw.rect(self.screen, (50, 100, 140) if can_enter else (70, 40, 40), p_btn, border_radius=6)
                    pygame.draw.rect(self.screen, YELLOW if can_enter else PANEL_BORDER, p_btn, 2, border_radius=6)
                    txt_label = f"Portal {p_id}: {p_data['name']}" if can_enter else f"Locked: {p_data['name']} (Lvl {p_data['required_level']} needed)"
                    self.screen.blit(FONT_BOLD.render(txt_label, True, WHITE if can_enter else (180, 140, 140)), (p_btn.x + 12, p_btn.y + 12))
            else:
                skills = [("Slash", "1. Basic Slash", 650, 430), ("Heavy", "2. Heavy Strike", 650, 490),
                          ("Heal", "3. Holy Heal", 875, 430), ("Run", "4. Bumalik sa Map", 875, 490)]
                for s_key, s_name, bx, by in skills:
                    btn = pygame.Rect(bx, by, 210, 50)
                    is_sel = (self.selected_skill == s_key)
                    pygame.draw.rect(self.screen, (60, 100, 150) if is_sel else (40, 50, 75), btn, border_radius=6)
                    pygame.draw.rect(self.screen, YELLOW if is_sel else PANEL_BORDER, btn, 2, border_radius=6)
                    self.screen.blit(FONT_BOLD.render(s_name, True, WHITE), (btn.x + 15, btn.y + 14))

            log_y = 575
            for msg in self.command_log[-3:]:
                self.screen.blit(FONT.render(msg, True, (225, 225, 225)), (650, log_y))
                log_y += 22

            pygame.display.flip()

    if __name__ == "__main__":
        game = ChronoGridGame()
        game.run()

except Exception as e:
    import traceback
    print("\n[CRITICAL ERROR] Nag-crash ang laro:")
    traceback.print_exc()
    input("\nPindutin ang Enter para isara...")