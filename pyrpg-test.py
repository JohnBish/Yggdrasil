import os
import math
import random
import dill as pickle
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font
#Necessary for custom font
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


class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Yggdrasil")
        self.protocol('WM_DELETE_WINDOW', self.exit)
        s=ttk.Style()
        s.theme_use('clam')
        print(self.loadfont(FONT_PATH + "DejaVuSansMono.ttf"))
        dejavusansmono = tkinter.font.Font(family='DejaVu Sans Mono', size=15, weight=tkinter.font.NORMAL)
        self.map_string = tk.Text(self, width=MAP_WIDTH, height=MAP_HEIGHT + 1)
        self.map_string.config(font=dejavusansmono)
        self.map_string.tag_config('mono', spacing1=-10)
        self.map_string.pack()
        self.scroll = tk.Scrollbar(self)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_out = tk.Text(self, width=MAP_WIDTH - 1, height=4, font=dejavusansmono)
        self.text_out.pack(fill=tk.Y)
        self.text_in = ttk.Entry(self, width=MAP_WIDTH - 1, font=dejavusansmono)
        self.text_in.pack(side=tk.BOTTOM, fill=tk.Y)
        self.scroll.config(command=self.text_out.yview)
        self.text_out.config(yscrollcommand=self.scroll.set)
        self.text_in_button = tk.Button(command=self._save_callback)
        self.bind('<Return>', (lambda e, b=self.text_in_button: b.invoke()))
        self.daytime()
        self.dark = False
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
        self.text_in.configure(background='black', foreground='white')

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

    def set_map_frame(self, text):
        self.map_string.config(state="normal")
        self.map_string.delete('1.0', tk.END)
        self.map_string.insert(tk.END, text, 'mono')
        self.map_string.config(state="disabled")

    def print_ln(self, text):
        self.text_out.config(state=tk.NORMAL)
        self.text_out.insert(tk.END, text + "\n")
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
        self.set_map_frame(title)
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

    def load_map(self, fname, storyText=[], specialTiles=[], NPCs=[], items=[], dark=False):
        _map = [[]]
        self.entityMap = [[]]
        map_height = 0
        with open(MAP_PATH + fname, "r") as f:
            for idx, line in enumerate(f):
                map_height = idx + 1
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
        self.spawn_npcs(NPCs)
        for i in items:
            if i.iid not in self.player.checkpoints['item_ids']:
                self.items.append(i)
        if not (fname in self.player.checkpoints['levels']):
            self.player.checkpoints['levels'].append(fname)
            self.push_story_text(storyText)
        if map_height <= MAP_HEIGHT:
            self.map_string.config(height=map_height + 1)
            self.text_out.config(height=4 + MAP_HEIGHT - map_height)
        else:
            self.map_string.config(height=MAP_HEIGHT + 1)
            self.text_out.config(height=4)
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
                self.entityMap[idx].append(Entity("", [val.image], (0, 0), math.inf, val.solid))
        for idx, e in enumerate(self.entities):
            if e.health <= 0:
                if str(e) == "λ":
                    self.gameOver = True
                self.entities[idx].death_callback(self)
                self.entities.pop(idx)
            self.draw_entity(e)
        for e in self.entities:
            e.update(self.map, self.entityMap, self)
            for a in e.appendages:
                a.update(self.entityMap)
                self.draw_appendage(e, a)
        for i in self.items:
            i.update(self.map, self.entityMap, self)
        for j in self.player.items:
            j.update(self.map, self.entityMap, self)

    def spawn_entities(self):
        if self.save.map in SPAWN_TABLES:
            for e in SPAWN_TABLES[self.save.map]:
                if random.randint(0, e['rarity']) == 0:
                    x = random.randint(0, len(self.map) - 2)
                    y = random.randint(0, len(self.map[0]) - 2)
                    try:
                        if not self.entityMap[x][y].solid:
                            self.entities.append(Enemy(e['name'], e['image'], (x, y), e['health'], e['solid'], e['speed'], Sword(*WEAPONS[e['item']], (x, y))))
                    except IndexError:
                        pass # This occasionally throws an IndexError while changing maps

    def spawn_npcs(self, NPCs):
        for n in NPCs:
            if n['name'] not in self.player.killedNPCs:
                if 'deathMessage' in n:
                    self.entities.append(NPC(n['name'], n['image'], (n['x'], n['y']), n['health'], deathMessage=n['deathMessage']))
                else:
                    self.entities.append(NPC(n['name'], n['image'], (n['x'], n['y']), n['health']))

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
            if self.player.x < MAP_HEIGHT / 2:
                rendered_map = rendered_map[:MAP_HEIGHT]
            elif len(rendered_map) - self.player.x - 1 < MAP_HEIGHT / 2:
                rendered_map = rendered_map[len(self.entityMap) - MAP_HEIGHT - 2:]
            else:
                rendered_map = rendered_map[self.player.x - int(MAP_HEIGHT / 2) - 1:self.player.x + int(MAP_HEIGHT / 2)]
        frame = 'Health [' + ('='*int(self.player.health * 10 / MAX_HEALTH)).ljust(10) + '] ' + str(round(self.player.health)) + '\n'
        for row in rendered_map:
            for tile in row:
                frame += str(tile)
        if frame[-1] == "\n":
            frame = frame[:-1]
        self.set_map_frame(frame)

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
        self.set_map_frame(frame)
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
                self.master.set_map_frame(i)
                self.master.after(int(TICK_DELAY * 5000), self.master.update())


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


