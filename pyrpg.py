import os
import math
import random
import dill as pickle
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font

#Necessary for importing fonts into TkInter
from ctypes import windll, byref, create_unicode_buffer, create_string_buffer
FR_PRIVATE  = 0x10
FR_NOT_ENUM = 0x20

TITLE = "Yggdrasil"
VERSION = "0.0"

SAVE_PATH = "save/"
MAP_PATH = "assets/maps/"
FONT_PATH = "assets/fonts/"

MAP_WIDTH = 39
MAP_HEIGHT = 19

TICK_FREQUENCY = 30
TICK_DELAY = 1 / TICK_FREQUENCY

MAX_HEALTH = 100

PERMUTATION = (151,160,137,91,90,15,
    131,13,201,95,96,53,194,233,7,225,140,36,103,30,69,142,8,99,37,240,21,10,23,
    190, 6,148,247,120,234,75,0,26,197,62,94,252,219,203,117,35,11,32,57,177,33,
    88,237,149,56,87,174,20,125,136,171,168, 68,175,74,165,71,134,139,48,27,166,
    77,146,158,231,83,111,229,122,60,211,133,230,220,105,92,41,55,46,245,40,244,
    102,143,54, 65,25,63,161, 1,216,80,73,209,76,132,187,208, 89,18,169,200,196,
    135,130,116,188,159,86,164,100,109,198,173,186, 3,64,52,217,226,250,124,123,
    5,202,38,147,118,126,255,82,85,212,207,206,59,227,47,16,58,17,182,189,28,42,
    223,183,170,213,119,248,152, 2,44,154,163, 70,221,153,101,155,167, 43,172,9,
    129,22,39,253, 19,98,108,110,79,113,224,232,178,185, 112,104,218,246,97,228,
    251,34,242,193,238,210,144,12,191,179,162,241, 81,51,145,235,249,14,239,107,
    49,192,214, 31,181,199,106,157,184, 84,204,176,115,121,50,45,127, 4,150,254,
    138,236,205,93,222,114,67,29,24,72,243,141,128,195,78,66,215,61,156,180)
GRAD3 = [[1,1,0],[-1,1,0],[1,-1,0],[-1,-1,0],
    [1,0,1],[-1,0,1],[1,0,-1],[-1,0,-1], 
    [0,1,1],[0,-1,1],[0,1,-1],[0,-1,-1]]
P = [x & 255 for x in PERMUTATION]


