import pygame, random, sys, os, mysql.connector
from pygame.locals import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_HOST = os.environ.get("SNAKE_DB_HOST", "localhost")
DB_USER = os.environ.get("SNAKE_DB_USER", "root")
DB_PASS = os.environ.get("SNAKE_DB_PASS", "")
DB_NAME = os.environ.get("SNAKE_DB_NAME", "SNAKE_GAME")

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600 
CELLSIZE = 20
CELL_WIDTH = int(WINDOW_WIDTH / CELLSIZE)
CELL_HEIGHT = int((WINDOW_HEIGHT - 140) / CELLSIZE)

# --- Colors
White = (255, 255, 255)
Black = (0, 0, 0)
Red = (255, 0, 0)
Green = (0, 255, 0)
DarkGreen = (0, 155, 0)
DarkGrey = (40, 40, 40)
Grey = (140, 146, 172)
BGcolor = Black

INPUT_BG = (20, 20, 20)
INPUT_ACTIVE = (60, 60, 60)

HEAD = 0
score = None

FPSCLOCK = None
DISPLAYSURF = None
BASICFONT = None

def connect_database():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            use_pure=True,
            ssl_disabled=True,
        )
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
        conn.database = DB_NAME
        cur.execute(
            "CREATE TABLE IF NOT EXISTS PLAYERS ("
            "USERNAME VARCHAR(50) PRIMARY KEY, "
            "PASSWORD VARCHAR(50) NOT NULL)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS SCOREBOARD ("
            "SERIAL_NUM INT AUTO_INCREMENT PRIMARY KEY, "
            "USERNAME VARCHAR(50) NOT NULL, "
            "SCORE INT NULL)"
        )
        conn.commit()
        return conn
    except mysql.connector.Error as err:
        print("Could not connect to MySQL:", err)
        print("Check that MySQL is running and that the SNAKE_DB_PASS environment variable is set.")
        sys.exit(1)

scoreboard = connect_database()
data = scoreboard.cursor()
#Deleting NULL values out of precaution
data.execute("DELETE FROM SCOREBOARD WHERE SCORE IS NULL;")
scoreboard.commit()

#Database functions
def add_score(username):
        data.execute("INSERT INTO SCOREBOARD (USERNAME) VALUES (%s)", (username,))
        scoreboard.commit()
        return True

def get_user_scores(username):
        data.execute("SELECT SCORE FROM SCOREBOARD WHERE USERNAME = %s AND SCORE IS NOT NULL ORDER BY SERIAL_NUM", (username,))
        return [r[0] for r in data.fetchall()]

def OverallMax():
        data.execute("SELECT MAX(SCORE) FROM SCOREBOARD")
        row = data.fetchone()
        return row[0] if row and row[0] is not None else None