class Entity(Tileizable):
    def __init__(self, name, images, pos, health, solid):
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
    def __init__(self, master, app, disp, dir, image, lifespan, damage=0, piercing=False, solid=False, next_appendage=None):
        super().__init__(solid)
        self.master = master
        self.app = app
        self.x, self.y = disp
        self.dirx, self.diry = dir
        self.image = image
        self.remaining_age = lifespan
        self.damage = damage
        self.piercing = piercing
        self.next = next_appendage

    def __repr__(self):
        return self.image

    def update(self, emap):
        self.remaining_age -= 1
        if self.remaining_age < 1:
            self.delete()
        emap[self.master.x + self.dirx][self.master.y + self.diry].take_damage(self.app, self.damage)
        # Sword can damage enemy in front of itself
        if self.piercing:
            emap[self.master.x + self.dirx][self.master.y + self.diry * 2].take_damage(self.app, self.damage)

    def take_damage(self, app, d):
        pass  # EntityAppendages are added to EntityMap, so this function is rarely called

    def delete(self):
        if self.next:
            self.master.appendages.append(self.next)
        self.master.appendages.pop(0)


class ItemUser(Entity):
    def __init__(self, name, images, pos, health, solid, item):
        super().__init__(name, images, pos, health, solid)
        self.item = item
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
    def __init__(self, name, pos, item):
        super().__init__(name, ["λ"], pos, 100, True, item)
        self.checkpoints = {'levels': [], 'item_ids': []}
        self.items: [Item] = [self.item]
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
    def __init__(self, name, images, pos, health, solid, speed, item):
        super().__init__(name, images, pos, health, solid, item)
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


class NPC(Entity):
    def __init__(self, name, images, pos, health, deathMessage=[]):
        super().__init__(name, images, pos, health, True)
        self.deathMessage = deathMessage

    def death_callback(self, app):
        app.push_story_text(self.deathMessage)
        app.player.killedNPCs.append(self.name)


class Item(Entity):
    def __init__(self, name, image, use_callback, pos, damage=0, regen=0, consumable=False, iid=None):
        super().__init__(name, image, pos, math.inf, False)
        self.damage = damage
        self.regen = regen
        self.consumable = consumable
        self.iid = iid
        self.count = 1
        self.use_callback = lambda *args, **kwargs: use_callback(self, *args, **kwargs)


class Projectile(Entity):
        def __init__(self, name, images, pos, vel):
            super().__init__(name, images, pos, math.inf, False)
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
        super().init(name, "e", heal_callback, pos, regen=regen, iid=iid)


class Save:
    def __init__(self, name):
        self.player = Player(name, (8, 0), Sword(*WEAPONS['Rusty Sword'], (8, 0)))
        self.entities = []
        self.map = "01"