class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Yggdrasil")
        self.protocol('WM_DELETE_WINDOW', self.exit)
        s=ttk.Style()
        s.theme_use('clam')
        print(self.loadfont(FONT_PATH + "apple2.ttf"))
        #print(tk.font.families())
        self.font = tkinter.font.Font(family='Print Char 21', size=12, weight=tkinter.font.NORMAL)
        titleFont = tkinter.font.Font(family='Print Char 21', size=6, weight=tkinter.font.BOLD)
        self.map_string = ttk.Label(self, justify='left', font=titleFont)
        self.map_string.pack()
        self.scroll = tk.Scrollbar(self)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_out = tk.Text(self, width=MAP_WIDTH - 1, height=4, font=self.font)
        self.text_out.pack(fill=tk.Y)
        self.text_in = ttk.Entry(self, width=MAP_WIDTH - 1, font=self.font)
        self.text_in.pack(side=tk.BOTTOM, fill=tk.Y)
        self.scroll.config(command=self.text_out.yview)
        self.text_out.config(yscrollcommand=self.scroll.set)
        self.text_in_button = tk.Button(command=self._save_callback)
        self.bind('<Return>', (lambda e, b=self.text_in_button: b.invoke()))
        self.daytime()
        self.dark = False
        self.map_editable = False
        self.xray = False
        self.text_queue = []
        self.exit = False
        self.paused = True
        self.gameOver = False
        self.player: Player = None
        self.save: Save = None
        self.entities: [Entity] = []
        self.items: [Item] = []
        self.map: [[Tile]] = [[]]
        self.entityMap = [[]]
        self.inventory_index = 0
        self.inventory_display_switch = False
        self.get_save()

    @staticmethod
    def loadfont(fontpath, private=True, enumerable=False):
        '''
        Makes fonts located in file `fontpath` available to the font system.

        `private`     if True, other processes cannot see this font, and this 
                    font will be unloaded when the process dies
        `enumerable`  if True, this font will appear when enumerating fonts

        See https://msdn.microsoft.com/en-us/library/dd183327(VS.85).aspx

        '''
        # This function was taken from
        # https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15
        if isinstance(fontpath, bytes):
            pathbuf = create_string_buffer(fontpath)
            AddFontResourceEx = windll.gdi32.AddFontResourceExA
        elif isinstance(fontpath, str):
            pathbuf = create_unicode_buffer(fontpath)
            AddFontResourceEx = windll.gdi32.AddFontResourceExW
        else:
            raise TypeError('fontpath must be of type bytes or str')
        flags = (FR_PRIVATE if private else 0) | (FR_NOT_ENUM if not enumerable else 0)
        numFontsAdded = AddFontResourceEx(byref(pathbuf), flags, 0)
        return bool(numFontsAdded)

    def nighttime(self):
        self.map_string.configure(background='black', foreground='white')
        self.text_out.configure(background='black', foreground='white')
        self.configure(background='black')
        self.text_in.configure(background='black', foreground='black')

    def daytime(self):
        self.map_string.configure(background='white', foreground='black')
        self.text_out.configure(background='white', foreground='black')
        self.configure(background='#f0f0ed')
        self.text_in.configure(background='white', foreground='black')

    def update_xray(self):
        if self.xray:
            self.nighttime()
        else:
            self.daytime()

    @staticmethod
    def chunkify_text(text):
        for c in range(MAP_WIDTH, len(text) + MAP_WIDTH, MAP_WIDTH):
            if len(text) < MAP_WIDTH:
                yield text[1:]
                break
            end = text[0:c].rfind(" ")
            yield text[0:end + 1]
            text = text[end:]

    def print_ln(self, text):
        if len(text) > MAP_WIDTH:
            chunks = self.chunkify_text(text)
            text = ""
            for c in chunks:
                text += c + "\n"
        else:
            text += "\n"
        self.text_out.config(state=tk.NORMAL)
        self.text_out.insert(tk.END, text)
        self.text_out.config(state=tk.DISABLED)
        self.text_out.see(tk.END)

    def clear_input(self):
        self.text_in.delete(0, tk.END)
        self.text_in.focus()

    def get_save(self):
        titleImageSet = []
        for fname in os.listdir('assets/title'):
            image = ""
            with open('assets/title/' + fname) as f:
                for line in f:
                    image += line
            titleImageSet.append(image)
        title = AnimPlayer(self, titleImageSet)
        self.map_string.config(text=title)
        self.print_ln("Select your save:")
        self.print_ln("(n) — New Game")
        for idx, f in enumerate(os.listdir(SAVE_PATH)):
            self.print_ln("(" + str(idx + 1) + ") — " + f)
        self.clear_input()
        title.start()

    def _save_callback(self):
        saves = os.listdir(SAVE_PATH)
        resp = self.text_in.get()
        self.clear_input()
        if resp == "n":
            self.print_ln("Choose a name")
            self.text_in_button.config(command=self._name_callback)
        else:
            try:
                self._init_callback(self.load_game(saves[int(resp) - 1]))
            except (ValueError, IndexError):
                self.print_ln("Invalid input")

    def _name_callback(self):
        if self.text_in.get():
            if self.text_in.get() not in os.listdir(SAVE_PATH):
                self._init_callback(Save(self.text_in.get()))
            else:
                self.print_ln("Another player is using that name")

    def _init_callback(self, save):
        self.map_string.config(font=self.font)
        self.text_in.delete(0, tk.END)
        self.save = save
        self.player = self.save.player
        self.entities = self.save.entities
        self.map_string.focus()
        self.unfreeze_player()
        self.text_in_button.config(command=lambda: None)
        self.print_ln("Welcome, " + self.player.name)
        self.map = self.load_map(MAPS[self.save.map][0], **MAPS[self.save.map][1])
        self.title("Yggdrasil - " + self.player.name)
        self.game_loop()

    def push_story_text(self, texts):
        if len(texts) == 0:
            return
        self.freeze_player()
        for text in texts:
            self.text_queue.append(text)
        self.bind('<Return>', self._push_story_text_callback)
        self._push_story_text_callback(None)

    def _push_story_text_callback(self, event):
        if len(self.text_queue) == 0:
            self.print_ln('...')
            self.unfreeze_player()
        else:
            self.print_ln(self.text_queue.pop(0))

    def _inventory_callback(self, event):
        self.inventory_display_switch = not self.inventory_display_switch
        if self.inventory_display_switch:
            self.freeze_player()
            self.print_ln("[e] equip")
            self.print_ln("[u] use")
            self.print_ln("[d] drop")
            self.bind('<Escape>', self._inventory_callback)
            self.bind('e', self._equip_callback)
            self.bind('u', self._use_callback)
            self.bind('d', self._drop_callback)
            self.bind('<Return>', (lambda e, b=self.text_in_button: b.invoke()))
        else:
            self.unbind('<Escape>')
            self.unbind('e')
            self.unbind('u')
            self.unbind('d')
            self.unfreeze_player()
            self.clear_input()
            self.map_string.focus()
            self.text_in_button.config(command=lambda: None)
            self.print_ln("...")

    def _equip_callback(self, event):
        if len(self.player.items) == 1:
            self.print_ln("You've only got one item")
        else:
            self.print_ln("Select an item to equip (1-" + str(len(self.player.items) - 1) + ")")
            self.text_in.focus()
            self.text_in_button.config(command=self._equip_pick_callback)

    def _equip_pick_callback(self):
        if self.text_in.get():
            if self.text_in.get() == "0":
                    self.print_ln("You're already holding that")
                    self.clear_input()
            else:
                try:
                    self.map_string.focus()
                    self.player.item = self.player.items[int(self.text_in.get())]
                    self.player.items.insert(0, self.player.items.pop(int(self.text_in.get())))
                    self.print_ln("You take out a " + self.player.item.name)
                    self.clear_input()
                    self.map_string.focus()
                except (ValueError, IndexError):
                    self.print_ln("Invalid input")
                    self.clear_input()
                    self.map_string.focus()

    def _drop_callback(self, event):
        if len(self.player.items) == 1:
            self.print_ln("You've only got one item")
        else:
            self.print_ln("Select an item to drop (1-" + str(len(self.player.items) - 1) + ")")
            self.text_in.focus()
            self.text_in_button.config(command=self._drop_pick_callback)

    def _drop_pick_callback(self):
        if self.text_in.get():
            if self.text_in.get() == "0":
                self.print_ln("You can't drop an equipped item")
                self.clear_input()
                self.map_string.focus()
            else:
                try:
                    i = self.player.items[int(self.text_in.get())]
                    i.x = self.player.x
                    i.y = self.player.y
                    self.items.append(self.player.items.pop(int(self.text_in.get())))
                    self.print_ln("You drop a " + i.name)
                    self.clear_input()
                    self.map_string.focus()
                except (ValueError, IndexError):
                    self.print_ln("Invalid input")
                    self.clear_input()
                    self.map_string.focus()

    def _use_callback(self, event):
        self.print_ln("Select an item to use (0-" + str(len(self.player.items) - 1) + ")")
        self.text_in.focus()
        self.text_in_button.config(command=self._use_pick_callback)

    def _use_pick_callback(self):
        if self.text_in.get():
            try:
                self.player.items[int(self.text_in.get())].use_callback(self.player, self)
                self.clear_input()
                self.map_string.focus()
            except (ValueError, IndexError):
                self.print_ln("Invalid input")
                self.clear_input()
                self.map_string.focus()

    @staticmethod
    def load_game(fname):
        with open(SAVE_PATH + fname, 'rb') as f:
            if f:
                return pickle.load(f)

    def save_game(self):
        with open(SAVE_PATH + self.player.name, 'w+b') as f:
            pickle.dump(self.save, f)

    def load_map(self, fname, storyText=[], specialTiles=[], NPCs=[], items=[], callback=lambda app: None, dark=False, editable=False):
        if fname == None:
            fname = "base-custom-dimension"
        _map = [[]]
        self.entityMap = [[]]
        with open(MAP_PATH + fname, "r") as f:
            for idx, line in enumerate(f):
                _map.append([])
                for tile in line:
                    _map[idx].append(TILES[tile])
        for s in specialTiles:
            try:
                _map[s.x][s.y] = s
            except IndexError:
                pass # Sometimes breaks while changing maps
        self.save.map = fname
        self.entities = [self.player]
        self.items = []
        self.dark = dark
        self.map_editable = editable
        self.spawn_npcs(NPCs)
        for i in items:
            if i.iid not in self.player.checkpoints['item_ids']:
                self.items.append(i)
        if not (fname in self.player.checkpoints['levels']):
            self.player.checkpoints['levels'].append(fname)
            self.push_story_text(storyText)
        callback(self)
        return _map

    def exit(self):
        if self.save:
            self.save_game()
        self.exit = True
        self.destroy()

    def freeze_player(self):
        self.paused = True
        self.unbind('w')
        self.unbind('<Up>')
        self.unbind('s')
        self.unbind('<Down>')
        self.unbind('a')
        self.unbind('<Left>')
        self.unbind('d')
        self.unbind('<Right>')
        self.unbind('<Return>')
        self.unbind('<Shift_L>')
        self.unbind('<Shift_R>')
        self.unbind(',')
        self.unbind('i')

    def unfreeze_player(self):
        self.paused = False
        self.bind('w', lambda e=self.entityMap: self.player.move(self.map, self.entityMap, (-1, 0), self))
        self.bind('<Up>', lambda e=self.entityMap: self.player.move(self.map, self.entityMap, (-1, 0), self))
        self.bind('s', lambda e=self.entityMap: self.player.move(self.map, self.entityMap, (1, 0), self))
        self.bind('<Down>', lambda e=self.entityMap: self.player.move(self.map, self.entityMap, (1, 0), self))
        self.bind('a', lambda e=self.entityMap: self.player.move(self.map, self.entityMap, (0, -1), self))
        self.bind('<Left>', lambda e=self.entityMap: self.player.move(self.map, self.entityMap, (0, -1), self))
        self.bind('d', lambda e=self.entityMap: self.player.move(self.map, self.entityMap, (0, 1), self))
        self.bind('<Right>', lambda e=self.entityMap: self.player.move(self.map, self.entityMap, (0, 1), self))
        self.bind('<Return>', lambda e=self: self.player.use(self))
        self.bind('<Shift_L>', lambda e=self: self.player.use_secondary(self))
        self.bind('<Shift_R>', lambda e=self: self.player.use_secondary(self))
        self.bind(',', lambda e=self.items: self.player.pick_up(self, self.items))
        self.bind('i', self._inventory_callback)

    def update_entities(self):
        if self.xray:
            self.player.health -= .1
        self.entityMap = [[]]
        for idx, row in enumerate(self.map):
            self.entityMap.append([])
            for val in row:
                self.entityMap[idx].append(Entity("", [val.image], math.inf, val.solid, (0, 0)))
        for idx, e in enumerate(self.entities):
            if e.health <= 0:
                if isinstance(e, Player):
                    self.gameOver = True
                self.entities[idx].death_callback(self)
                self.entities.pop(idx)
            self.draw_entity(e)
        for e in self.entities:
            e.update(self.map, self.entityMap, self)
            for a in e.appendages:
                a.update(self.entityMap, self)
                self.draw_appendage(e, a)
        for i in self.items:
            i.update(self.map, self.entityMap, self)
        for j in self.player.items:
            j.update(self.map, self.entityMap, self)

    def spawn_entities(self):
        if self.save.map in SPAWN_TABLES:
            for e in SPAWN_TABLES[self.save.map]:
                if random.randint(0, e[1]) == 0:
                    x = random.randint(0, len(self.map) - 2)
                    y = random.randint(0, len(self.map[0]) - 2)
                    try:
                        if not self.entityMap[x][y].solid:
                            self.entities.append(Enemy(*e[0], (x, y)))
                    except IndexError:
                        pass # This occasionally throws an IndexError while changing maps

    def spawn_npcs(self, NPCs):
        for n in NPCs:
            if n['name'] not in self.player.killedNPCs:
                if 'deathMessage' in n:
                    self.entities.append(NPC(n['name'], n['image'], n['health'], (n['x'], n['y']), deathMessage=n['deathMessage']))
                else:
                    self.entities.append(NPC(n['name'], n['image'], n['health'], (n['x'], n['y'])))

    def draw_entity(self, e):
        self.entityMap[e.x][e.y] = e

    def draw_appendage(self, e, a):
        self.entityMap[e.x + a.x][e.y + a.y] = a

    def render_map(self):
        rendered_map = [[]]
        for idx, row in enumerate(self.entityMap):
            rendered_map.append([])
            for idy, val in enumerate(row):
                if self.dark and not self.xray and str(val) != "\n":
                    dx = abs(self.player.x - idx)
                    dy = abs(self.player.y - idy)
                    for a in self.player.appendages:
                        dx = min(dx, abs(self.player.x + a.x - idx))
                        dy = min(dy, abs(self.player.y + a.y - idy))
                    d = math.floor(math.sqrt(dx ** 2 + dy ** 2))
                    if isinstance(val, ItemUser) or isinstance(val, EntityAppendage) or isinstance(val, Projectile):
                        if d <= self.player.seeRadius + 3:
                            rendered_map[idx].append(val)
                        else:
                            rendered_map[idx].append("█")
                    elif d <= self.player.seeRadius:
                        rendered_map[idx].append(val)
                    elif d <= self.player.seeRadius + 1:
                        rendered_map[idx].append("░")
                    elif d <= self.player.seeRadius + 2:
                        rendered_map[idx].append("▒")
                    elif d <= self.player.seeRadius + 3:
                        rendered_map[idx].append("▓")
                    else:
                        rendered_map[idx].append("█")
                else:
                    rendered_map[idx].append(val)
        for i in self.items:
            if not self.entityMap[i.x][i.y].solid:
                if rendered_map[i.x][i.y] != "█":
                    rendered_map[i.x][i.y] = i
        if len(rendered_map[0]) > MAP_WIDTH:
            if self.player.y < MAP_WIDTH / 2:
                for idx, row in enumerate(rendered_map):
                    rendered_map[idx] = row[:MAP_WIDTH]
                    rendered_map[idx].append(TILES["\n"])
            elif len(rendered_map[0]) - self.player.y - 1 < MAP_WIDTH / 2:
                for idx, row in enumerate(rendered_map):
                    rendered_map[idx] = row[len(self.entityMap[0]) - MAP_WIDTH - 1:]
            else:
                for idx, row in enumerate(rendered_map):
                    rendered_map[idx] = row[self.player.y - int(MAP_WIDTH / 2) - 1:self.player.y + int(MAP_WIDTH / 2)]
                    rendered_map[idx].append(TILES["\n"])
        while len(rendered_map[-1]) == 0 or len(rendered_map[-1]) == 1:
            rendered_map.pop()
        if len(rendered_map) > MAP_HEIGHT:
            self.text_out.config(height=4)
            if self.player.x < MAP_HEIGHT / 2:
                rendered_map = rendered_map[:MAP_HEIGHT]
            elif len(rendered_map) - self.player.x - 1 < MAP_HEIGHT / 2:
                rendered_map = rendered_map[len(self.entityMap) - MAP_HEIGHT - 2:]
            else:
                rendered_map = rendered_map[self.player.x - int(MAP_HEIGHT / 2) - 1:self.player.x + int(MAP_HEIGHT / 2)]
        else:
            self.text_out.config(height=4 + MAP_HEIGHT - len(rendered_map))
        frame = 'Health [' + ('='*int(self.player.health * 10 / MAX_HEALTH)).ljust(10) + '] ' + str(round(self.player.health)) + '\n'
        for row in rendered_map:
            for tile in row:
                frame += str(tile)
        if frame[-1] == "\n":
            frame = frame[:-1]
        self.map_string.config(text=frame)

    def render_inventory(self):
        frame = "Inventory\n" + "—"*MAP_WIDTH + "\n"
        iMax = MAP_HEIGHT - 3
        i = MAP_HEIGHT - 3
        n = MAP_HEIGHT - 3
        while i > 0:
            try:
                prefix = self.player.items[(iMax - n) + self.inventory_index].images + " "
                postfix = ""
                if self.player.items[(iMax - n) + self.inventory_index].count > 1:
                    postfix += " (" + str(self.player.items[(iMax - n) + self.inventory_index].count) + ")"
                if self.player.item.name == self.player.items[(iMax - n) + self.inventory_index].name:
                    postfix += " (equipped)"
                if (iMax - n) + self.inventory_index == 1:
                    postfix += " (secondary)"
                line = "[" + str((iMax - n) + self.inventory_index) + "] " + prefix + self.player.items[(iMax - n) + self.inventory_index].name.capitalize() + postfix + "\n"
                if len(line) > MAP_WIDTH:
                    line = "[" + str((iMax - n) + self.inventory_index) + "] " + prefix + self.player.items[(iMax - n) + self.inventory_index].name.capitalize() + "\n     " + postfix + "\n"
                    i -= 1
            except IndexError:
                line = "\n"
            frame += line
            i -= 1
            n -= 1
        self.text_out.config(height=5)
        self.map_string.config(text=frame)
        self.text_out.see(tk.END)

    def game_loop(self):
        self.paused = False
        while not self.exit: # and not self.paused:
            if self.inventory_display_switch:
                self.render_inventory()
            else:
                self.spawn_entities()
                self.update_entities()
                if self.gameOver:
                    self.game_over()
                    self.gameOver = False
                    continue
                self.render_map()
            self.after(int(TICK_DELAY * 1000), self.update())

    @staticmethod
    def generate_item(item, pos, iid=None):
        i = ITEMS[item]
        return Item(*i[0], pos, **i[1], iid=iid)

    def game_over(self):
        self.print_ln("GAME OVER")
        self.after(3000, self.restart)

    def restart(self):
        self.save = Save(self.player.name)
        self.player.health = 50
        self.player.x = 8
        self.player.y = 0
        self.save.player = self.player
        self.entities: [Entity] = self.save.entities
        self.map = self.load_map(MAPS[self.save.map][0], **MAPS[self.save.map][1])
        self.update_entities()
        self.bind('<Return>', lambda e=self: self.player.use(self))
        self.print_ln('...')