#Simple input box and buttons
class TextInput:
    def __init__(self, rect, font, is_password=False, numeric_only=False):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.is_password = is_password
        self.numeric_only = numeric_only
        self.text = ""
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == K_RETURN:
                pass
            else:
                ch = event.unicode
                if self.numeric_only:
                    if ch.isdigit():
                        self.text += ch
                else:
                    if ch:
                        self.text += ch

    def draw(self, surface):
        color = INPUT_ACTIVE if self.active else INPUT_BG
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, Grey, self.rect, 2)
        display = self.text
        if self.is_password:
            display = "*" * len(self.text)
        txt_surf = self.font.render(display, True, White)
        surface.blit(txt_surf, (self.rect.x + 6, self.rect.y + (self.rect.height - txt_surf.get_height()) // 2))

class Button:
    def __init__(self, rect, font, label):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.label = label
        self.hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface):
        color = (80, 120, 80) if self.hover else (60, 100, 60)
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, Grey, self.rect, 2)
        txt = self.font.render(self.label, True, White)
        surface.blit(txt, (self.rect.centerx - txt.get_width() // 2, self.rect.centery - txt.get_height() // 2))

#Main Game functions
def MainLoop(username):
    StartScreen()
    while True:
        RunGame()
        GameOverScreen(username)

def RunGame():
    global FPSCLOCK, DISPLAYSURF, BASICFONT, score
    startx = random.randint(5, CELL_WIDTH - 10)
    starty = random.randint(5, CELL_HEIGHT - 10)
    wormCoords = [{'x': startx, 'y': starty},
                  {'x': startx - 1, 'y': starty},
                  {'x': startx - 2, 'y': starty}]
    direction = 'right'
    apple = getRandomLocation(wormCoords)

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                terminate()
            elif event.type == KEYDOWN:
                if event.key == K_LEFT and direction != 'right':
                    direction = 'left'
                elif event.key == K_RIGHT and direction != 'left':
                    direction = 'right'
                elif event.key == K_UP and direction != 'down':
                    direction = 'up'
                elif event.key == K_DOWN and direction != 'up':
                    direction = 'down'
                elif event.key == K_ESCAPE:
                    terminate()

        # Wall collision
        if (wormCoords[HEAD]['x'] < 0 or wormCoords[HEAD]['x'] >= CELL_WIDTH or
            wormCoords[HEAD]['y'] < 0 or wormCoords[HEAD]['y'] >= CELL_HEIGHT):
            return

        # Body collision
        for wormBody in wormCoords[1:]:
            if wormBody['x'] == wormCoords[HEAD]['x'] and wormBody['y'] == wormCoords[HEAD]['y']:
                return

        score = len(wormCoords) - 3

        #Movement and eating apples
        if wormCoords[HEAD]['x'] == apple['x'] and wormCoords[HEAD]['y'] == apple['y']:
            apple = getRandomLocation(wormCoords)
        else:
            del wormCoords[-1]

        if direction == 'up':
            newHead = {'x': wormCoords[HEAD]['x'], 'y': wormCoords[HEAD]['y'] - 1}
        elif direction == 'down':
            newHead = {'x': wormCoords[HEAD]['x'], 'y': wormCoords[HEAD]['y'] + 1}
        elif direction == 'left':
            newHead = {'x': wormCoords[HEAD]['x'] - 1, 'y': wormCoords[HEAD]['y']}
        elif direction == 'right':
            newHead = {'x': wormCoords[HEAD]['x'] + 1, 'y': wormCoords[HEAD]['y']}

        wormCoords.insert(0, newHead)
        DISPLAYSURF.fill(BGcolor)
        DrawHeader()
        DrawGrid()
        DrawWorm(wormCoords)
        DrawApple(apple)
        DrawScore(score)
        pygame.display.update()
        snakeLength = len(wormCoords)
        speedBoost = ((snakeLength - 3) // 3) * 2
        FPS = min(6 + speedBoost, 30)
        FPSCLOCK.tick(FPS)

def StartScreen():
    DISPLAYSURF.fill(BGcolor)
    titlefont = pygame.font.Font('freesansbold.ttf', 36)
    title_surf = titlefont.render("Snake Game", True, White)
    DISPLAYSURF.blit(title_surf, (20, 12))
    DrawMsg("Use arrow keys to move. Avoid walls and yourself.")
    pygame.display.update()
    pygame.time.wait(700)

def GameOverScreen(username):
    global score, panel_font
    scoreint = int(score)
    data.execute(
            "UPDATE SCOREBOARD SET SCORE = %s WHERE USERNAME = %s AND SCORE IS NULL;",
            (scoreint, username)
        )
    scoreboard.commit()
    if data.rowcount == 0:
        data.execute("INSERT INTO SCOREBOARD (USERNAME, SCORE) VALUES (%s, %s)", (username, score))
        scoreboard.commit()
    # fonts
    big_font = pygame.font.Font('freesansbold.ttf', 60)
    panel_font = pygame.font.Font('freesansbold.ttf', 20)
    img = pygame.image.load(os.path.join(BASE_DIR, "GameOver.png"))

    stat_text = None
    stat_time = 0
    STAT_DURATION = 5000

    while True:
        BG_img = pygame.transform.scale(img, (800, 600))
        pos = BG_img.get_rect()
        pos.center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
        DISPLAYSURF.blit(BG_img, pos)
        DrawHeader()

        text = "GAME OVER"
        titleSurf = big_font.render(text, True, White)
        titleRect = titleSurf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        DISPLAYSURF.blit(titleSurf, titleRect)

        sub_text = f"Last saved score: {score}" if score is not None else "Score saved"
        subSurf = panel_font.render(sub_text, True, Grey)
        subRect = subSurf.get_rect(center= (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40))
        DISPLAYSURF.blit(subSurf, subRect)
        
        current_time = pygame.time.get_ticks()
        if stat_text and current_time - stat_time < STAT_DURATION:
            DisplayStats(stat_text)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == QUIT:
                terminate()
            elif event.type == KEYDOWN:
                if event.key == K_s:
                    add_score(username)
                    return
                elif event.key == K_ESCAPE:
                    terminate()
                elif event.key == K_o:
                    overall = OverallMax()
                    val = str(overall) if overall is not None else "N/A"
                    stat = f"Overall maximum score: {val}"
                    stat_text = stat
                    stat_time = pygame.time.get_ticks()
                elif event.key == K_l:
                    scores = get_user_scores(username)
                    if len(scores) >= 2:
                        stat = f"Your previous score was: {scores[-2]}"
                    elif len(scores) == 1:
                        stat = f"Only one recorded score: {scores[0]}"
                    else:
                        stat = f"No previous score found."
                    stat_text = stat
                    stat_time = pygame.time.get_ticks()
                elif event.key == K_n:
                    scores = get_user_scores(username)
                    stat = f"Your minimum score is: {min(scores)}" if scores else "No scores yet for user."
                    stat_text = stat
                    stat_time = pygame.time.get_ticks()
                elif event.key == K_m:
                    scores = get_user_scores(username)
                    stat = f"Your maximum score is: {max(scores)}" if scores else "No scores yet from other user."
                    stat_text = stat
                    stat_time = pygame.time.get_ticks()

#Supporting funtions
def DisplayStats(m):
    message = str(m)
    statSurf = panel_font.render(message, True, Grey)
    statRect = statSurf.get_rect(center= (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 80))
    DISPLAYSURF.blit(statSurf, statRect)
    return

def DrawHeader():
    pygame.draw.rect(DISPLAYSURF, (10,10,10), (0,0, WINDOW_WIDTH, 140))
    titlefont = pygame.font.Font('freesansbold.ttf', 40)
    title = titlefont.render("SNAKE GAME", True, White)
    DISPLAYSURF.blit(title, (20, 50))

def DrawMsg(text):
    txt = BASICFONT.render(text, True, Grey)
    DISPLAYSURF.blit(txt, (20, 56))

def DrawScore(score_val):
    txt = BASICFONT.render(f"SCORE: {score_val}", True, White)
    DISPLAYSURF.blit(txt, (WINDOW_WIDTH - 130, 60))

def DrawGrid():
    top = 140
    for x in range(0, WINDOW_WIDTH, CELLSIZE):
        pygame.draw.line(DISPLAYSURF, DarkGrey, (x, top), (x, WINDOW_HEIGHT))
    for y in range(top, WINDOW_HEIGHT, CELLSIZE):
        pygame.draw.line(DISPLAYSURF, DarkGrey, (0, y), (WINDOW_WIDTH, y))

def DrawWorm(wormCoords):
    for coord in wormCoords:
        x = coord['x'] * CELLSIZE
        y = coord['y'] * CELLSIZE + 140
        wormSegmentRect = pygame.Rect(x, y, CELLSIZE, CELLSIZE)
        pygame.draw.rect(DISPLAYSURF, DarkGreen, wormSegmentRect)
        wormInnerSegmentRect = pygame.Rect(x + 4, y + 4, CELLSIZE - 8, CELLSIZE - 8)
        pygame.draw.rect(DISPLAYSURF, Green, wormInnerSegmentRect)

def DrawApple(coord):
    x = coord['x'] * CELLSIZE
    y = coord['y'] * CELLSIZE + 140
    appleRect = pygame.Rect(x, y, CELLSIZE, CELLSIZE)
    pygame.draw.rect(DISPLAYSURF, Red, appleRect)

def getRandomLocation(wormCoords):
    while True:
        location = {'x': random.randint(0, CELL_WIDTH - 1), 'y': random.randint(0, CELL_HEIGHT - 1)}
        if location not in wormCoords:
            return location

def terminate():
    data.execute("DELETE FROM SCOREBOARD WHERE SCORE IS NULL;")
    scoreboard.commit()
    pygame.quit()
    try:
        if data: data.close()
        if scoreboard: scoreboard.close()
    except Exception:
        pass
    sys.exit()

#Main application: starting Interface
def MainApp():
    global FPSCLOCK, DISPLAYSURF, BASICFONT, scoreboard, data
    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    DISPLAYSURF = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Snake Game - Sign in")
    BASICFONT = pygame.font.Font('freesansbold.ttf', 18)

    # UI elements
    font = pygame.font.Font('freesansbold.ttf', 18)
    title_font = pygame.font.Font('freesansbold.ttf', 32)
    username_input = TextInput((20, 60, 300, 36), font, is_password=False, numeric_only=False)
    password_input = TextInput((340, 60, 300, 36), font, is_password=True, numeric_only=True)
    login_btn = Button((660, 36, 120, 36), font, "Login")
    reg_btn = Button((660, 86, 120, 36), font, "Register")

    # Message shown on screen
    msg = ""

    # Main UI loop
    while True:
        DISPLAYSURF.fill(BGcolor)
        pygame.draw.rect(DISPLAYSURF, (10,10,10), (0,0, WINDOW_WIDTH, 140))
        title = title_font.render("SNAKE GAME", True, White)
        DISPLAYSURF.blit(title, (20, 18))
        label_user = font.render("Username:", True, Grey)
        DISPLAYSURF.blit(label_user, (20, 105))
        label_pass = font.render("Password (numbers):", True, Grey)
        DISPLAYSURF.blit(label_pass, (340, 105))

        # draw inputs/buttons
        username_input.draw(DISPLAYSURF)
        password_input.draw(DISPLAYSURF)
        login_btn.draw(DISPLAYSURF)
        reg_btn.draw(DISPLAYSURF)

        # main message (errors or info)
        msg_color = Red if msg and msg.lower().startswith("error") else White
        msg_surf = BASICFONT.render(msg or "Enter credentials or register", True, msg_color)
        DISPLAYSURF.blit(msg_surf, (20, WINDOW_HEIGHT - 36))

        DrawGrid()
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == QUIT:
                terminate()
            username_input.handle_event(event)
            password_input.handle_event(event)

                # Login click
            if login_btn.handle_event(event):
                u = username_input.text.strip()
                p = password_input.text.strip()
                if not u or not p:
                    msg = "Error: Enter username and numeric password."
                    continue
                try:
                    pnum = int(p)
                except ValueError:
                    msg = "Error: Password must be numeric."
                    continue

                data.execute("SELECT PASSWORD FROM PLAYERS WHERE USERNAME = %s", (u,))
                row = data.fetchone()
                if row and row[0] == pnum:
                    msg = "Login successful. Starting game..."
                    add_score(u)
                    pygame.time.wait(300)
                    MainLoop(u)
                    msg = ""
                else:
                    msg = "Error: Invalid username or password."

                # Register click
            if reg_btn.handle_event(event):
                u = str(username_input.text.strip())
                p = password_input.text.strip()
                if not u or not p:
                    msg = "Error: Enter username and numeric password."
                    continue
                try:
                    pnum = int(p)
                except ValueError:
                    msg = "Error: Password must be numeric."
                    continue
                try:
                    data.execute("INSERT INTO PLAYERS (USERNAME, PASSWORD) VALUES (%s, %s)", (u, p))
                    scoreboard.commit()
                    data.execute("INSERT INTO SCOREBOARD (USERNAME) VALUES (%s)", (u,))
                    scoreboard.commit()
                    msg = "Registered. Starting game..."
                    pygame.time.wait(300)
                    MainLoop(u)
                    msg = ""
                    pass
                except Exception:
                    msg = "Error: This username already exists. Please use another or click on login."

            FPSCLOCK.tick(30)


if __name__ == "__main__":
    MainApp()