def sword_callback(item, master, app):
        if not app.entityMap[master.x][master.y + master.direction].solid:
            if len(master.appendages) == 0:
                if master.direction == 1:
                    master.appendages.append(EntityAppendage(master, app, (0, master.direction), (0, master.direction), "/", 1, damage=item.damage, piercing=False,
                                                           next_appendage=EntityAppendage(master, app, (0, master.direction), (0, master.direction),  "—",
                                                                                          12, damage=item.damage, piercing=True,
                                                                                          next_appendage=EntityAppendage(
                                                                                              master, app, (0, master.direction), (0, master.direction),
                                                                                              "/", 1, damage=item.damage,
                                                                                              piercing=False))))
                elif master.direction == -1:
                    master.appendages.append(EntityAppendage(master, app, (0, master.direction), (0, master.direction), "\\", 1, damage=item.damage, piercing=False,
                                                           next_appendage=EntityAppendage(master, app, (0, master.direction), (0, master.direction), "—",
                                                                                          12, damage=item.damage, piercing=True,
                                                                                          next_appendage=EntityAppendage(
                                                                                              master, app, (0, master.direction), (0, master.direction),
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
                master.appendages.append(EntityAppendage(master, app, (0, master.direction), (0, master.direction),")", 12))
            elif master.direction == -1:
                master.appendages.append(EntityAppendage(master, app, (0, master.direction), (0, master.direction),"(", 12))
        elif master.appendages[-1].image == ")":
            master.appendages[-1].remaining_age = 3
        elif master.appendages[-1].image == "(":
            master.appendages[-1].remaining_age = 3
        if item.cooldown == 0:
            arrow = Projectile('arrow', '*', (master.x, master.y + master.direction), (0, master.direction))
            app.entities.append(arrow)
            if master.direction == 1:
                arrow.appendages.append(EntityAppendage(arrow, app, (0, -1), (0, 1), "→", math.inf, damage=item.damage, piercing=False))
            elif master.direction == -1:
                arrow.appendages.append(EntityAppendage(arrow, app, (0, 1), (0, -1), "←", math.inf, damage=item.damage, piercing=False))
            item.cooldown = int(TICK_FREQUENCY / 3)


def shield_callback(item, master, app):
    if not app.entityMap[master.x][master.y + master.direction].solid:
        if item.cooldown == 0:
            if master.direction == 1:
                master.appendages.append(EntityAppendage(master, app, (0, master.direction), (0, master.direction),"]", 12, solid=True))
            elif master.direction == -1:
                master.appendages.append(EntityAppendage(master, app, (0, master.direction), (0, master.direction),"[", 12, solid=True))
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
    'Worm Flesh': (('piece of worm flesh', 'e', heal_callback), {'regen': 30, 'consumable': True}),
    'Red Potion': (('red potion', 'p', heal_callback), {'regen': 50, 'consumable': True}),
    'X-Ray Spell': (('x-ray spell', '★', xray_callback), {})
    
}

WEAPONS = {
    'Rusty Sword': ('rusty sword', 1),
    'Steel Sword': ('steel sword', 3),
    'Wooden Bow': ('wooden bow', 5),
    'Wooden Shield': ('wooden shield', 30)
}

MONSTERS = {
    'Worm': {'name': 'Worm', 'image': '~', 'health': 10, 'solid': True,
        'speed': 1, 'rarity': 90, 'item': 'Rusty Sword'},
    'Kobold': {'name': 'Kobold', 'image': 'k', 'health': 20, 'solid': True,
        'speed': 1.25, 'rarity': 40, 'item': 'Rusty Sword'}
}

DROP_TABLES = {
    'Worm': {'Worm Flesh': .25}
}

SPAWN_TABLES = {
    '01': [MONSTERS['Worm']],
    '02': [MONSTERS['Worm']],
    '04-h1-r2': [MONSTERS['Kobold']]
}

MAPS = {
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
            Portal("◘", (36, 18), (10, 5), "04-h1-r1"),
            Portal("◘", (37, 18), (11, 5), "04-h1-r1"),
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
            Portal("◘", (10, 6), (36, 19), "04"),
            Portal("◘", (11, 6), (37, 19), "04"),
            Portal("◘", (19, 2), (3, 2), "04-h1-r2"),
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
            Portal("◘", (3, 2), (19, 2), "04-h1-r1"),
            Portal("◘", (21, 27), (20, 9), "04-h1-r3"),
        ], 'items': [
            Sword(*WEAPONS['Steel Sword'], (16, 41), iid=3),
        ], 'dark': True
    }),
    '04-h1-r3': ('04-h1-r3', {'specialTiles': [
            Portal("◘", (20, 9), (21, 27), "04-h1-r2"),
        ]
    }),
    's1': ('s1', {'storyText': [
            'You stumble upon a secret chamber.'
        ],
        'specialTiles': [
            Portal("@", (3, 3), (0, 15), "03"),
        ], 'items': [
            Bow(*WEAPONS['Wooden Bow'], (1, 1), iid=1),
            App.generate_item('Red Potion', (4, 5), iid=2)
        ]
    })
}

if __name__ == "__main__":
    root = App()
    root.mainloop()