class AnimPlayer:
    def __init__(self, master, imageSet):
        self.master = master
        self.imageSet = imageSet
    
    def start(self):
        while self.master.paused:
            for i in self.imageSet:
                if self.master.exit:
                    return
                self.master.map_string.config(text=i)
                self.master.after(int(TICK_DELAY * 5000), self.master.update())


class Mines:
    chunks = []

    def update(self, master):
        if master.player.x <= MAP_WIDTH / 2 + 1:
            pass

    @staticmethod
    def load_chunk(X, Y, seed):
        return ([
            [ProceduralTerrain.generate_mine_tile(x, y, seed=seed) for y in range(32)]
            for x in range(64)
        ], (X, Y))

    @staticmethod
    def generate_map(map):
        _map = []
        chunks = []
        for c in chunks:
            pass


class ProceduralTerrain:
    @staticmethod
    def dot(g, x, y):
        return g[0]*x + g[1]*y

    @staticmethod
    def simplex_noise(xin, yin):
        n0, n1, n2 = 0, 0, 0
        F2 = .5 * (math.sqrt(3) - 1)
        s = (xin + yin) * F2
        i, j = math.floor(xin + s), math.floor(yin + s)
        G2 = (3 - math.sqrt(3)) / 6
        t = (i + j) * G2
        X0 = i - t
        Y0 = j - t
        x0 = xin - X0
        y0 = yin - Y0
        i1, j1 = 0, 1
        if x0 > y0:
            i1 = 1
            j1 = 0
        x1 = x0 - i1 + G2
        y1 = y0 - j1 + G2
        x2 = x0 - 1 + 2 * G2
        y2 = y0 - 1 + 2 * G2
        ii = i & 255
        jj = j & 255
        gi0 = P[ii + P[jj]] % 12
        gi1 = P[ii + i1+ P[jj + j1]] % 12
        gi2 = P[ii + 1 + P[jj + 1]] % 12
        t0 = .5 - x0*x0 - y0*y0
        if t0 < 0:
            n0 = 0
        else:
            t0 *= t0
            n0 = t0*t0 * ProceduralTerrain.dot(GRAD3[gi0], x0, y0)
        t1 = .5 - x1*x1 - y1*y1
        if t1 < 0:
            n1 = 0
        else:
            t1 *= t1
            n1 = t1*t1 * ProceduralTerrain.dot(GRAD3[gi1], x1, y1)
        t2 = .5 - x2*x2 - y2*y2
        if t2 < 0:
            n2 = 0
        else:
            t2 *= t2
            n2 = t2*t2 * ProceduralTerrain.dot(GRAD3[gi2], x2, y2)
        return 70 * (n0 + n1 + n2)

    @staticmethod
    def generate_mine_tile(x, y, seed=0):
        weight = ProceduralTerrain.simplex_noise(x/20 + seed, y/20 + seed) + ProceduralTerrain.simplex_noise(x/5 + seed, y/5 + seed)*.5
        if weight < .1:
            return TILES["#"]
        elif weight < .3:
            return TILES["."]
        elif weight < .35:
            return TILES["-"]
        else:
            return TILES[" "]


class Tileizable:
    def __init__(self, solid):
        self.solid = solid


class Tile(Tileizable):
    def __init__(self, image, solid):
        super().__init__(solid)
        self.image = image

    def __repr__(self):
        return self.image

    def trigger(self, app, player):
        pass


class Portal(Tile):
    def __init__(self, image, pos, pos_to, map_to):
        super().__init__(image, False)
        self.mapTo = map_to
        self.y, self.x = pos
        self.y_to, self.x_to = pos_to

    def trigger(self, app, player):
        app.map = app.load_map(MAPS[self.mapTo][0], **MAPS[self.mapTo][1])
        player.x, player.y = self.x_to, self.y_to


class MineShaft(Tile):
    def __init__(self, image, pos):
        super().__init__(image, False)
        self.y, self.x = pos

    def trigger(self, app, player):
        app.entityMap = [[]]
        _map = Mines.load_chunk(0, 0, app.save.MINE_SEED)[0]
        for row in _map:
            row.append(TILES["\n"])
        app.save.map = 'mine'
        app.entities = [player]
        app.items = []
        app.dark = True
        self.map_editable = True
        if not ('mine' in player.checkpoints['levels']):
            player.checkpoints['levels'].append('mine')
        player.x, player.y = 15, 15
        app.map = _map


class Entity(Tileizable):
    def __init__(self, name, images, health, solid, pos):
        super().__init__(solid)
        self.name = name
        self.images = images
        self.currentImage = self.images[0]
        self.appendages = []
        self.x, self.y = pos
        self.health = health

    def __repr__(self):
        return self.currentImage

    def update(self, map, emap, app):
        pass

    def move(self, map, emap, disp, app):
        try:
            if not map[self.x + disp[0]][self.y + disp[1]].solid and not emap[self.x + disp[0]][self.y + disp[1]].solid:
                self.x += disp[0]
                self.y += disp[1]
        except IndexError:
            pass  # Sometimes while changing maps this will throw an IndexError

    def take_damage(self, app, d):
        self.health -= d

    def death_callback(self, app):
        pass


class EntityAppendage(Tileizable):
    def __init__(self, master, disp, dir, image, lifespan, damage=0, piercing=False, solid=False, next_appendage=None):
        super().__init__(solid)
        self.master = master
        self.x, self.y = disp
        self.dirx, self.diry = dir
        self.image = image
        self.remaining_age = lifespan
        self.damage = damage
        self.piercing = piercing
        self.next = next_appendage

    def __repr__(self):
        return self.image

    def update(self, emap, app):
        self.remaining_age -= 1
        if self.remaining_age < 1:
            self.delete()
        emap[self.master.x + self.dirx][self.master.y + self.diry].take_damage(app, self.damage)
        # Sword can damage enemy in front of itself
        if self.piercing:
            emap[self.master.x + self.dirx][self.master.y + self.diry * 2].take_damage(app, self.damage)

    def take_damage(self, app, d):
        pass  # EntityAppendages are added to EntityMap, so this function is rarely called

    def delete(self):
        if self.next:
            self.master.appendages.append(self.next)
        self.master.appendages.pop(0)


class ItemUser(Entity):
    def __init__(self, name, images, health, solid, item, pos):
        super().__init__(name, images, health, solid, pos)
        self.item = item
        self.items: [Item] = [self.item]
        self.direction = 1

    def move(self, map, emap, disp, app):
        super().move(map, emap, disp, app)
        if disp[1] == 1:
            self.direction = 1
        elif disp[1] == -1:
            self.direction = -1

    def use(self, app):
        self.item.use_callback(self, app)

    def use_secondary(self, app):
        if len(self.items) > 1:
            self.items[1].use_callback(self, app)
        else:
            app.print_ln("No secondary item available")


class Player(ItemUser):
    def __init__(self, name, item, pos):
        super().__init__(name, ['¥'], 100, True, item, pos)
        self.checkpoints = {'levels': [], 'item_ids': []}
        self.modifiedLevels = []
        self.inventory = []
        self.killedNPCs = []
        self.seeRadius = 3

    def move(self, map, emap, disp, app):
        super().move(map, emap, disp, app)
        map[self.x][self.y].trigger(app, self)

    def pick_up(self, app, itemSet):
        for idx, i in enumerate(itemSet):
            if self.x == i.x and self.y == i.y:
                app.print_ln("[You pick up a " + i.name + "]")
                try:
                    if i.iid != None:
                        self.checkpoints['item_ids'].append(i.iid)
                except AttributeError:
                    pass
                for j in self.items:
                    if i.name == j.name:
                        j.count += 1
                        itemSet.pop(idx)
                        return
                self.items.append(itemSet.pop(idx))


class Enemy(ItemUser):
    def __init__(self, name, images, health, solid, speed, item, pos):
        super().__init__(name, images, health, solid, item, pos)
        self.speed = speed

    def update(self, map, emap, app):
        moveable = (random.randint(0, TICK_FREQUENCY) + 1) * self.speed > TICK_FREQUENCY
        if moveable:
            self.move(map, emap, (random.randint(-1, 1), random.randint(-1, 1)), app)
        if abs(app.player.x - self.x) <= 5 and abs(app.player.y - self.y) <= 5 and app.player.y - self.y != 0:
            self.direction = int((app.player.y - self.y) / abs(app.player.y - self.y))
            if random.randint(0, TICK_FREQUENCY) == 0:
                self.use(app)

    def death_callback(self, app):
        app.print_ln("[The " + self.name + " is slain]")
        if self.name in DROP_TABLES:
            for item in DROP_TABLES[self.name]:
                if random.randint(1, 100) <= DROP_TABLES[self.name][item]*100:
                    app.items.append(app.generate_item(item, (self.x, self.y)))


class Stag(Enemy):
    def __init__(self, name, health, speed, item, secondaryItem, pos):
        super().__init__(name, "V", health, True, speed, item, pos)
        self.appendages.append(EntityAppendage(self, (-1, 0), (-1, 0),"Y", math.inf, damage=item.damage, piercing=False))
        self.appendages.append(EntityAppendage(self, (0, -self.direction), (0, -self.direction),"=", math.inf, damage=item.damage, piercing=False))
        self.appendages.append(self.generate_leg((1, 1)))
        self.appendages.append(self.generate_leg((1, -1)))
        self.items.append(secondaryItem)

    def update(self, map, emap, app):
        dy = app.player.x - self.x
        dx = app.player.y - self.y
        moveable = (random.randint(0, TICK_FREQUENCY) + 1) * self.speed > TICK_FREQUENCY
        if moveable:
            if abs(dx) <= 5 and dx != 0:
                self.move(map, emap, (0, int(-dx / abs(dx))), app)
                self.appendages[2] = self.generate_leg((1, 1))
                self.appendages[3] = self.generate_leg((1, -1))
            elif abs(dx) >= 10 and dx != 0:
                self.move(map, emap, (0, int(dx / abs(dx))), app)
                self.appendages[2] = self.generate_leg((1, 1))
                self.appendages[3] = self.generate_leg((1, -1))
            if dy != 0:
                self.move(map, emap, (int(dy / abs(dy)), 0), app)
                self.appendages[2] = self.generate_leg((1, 1))
        usable = True #random.randint(0, round(TICK_FREQUENCY / 4)) == 0
        self.use_secondary(app)
        # if usable and dy != 0:
        #     self.direction = int((dy) / abs(dy))
        #     if abs(app.player.x - self.x) <= 5 and abs(app.player.y - self.y) <= 5 and app.player.y - self.y != 0:
        #         self.use(app)
        #     else:
        #         self.use_secondary(app)

    def generate_leg(self, offset):
        state = (self.x + self.y + offset[1]) % 3
        if state:
            return EntityAppendage(self, offset, offset,"\\", math.inf, damage=self.item.damage, piercing=False)
        else:
            return EntityAppendage(self, offset, offset,"|", math.inf, damage=self.item.damage, piercing=False)


class NPC(Entity):
    def __init__(self, name, images, health, pos, deathMessage=[]):
        super().__init__(name, images, health, True, pos)
        self.deathMessage = deathMessage

    def death_callback(self, app):
        app.push_story_text(self.deathMessage)
        app.player.killedNPCs.append(self.name)


class Item(Entity):
    def __init__(self, name, image, use_callback, pos, damage=0, regen=0, consumable=False, placeable=False, iid=None):
        super().__init__(name, image, math.inf, False, pos)
        self.damage = damage
        self.regen = regen
        self.consumable = consumable
        self.placeable = placeable
        self.iid = iid
        self.count = 1
        self.use_callback = lambda *args, **kwargs: use_callback(self, *args, **kwargs)


class Projectile(Entity):
        def __init__(self, name, images, vel, pos):
            super().__init__(name, images, math.inf, False, pos)
            self.vel = vel

        def update(self, map, emap, app):
            self.move(map, emap, self.vel, app)
            if emap[self.x + self.vel[0]][self.y + self.vel[1]].solid:
                self.health = 0


class Sword(Item):
    def __init__(self, name, damage, pos, iid=None):
        super().__init__(name, "/", sword_callback, pos, damage=damage, iid=iid)


class Bow(Item):
    def __init__(self, name, damage, pos, iid=None):
        super().__init__(name, ")", bow_callback, pos, damage=damage, iid=iid)
        self.cooldown = 0

    def update(self, map, emap, app):
        if self.cooldown > 0:
            self.cooldown -= 1


class Shield(Item):
    def __init__(self, name, max_cooldown, pos, iid=None):
        super().__init__(name, "Ø", shield_callback, pos, iid=iid)
        self.max_cooldown = max_cooldown
        self.cooldown = 0

    def update(self, map, emap, app):
        if self.cooldown > 0:
            self.cooldown -= 1


class Heal(Item):
    def __init__(self, name, regen, pos, iid=None):
        super().__init__(name, "e", heal_callback, pos, regen=regen, iid=iid)


class WorldSeed(Item):
    def __init__(self, name, pos, iid=None):
        super().__init__(name, "¤", seed_callback, pos, iid=iid)
        self.map_to = "base-custom-dimension"
        self.coords_to = (9, 12)


class Save:
    def __init__(self, name):
        self.player = Player(name, Sword(*WEAPONS['Rusty Sword'], (8, 0)), (8, 0))
        self.entities = []
        self.map = "01"
        self.MINE_SEED = random.random()
        while ProceduralTerrain.generate_mine_tile(self.MINE_SEED + 15, self.MINE_SEED + 15).solid:
            self.MINE_SEED = random.random()


def sword_callback(item, master, app):
        if not app.entityMap[master.x][master.y + master.direction].solid:
            if len(master.appendages) == 0:
                if master.direction == 1:
                    master.appendages.append(EntityAppendage(master, (0, master.direction), (0, master.direction), "/", 1, damage=item.damage, piercing=False,
                                                           next_appendage=EntityAppendage(master, (0, master.direction), (0, master.direction),  "—",
                                                                                          12, damage=item.damage, piercing=True,
                                                                                          next_appendage=EntityAppendage(
                                                                                              master, (0, master.direction), (0, master.direction),
                                                                                              "/", 1, damage=item.damage,
                                                                                              piercing=False))))
                elif master.direction == -1:
                    master.appendages.append(EntityAppendage(master, (0, master.direction), (0, master.direction), "\\", 1, damage=item.damage, piercing=False,
                                                           next_appendage=EntityAppendage(master, (0, master.direction), (0, master.direction), "—",
                                                                                          12, damage=item.damage, piercing=True,
                                                                                          next_appendage=EntityAppendage(
                                                                                              master, (0, master.direction), (0, master.direction),
                                                                                              "\\", 1, damage=item.damage,
                                                                                              piercing=False))))
            elif master.appendages[-1].image == "—":
                master.appendages[-1].remaining_age = 3

def katana_callback(item, master, app):
    if not app.entityMap[master.x][master.y + master.direction].solid:
        if len(master.appendages) == 0:
            if master.direction == 1:
                pass
            elif master.direction == -1:
                pass
                
def bow_callback(item, master, app):
    if not app.entityMap[master.x][master.y + master.direction].solid:
        if len(master.appendages) == 0:
            if master.direction == 1:
                master.appendages.append(EntityAppendage(master, (0, master.direction), (0, master.direction),")", 12))
            elif master.direction == -1:
                master.appendages.append(EntityAppendage(master, (0, master.direction), (0, master.direction),"(", 12))
        elif master.appendages[-1].image == ")":
            master.appendages[-1].remaining_age = 3
        elif master.appendages[-1].image == "(":
            master.appendages[-1].remaining_age = 3
        if item.cooldown == 0:
            arrow = Projectile('arrow', '*', (0, master.direction), (master.x, master.y + master.direction))
            app.entities.append(arrow)
            if master.direction == 1:
                arrow.appendages.append(EntityAppendage(arrow, (0, -1), (0, 1), "→", math.inf, damage=item.damage, piercing=False))
            elif master.direction == -1:
                arrow.appendages.append(EntityAppendage(arrow, (0, 1), (0, -1), "←", math.inf, damage=item.damage, piercing=False))
            item.cooldown = int(TICK_FREQUENCY / 3)


def shield_callback(item, master, app):
    if not app.entityMap[master.x][master.y + master.direction].solid:
        if item.cooldown == 0:
            if master.direction == 1:
                master.appendages.append(EntityAppendage(master, (0, master.direction), (0, master.direction),"]", 12, solid=True))
            elif master.direction == -1:
                master.appendages.append(EntityAppendage(master, (0, master.direction), (0, master.direction),"[", 12, solid=True))
            item.cooldown = item.max_cooldown


def heal_callback(item, master, app):
        old_health = master.health
        master.health += item.regen
        if master.health > 100:
            master.health = 100
        app.print_ln("[You are healed for " + str(master.health - old_health) + " hp]")
        if item.consumable:
            item.count -= 1
            if item.count <= 0:
                for idx, i in enumerate(master.items):
                    if i.name == item.name:
                        master.items.pop(idx)
                        if i.name == master.item.name:
                            master.item = master.items[0]
                        return

def xray_callback(item, master, app):
    app.xray = not app.xray
    app.update_xray()
    if app.xray:
        app.print_ln("[X-ray vision activated]")
    else:
        app.print_ln("[X-ray vision deactivated]")

def seed_callback(item, master, app):
    old_map = app.save.map
    old_coords = (master.x, master.y)
    app.map = app.load_map(MAPS[item.map_to][0], **MAPS[item.map_to][1])
    master.x, master.y = item.coords_to[0], item.coords_to[1]
    if old_map != "mine":
        item.map_to = old_map
    else:
        item.map_to = "base-custom-dimension"
    item.coords_to = old_coords

def placeable_callback(item, master, app):
    pass

def stag1(app):
    app.entities.append(Stag("1", 500, 3, Sword(*WEAPONS['Rusty Sword'], (0, 0)), Bow(*WEAPONS['Wooden Bow'], (0, 0)), (10, 13)))


TILES = {
    "\n": Tile("\n", True),
    " ": Tile(" ", False),
    ".": Tile(".", False),
    "#": Tile("#", True),
    "-": Tile("░", False),
    "_": Tile("▒", False),
    "^": Tile("▓", False),
    "*": Tile("█", False),
    "[": Tile("[", True),
    "]": Tile("]", True),
    "/": Tile("/", True),
    "b": Tile("\\", True),
    "r": Tile("¯", True),
    "d": Tile("◘", False),
    "6": Tile("═", True),
    "8": Tile("║", True),
    "1": Tile("╚", True),
    "3": Tile("╝", True),
    "7": Tile("╔", True),
    "9": Tile("╗", True),
    "5": Tile("│", True),
    "z": Tile("╘", True),
    "x": Tile("╛", True),
    "c": Tile("╒", True),
    "v": Tile("╕", True),
    "n": Tile("╩", True),
    "e": Tile("╠", True),
    "s": Tile("╦", True),
    "w": Tile("╣", True),
}

ITEMS = {
    'Gold Piece': (('gold piece', '$', lambda item, master, app: None), {}),
    'Worm Flesh': (('piece of worm flesh', 'e', heal_callback), {'regen': 30, 'consumable': True}),
    'Red Potion': (('red potion', 'p', heal_callback), {'regen': 50, 'consumable': True}),
    'X-Ray Spell': (('x-ray spell', '§', xray_callback), {}),    
}

WEAPONS = {
    'Rusty Sword': ('rusty sword', 1),
    'Steel Sword': ('steel sword', 3),
    'Wooden Bow': ('wooden bow', 5),
    'Wooden Shield': ('wooden shield', 30)
}

MONSTERS = {
    'Worm': ('Worm', '~', 10, True, 1, Sword(*WEAPONS['Rusty Sword'], (0, 0))),
    'Kobold': ('Kobold', 'k', 20, True, 1.25, Sword(*WEAPONS['Rusty Sword'], (0, 0)))
}

DROP_TABLES = {
    'Worm': {'Worm Flesh': .25},
    'Kobold': {'Gold Piece': .5}
}

SPAWN_TABLES = {
    '01': [(MONSTERS['Worm'], 90)],
    '02': [(MONSTERS['Worm'], 90)],
    '04-h1-r2': [(MONSTERS['Kobold'], 40)],
    '04-h1-r4': [(MONSTERS['Kobold'], 40)],
}

MAPS = {
    'base-custom-dimension': ('base-custom-dimension', {'editable': True,
        'specialTiles': [
            MineShaft("▓", (7, 7))
        ]}),
    '01': ('01', {'storyText':[
            'You are in a cave deep underground (Enter to continue...).',
            'You have wandered here for many years without ever finding anything of interest.'
        ],
        'specialTiles': [
            Portal(".", (41, 4), (1, 12), "02"),
            Portal(".", (41, 5), (1, 13), "02"),
            Portal(".", (41, 6), (1, 14), "02"),
            Portal(".", (41, 7), (1, 15), "02"),
            Portal(".", (41, 8), (1, 16), "02"),
            Portal(".", (41, 9), (1, 17), "02"),
            Portal(".", (41, 10), (1, 18), "02"),
            Portal(".", (41, 11), (1, 19), "02"),
            Portal(".", (41, 12), (1, 20), "02"),
            Portal(".", (41, 13), (1, 21), "02"),
        ], 'items': [
            WorldSeed('World Seed', (6, 8), iid=-1),
            Shield(*WEAPONS['Wooden Shield'], (5, 7), iid=0)
        ]
    }),
    '02': ('02', {'storyText': [
            'You enter a large cavern.'
        ],
        'specialTiles': [
            Portal(" ", (0, 12), (40, 4), "01"),
            Portal(" ", (0, 13), (40, 5), "01"),
            Portal(" ", (0, 14), (40, 6), "01"),
            Portal(" ", (0, 15), (40, 7), "01"),
            Portal(" ", (0, 16), (40, 8), "01"),
            Portal(" ", (0, 17), (40, 9), "01"),
            Portal(" ", (0, 18), (40, 10), "01"),
            Portal(" ", (0, 19), (40, 11), "01"),
            Portal(" ", (0, 20), (40, 12), "01"),
            Portal(" ", (0, 21), (40, 13), "01"),
            Portal(" ", (130, 13), (1, 3), "03"),
            Portal(" ", (130, 14), (1, 4), "03"),
            Portal(" ", (130, 15), (1, 5), "03"),
            Portal(" ", (130, 16), (1, 6), "03"),
            Portal(" ", (130, 17), (1, 7), "03"),
            Portal(" ", (130, 18), (1, 8), "03"),
            Portal(" ", (130, 19), (1, 9), "03"),
            Portal(" ", (130, 20), (1, 10), "03")
        ]
    }),
    '03': ('03', {'storyText': [
            '[Old Man] A wanderer, you say?',
            '[Old Man] We don\'t get many of those down here.',
            '[Old Man] Hmm...'
        ],
        'specialTiles': [
            Portal(".", (0, 3), (129, 13), "02"),
            Portal(".", (0, 4), (129, 14), "02"),
            Portal(".", (0, 5), (129, 15), "02"),
            Portal(".", (0, 6), (129, 16), "02"),
            Portal(".", (0, 7), (129, 17), "02"),
            Portal(".", (0, 8), (129, 18), "02"),
            Portal(".", (0, 9), (129, 19), "02"),
            Portal(".", (0, 10), (129, 20), "02"),
            Portal(" ", (85, 0), (51, 31), "04"),
            Portal(" ", (86, 0), (52, 31), "04"),
            Portal("@", (0, 14), (3, 2), "s1"),
        ], 'NPCs': [
            {'name': 'Old Man', 'image': 'O', 'health': 100, 'x': 10, 'y': 10,
            'deathMessage': ['You kill the old man!', 'You are a terrible person.']}
        ]
    }),
    '04': ('04', {'specialTiles': [
            Portal(".", (51, 32), (85, 1), "03"), 
            Portal(".", (52, 32), (85, 1), "03"),
            Portal("▏", (36, 18), (10, 5), "04-h1-r1"),
            Portal("▕", (37, 18), (11, 5), "04-h1-r1"),
        ]
    }),
    '04-h1-r1': ('04-h1-r1', {'storyText': [
            '[Hermit] Welcome to my humble abode.',
            '[Hermit] Please make yourself at home.',
            '[Hermit] Just don\'t go into the basement.',
            '[Hermit] I\'m afraid it has quite the infestation.',
            '[Hermit] But if you insist on going, take my x-ray spell.',
            '[Hermit] It\'ll let you see in the dark, but you\'ll gradually lose health from the radiation poisoning while it\'s active, so use it sparingly.'
        ],
        'specialTiles': [
            Portal("▏", (10, 6), (36, 19), "04"),
            Portal("▕", (11, 6), (37, 19), "04"),
            Portal("▓", (19, 2), (3, 2), "04-h1-r2"),
        ], 'NPCs': [
            {'name': 'Hermit', 'image': 'H', 'health': math.inf, 'x': 3, 'y': 3}
        ], 'items': [
            App.generate_item('X-Ray Spell', (4, 5), iid=4)
        ]
    }),
    '04-h1-r2': ('04-h1-r2', {'storyText': [
            'You enter a dimly lit cellar.'
        ],
        'specialTiles': [
            Portal("┗", (3, 2), (19, 2), "04-h1-r1"),
            Portal("▓", (21, 27), (20, 9), "04-h1-r3"),
        ], 'items': [
            Sword(*WEAPONS['Steel Sword'], (16, 41), iid=3),
        ], 'dark': True
    }),
    '04-h1-r3': ('04-h1-r3', {'specialTiles': [
            Portal("┗", (20, 9), (21, 27), "04-h1-r2"),
            Portal(" ", (19, 54), (36, 1), "04-h1-r4"),
            Portal(" ", (20, 54), (37, 1), "04-h1-r4"),
            Portal(" ", (21, 54), (38, 1), "04-h1-r4"),
            Portal(" ", (22, 54), (39, 1), "04-h1-r4"),
        ]
    }),
    '04-h1-r4': ('04-h1-r4', {'specialTiles': [
            Portal(" ", (36, 0), (19, 53), "04-h1-r3"),
            Portal(" ", (37, 0), (20, 53), "04-h1-r3"),
            Portal(" ", (38, 0), (21, 53), "04-h1-r3"),
            Portal(" ", (39, 0), (22, 53), "04-h1-r3"),
        ], 'callback': stag1}),
    's1': ('s1', {'storyText': [
            'You stumble upon a secret chamber.'
        ],
        'specialTiles': [
            Portal("@", (3, 3), (0, 15), "03"),
        ], 'items': [
            Bow(*WEAPONS['Wooden Bow'], (1, 1), iid=1),
            App.generate_item('Red Potion', (4, 5), iid=2)
        ]
    }),
    'mine': (None, {})
}

if __name__ == "__main__":
    root = App()
    root.mainloop()
