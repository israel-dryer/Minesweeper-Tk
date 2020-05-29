"""
    Title: Minesweeper
    Description: A clone based on the game built by Robert Donner and Curt Johson
    Author: Israel Dryer
    Modified: 2020-05-29
"""
import tkinter as tk
from tkinter import messagebox
from random import choices
from collections import namedtuple
from time import perf_counter
from os import listdir, path
import pickle
import numpy as np

Level = namedtuple('Level', 'height width mines')
Score = namedtuple('Score', 'score name')

DEFINED_LEVELS = {
    'beginner': Level(9, 9, 10),
    'intermediate': Level(16, 16, 40),
    'expert': Level(16, 30, 99)
}

class Game(tk.Tk):

    def __init__(self, difficulty):
        super().__init__()
        # remove from screen until fully built
        self.withdraw()
        
        # window properties
        self.tk_setPalette('#C0C0C0')
        self.title("Minesweeper")
        self.iconbitmap("winmine.ico")
        self.withdraw() # remove from screen until fully built

        # general game properties
        self.difficulty = difficulty
        self.level = DEFINED_LEVELS[difficulty]
        self.time_started = 0.0
        self.time_elapsed = 0.0
        self.tiles_visible = 0
        self.move_count = 0
        self.flags = 0
        self.mine_tiles = []
        self.checked = []
        self.use_marks = True # question mark on right-click
        self.visible_target = (self.level.height * self.level.width) - self.level.mines
        self.game_over = False
        self.highscores = self.load_highscores()

        # game images
        image_files = [(file.split('.')[0], 'Images/Opaque/' + file) for file in listdir('Images/Opaque') if not file.endswith('ico')]
        self.images = {key: tk.PhotoImage(file=val) for key, val in image_files}
        
        # APPLICATION MENU -------------------------------------------------------------------------
        self.menubar = tk.Menu(self)

        ## game menu
        self.gamemenu = tk.Menu(self.menubar, tearoff=0)
        self.gamemenu.add_command(label='New', accelerator='F2', command=lambda: self.on_reset_release(0))
        self.bind("<Key-F2>", self.on_reset_release)
        self.gamemenu.add_separator()

        ### level options
        self.level_var = tk.IntVar()
        self.level_var.set(1)
        self.gamemenu.add_radiobutton(label='Beginner', variable=self.level_var, value=1, command=lambda: self.on_level_select('beginner'))
        self.gamemenu.add_radiobutton(label='Intermediate', variable=self.level_var, value=2, command=lambda: self.on_level_select('intermediate'))
        self.gamemenu.add_radiobutton(label='Expert', variable=self.level_var, value=3, command=lambda: self.on_level_select('expert'))
        self.gamemenu.add_separator()

        ### miscellanous game options
        self.marks_var = tk.IntVar()
        self.marks_var.set(1)
        self.gamemenu.add_checkbutton(label='Marks (?)', variable=self.marks_var, command=self.on_toggle_marks)
        self.color_var = tk.IntVar()  # TODO monochrome buttons needed
        self.color_var.set(1)
        self.gamemenu.add_checkbutton(label='Color', variable=self.color_var, command=None, state=tk.DISABLED)
        self.sound_var = tk.IntVar() # TODO try to leverage system sounds
        self.sound_var.set(0)
        self.gamemenu.add_checkbutton(label='Sound', variable=self.sound_var, command=None, state=tk.DISABLED)
        self.gamemenu.add_separator()

        # high scores - displays the high scores for beginner, intermediate, and expert.
        self.gamemenu.add_command(label='Best Times...', command=lambda: HighScores(self))
        self.gamemenu.add_separator()

        # exit option and main menu setup
        self.gamemenu.add_command(label='Exit...', command=self.destroy)
        self.menubar.add_cascade(label='Game', underline=0, menu=self.gamemenu)

        ## help menu
        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label='Contents', accelerator='F1', state=tk.DISABLED, command=None)
        self.helpmenu.add_command(label='Search for Help on...', state=tk.DISABLED, command=None)
        self.helpmenu.add_command(label='Using Help', state=tk.DISABLED, command=None)
        self.helpmenu.add_separator()
        self.helpmenu.add_command(label='About Minesweeper...', command=lambda: AboutMinesweeper(self))
        self.menubar.add_cascade(label='Help', underline=0, menu=self.helpmenu)
        self.config(menu=self.menubar)

        # WINDOW WIDGETS ---------------------------------------------------------------------------

        # top information bar
        self.infobar = tk.Frame(self, relief=tk.SUNKEN, bd=3, padx=5, pady=3)
        self.infobar.grid_rowconfigure(0, weight=1)
        self.infobar.grid_columnconfigure(0, weight=1)
        self.infobar.grid_columnconfigure(1, weight=1)
        self.infobar.grid_columnconfigure(2, weight=1)
        ## left-side mine counter
        self.mine_count = tk.Canvas(self.infobar, width=39, height=23, bd=1, relief=tk.SUNKEN)
        self.mine_count.grid(row=0, column=0, sticky=tk.W)
        ## center reset button
        self.reset_btn = tk.Label(self.infobar, image=self.images['smile_raised'])
        self.reset_btn.bind("<Button-1>", self.on_reset_press)
        self.reset_btn.bind("<ButtonRelease-1>", self.on_reset_release)
        self.reset_btn.grid(row=0, column=1)
        ## right-side game timer
        self.timer = tk.Canvas(self.infobar, width=39, height=23, bd=1, relief=tk.SUNKEN)
        self.timer.grid(row=0, column=0, sticky=tk.E)
        self.timer.grid(row=0, column=2, sticky=tk.E)
        self.reset_infobar()
        # add infobar to root window
        self.infobar.pack(padx=5, pady=(5, 3), fill=tk.X, expand=tk.YES)

        # setup the tile grid based on height and width of level
        self.tile_grid = tk.Frame(self, relief=tk.SUNKEN, bd=3)
        self.setup_tile_grid()

        # center app on screen
        self.eval("tk::PlaceWindow . center")
        self.deiconify()

    @staticmethod
    def load_highscores():
        """Load highscores data if exists, otherwise create file"""
        if path.exists('highscores.data'):
            try:
                with open('highscores.data', 'rb') as f:
                    return pickle.load(f)
            except:
                highscores = {
                    'beginner': Score(999, 'Anomymous'),
                    'intermediate': Score(999, 'Anonymous'),
                    'expert': Score(999, 'Anomymous')
                    }
                with open('highscores.data', 'wb') as f:
                    pickle.dump(highscores, f)
                return highscores                
        else:
            highscores = {
                'beginner': Score(999, 'Anomymous'),
                'intermediate': Score(999, 'Anonymous'),
                'expert': Score(999, 'Anomymous')
                }
            with open('highscores.data', 'wb') as f:
                pickle.dump(highscores, f)
        return highscores
            
    def on_level_select(self, level):
        """Menu callback to create level board"""
        self.level = DEFINED_LEVELS[level]
        self.visible_target = (self.level.height * self.level.width) - self.level.mines
        # remove existing grid and restart
        for tile in self.tile_array.flatten():
            tile.destroy()
        # add new grid with new level settings
        self.setup_tile_grid()
        # reset_infobar
        self.reset_grid()
        self.reset_infobar()

    def on_toggle_marks(self):
        """Toggle question marks on right-click"""
        self.use_marks = True if not self.use_marks else False

    def setup_tile_grid(self):
        """Setup the tile grid based on level height and width"""
        self.tile_array = np.array([], dtype='object')
        for row in range(self.level.height):
            for col in range(self.level.width):
                tile = Tile(self.tile_grid, row, col, self.images['tile_raised'])
                self.tile_array = np.append(self.tile_array, tile)
                # button bindings
                tile.bind("<Button-3>", self.on_rclick_tile)
                tile.bind("<Button-1>", self.on_lclick_tile)
                tile.bind("<ButtonRelease-1>", self.on_lclick_tile_release)
                tile.bind("<Enter>", self.on_mouse_enter)
                tile.bind("<Leave>", self.on_mouse_leave)
        # reshape tile array to grid size (height, width)
        self.tile_array = self.tile_array.reshape((self.level.height, self.level.width))  
        # add tile grid to root window
        self.tile_grid.pack(padx=5, pady=(3, 5))                

    def generate_mines(self, event_tile):
        """Select random tiles as mines and set `is_mine` flag"""
        tiles = self.tile_array.flatten().tolist()
        # remove the event tile as an option to prevent player from losing on first click
        tiles.remove(event_tile)
        self.mine_tiles = choices(tiles, k=self.level.mines)
        for tile in self.mine_tiles:
            tile.is_mine = True

    def assign_neighbor_properties(self):
        """Assign tile and mine neighbor properties to each tile"""
        for tile in self.tile_array.flatten():
            neighbors, mines = self.neighbors(tile)
            tile.tile_neighbors = neighbors
            tile.mine_neighbors = mines

    def neighbors(self, tile):
        """Identify and return valid neighbors"""
        neighbors = []  # the 8-block area surrounding the target tile
        offsets = np.array([(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)])
        for offset in offsets:
            try:
                if all(list(map(lambda x: x >= 0, tuple(offset + tile.index)))):
                    neighbors.append(self.tile_array[tuple(tile.index + offset)])
            # any index that is out of bounds (negative) or (index error)
            except IndexError:
                continue
        # count of neighbors that are mines
        mines = self.mine_neighbors(neighbors)
        return neighbors, mines

    @staticmethod
    def mine_neighbors(neighbors):
        """Identify and return count of neighbors that are mines"""
        mines = map(lambda x: x.is_mine, neighbors)
        return sum(mines)

    def visible_tiles(self):
        """Return a count of visible tiles"""
        num_visible = sum(list(map(lambda x: x.is_visible, self.tile_array.flatten())))
        return num_visible

    def on_reset_press(self, _):
        """Reset button press callback"""
        self.reset_btn['image'] = self.images['smile_flat']

    def on_reset_release(self, _):
        """Reset button release callback"""
        self.reset_btn['image'] = self.images['smile_raised']
        self.reset_grid()
        self.reset_infobar()
        self.game_over = False

    def reset_grid(self):
        """Set or reset the mine grid"""
        for tile in self.tile_array.flatten():
            tile.is_visible = False
            tile.is_mine = False
            tile.is_flag = False
            tile.is_question = False
            tile.tile_neighbors = None
            tile.mine_neighbors = 0
            tile['image'] = self.images['tile_raised']

        # general game properties
        self.checked = []
        self.flags = 0
        self.move_count = 0
        self.set_timer(reset=True)

    def reset_infobar(self):
        """Reset the mine counter and game timer"""
        # mine counter
        self.mine_count.create_image(3, 3, anchor=tk.NW, image=self.images['0'])
        self.mine_count.create_image(16, 3, anchor=tk.NW, image=self.images['0'])
        self.mine_count.create_image(29, 3, anchor=tk.NW, image=self.images['0'])
        self.set_mine_count(0)
        # game timer
        self.timer.create_image(3, 3, anchor=tk.NW, image=self.images['0'])
        self.timer.create_image(16, 3, anchor=tk.NW, image=self.images['0'])
        self.timer.create_image(29, 3, anchor=tk.NW, image=self.images['0'])

    def set_mine_count(self, increment):
        """Increment mine counter"""
        self.flags -= increment
        num_string = f"{self.level.mines - self.flags:0>3}"
        a, b, c = tuple(list(num_string))
        self.mine_count.create_image(3, 3, anchor=tk.NW, image=self.images[a])
        self.mine_count.create_image(16, 3, anchor=tk.NW, image=self.images[b])
        self.mine_count.create_image(29, 3, anchor=tk.NW, image=self.images[c])

    def set_timer(self, reset=False):
        """Game timer"""
        # TODO the timer restarts whenever the game is reset; should start at first click of new round
        if self.time_started == 0 or reset:
            self.time_started = perf_counter()

        elapsed = f"{perf_counter() - self.time_started:0>3.0f}"
        digit_1, digit_2, digit_3 = tuple(elapsed)

        self.timer.create_image(3, 3, anchor=tk.NW, image=self.images[digit_1])
        self.timer.create_image(16, 3, anchor=tk.NW, image=self.images[digit_2])
        self.timer.create_image(29, 3, anchor=tk.NW, image=self.images[digit_3])
        if not self.game_over:
            self.after(1000, self.set_timer) 

    def on_mouse_enter(self, event):
        """Callback for mouse hover entering tile space."""
        tile = event.widget
        # question mark has flat relief on mouse-over
        if tile.is_question:
            tile['image'] = self.images['tile_question_flat']
        elif not any([self.game_over, tile.is_visible, tile.is_flag]):
            tile['image'] = self.images['tile_flat']
            
    def on_mouse_leave(self, event):
        """Callback for mouse hover leaving tile space. I would like this to show relief when the mouse
        is held down and dragged across the screen, but now sure how to do this yet. There is no relief
        for the tile flag, but there is for the question mark, per the original XP version of the game."""
        # TODO convert this to a <enter> + <Button-1> event
        tile = event.widget
        # no relief for tile flag
        if self.game_over or tile.is_visible or tile.is_flag:
            return
        # question mark has relief
        if tile.is_question:
            tile['image'] = self.images['tile_question_raised']
        else:
            tile['image'] = self.images['tile_raised']
            return

    def on_rclick_tile(self, event):
        """Set or remove flag file tile. The first right-click is a flag, the second is
        a question mark, the 3rd goes back to an empty raised button. Then then repeat."""
        tile = event.widget
        if self.game_over:
            return
        if not tile.is_visible:
            if tile.is_flag:
                tile.is_flag = False
                if self.use_marks:
                    tile.is_question = True
                    tile['image'] = self.images['tile_question_raised']
                self.set_mine_count(1)
            elif tile.is_question:
                tile.is_question = False
                tile['image'] = self.images['tile_flat']
            elif self.flags < self.level.mines:
                tile.is_flag = True
                tile['image'] = self.images['tile_flag']
                self.set_mine_count(-1)    

    def on_lclick_tile(self, event):
        """Callback for button press.  The game does not offically start until the first mouse
        click on a grid tile. This generates the tile and starts the timer. The tile in the event
        is passed to the reset grid method to exclude from the random selection of mines. This
        prevents the player for clicking on a mine as the first play and thus ending the game on
        the first click."""
        tile = event.widget
        if not self.game_over:
            # first move of the game
            if self.move_count == 0:
                self.reset_grid()
                self.generate_mines(tile)
                self.assign_neighbor_properties()
                self.reset_infobar()
            self.reset_btn['image'] = self.images['surprise']
            self.move_count += 1

    def on_lclick_tile_release(self, event):
        """Callback for button release"""
        # check if containing widget is event triggering widget
        tile = event.widget
        tile_x, tile_y = self.winfo_pointerxy()
        tile_under_mouse = self.winfo_containing(tile_x, tile_y)
        if self.game_over:
            return
        if any([tile != tile_under_mouse, tile.is_visible, tile.is_flag]):
            self.reset_btn['image'] = self.images['smile_raised']
            return
        if tile.is_mine:
            self.reset_btn['image'] = self.images['dead']
            tile.is_question = False
            self.game_over = True
            # uncover all mines
            for mine in self.mine_tiles:
                mine['image'] = self.images['tile_mine']
            # clicked mine is colored red
            tile['image'] = self.images['tile_explode']

        else:
            self.reset_btn['image'] = self.images['smile_raised']
            self.checked.clear()
            self.uncover_tile(tile)

        # check for win
        if self.visible_tiles() == self.visible_target:
            self.game_over = True
            self.reset_btn['image'] = self.images['sunglasses']
            for tile in self.tile_array.flatten():
                if tile.is_mine:
                    tile['image'] = self.images['tile_flag']

            # check for highscore and show results
            self.time_elapsed = int(perf_counter() - self.time_started)
            self.check_for_highscore()

    def check_for_highscore(self):
        """Determine if user has a high score to record"""
        current_highscore = self.highscores[self.difficulty].score
        user_score = self.time_elapsed
        if user_score < current_highscore:
            NewHighScore(self, user_score)
            

    def uncover_tile(self, tile):
        """Uncover all tiles around the target that are not bombs"""
        if any([tile in self.checked, tile.is_visible, tile.is_mine]):
            return
        if tile.mine_neighbors != 0:
            image = self.images['tile_' + str(tile.mine_neighbors)]
            tile['image'] = image
            tile.is_visible = True
            tile.is_question = False
            self.checked.append(tile)
            return
        
        tile['image'] = self.images['tile_flat']
        tile.is_visible = True
        tile.is_question = False
        self.checked.append(tile)
        try:
            # TODO Why is this try block needed?? What am I missing?
            for next_tile in tile.tile_neighbors:
                self.uncover_tile(next_tile)
        except IndexError:
            return

    def test_key(self, event):
        """Any key is pressed"""
        print(event)

class Tile(tk.Label):
    """Gameboard Tile"""
    def __init__(self, master, row, col, image):
        super().__init__(master, bd=0, image=image)
        self.row = row
        self.col = col
        self.index = np.array([row, col])
        self.is_visible = False
        self.visible_image = None
        self.is_mine = False
        self.is_flag = False
        self.is_question = False
        self.tile_neighbors = None
        self.mine_neighbors = 0
        self.grid(row=self.row, column=self.col, sticky=tk.NSEW)

class HighScores(tk.Toplevel):
    """Popup to show top scores for all levels of the game"""
    def __init__(self, root):
        super().__init__()
        self.geometry(f"+{root.winfo_x()-75}+{root.winfo_y()+110}")
        self.overrideredirect(1)
        self.title("Fastest Mine Sweepers")
        self.iconbitmap('Images/Opaque/winmine.ico')
        self.attributes('-topmost', 'true')
 
        self.root = root

        for x in range(4):
            self.grid_rowconfigure(x, weight=1)
        for y in range(4):
            self.grid_columnconfigure(y, weight=1)

        tk.Label(self, text="Beginner:", anchor=tk.W).grid(row=0, column=0, sticky=tk.W, padx=15, pady=(20, 0))
        tk.Label(self, text="Intermediate:", anchor=tk.W).grid(row=1, column=0, sticky=tk.W, padx=15, pady=0)
        tk.Label(self, text="Expert:", anchor=tk.W).grid(row=2, column=0, sticky=tk.W, padx=15, pady=(0, 10))

        self.score1_var = tk.StringVar()
        self.score2_var = tk.StringVar()
        self.score3_var = tk.StringVar()
        self.name1_var = tk.StringVar()
        self.name2_var = tk.StringVar()
        self.name3_var = tk.StringVar()

        self.level1_time = tk.Label(self, textvariable=self.score1_var, anchor=tk.W)
        self.level1_time.grid(row=0, column=1, sticky=tk.W, pady=(20, 0))
        self.level2_time = tk.Label(self, textvariable=self.score2_var, anchor=tk.W)
        self.level2_time.grid(row=1, column=1, sticky=tk.W, pady=0)
        self.level3_time = tk.Label(self, textvariable=self.score3_var, anchor=tk.W)
        self.level3_time.grid(row=2, column=1, sticky=tk.W, pady=(0, 10))

        self.level1_name = tk.Label(self, textvariable=self.name1_var, anchor=tk.W)
        self.level1_name.grid(row=0, column=2, sticky=tk.W, padx=15, pady=(20, 0))
        self.level2_name = tk.Label(self, textvariable=self.name2_var, anchor=tk.W)
        self.level2_name.grid(row=1, column=2, sticky=tk.W, padx=15, pady=0)
        self.level3_name = tk.Label(self, textvariable=self.name3_var, anchor=tk.W)
        self.level3_name.grid(row=2, column=2, sticky=tk.W, padx=15, pady=(0, 10))

        self.reset_btn = tk.Button(self, text="Reset Scores", command=self.reset_scores)
        self.reset_btn.grid(row=3, column=1, sticky=tk.NSEW, padx=15, pady=10)
        self.ok_btn = tk.Button(self, text="OK", command=self.destroy)
        self.ok_btn.grid(row=3, column=2, sticky=tk.NSEW, padx=15, pady=10)
        # reset scores
        self.update_scores()

    def update_scores(self):
        """Update the scores on the popup"""
        level1 = self.root.highscores['beginner']
        level2 = self.root.highscores['intermediate']
        level3 = self.root.highscores['expert']
        self.score1_var.set(f"{level1.score} seconds")
        self.score2_var.set(f"{level2.score} seconds")
        self.score3_var.set(f"{level3.score} seconds")
        self.name1_var.set(level1.name)
        self.name2_var.set(level2.name)
        self.name3_var.set(level3.name)
    
    def reset_scores(self):
        """reset all scores to anonymous"""
        # update scores in main file
        self.root.highscores['beginner'] = Score(999, 'Anonymous')
        self.root.highscores['intermediate'] = Score(999, 'Anonymous')
        self.root.highscores['expert'] = Score(999, 'Anonymous')
        with open('highscores.data', 'wb') as f:
            pickle.dump(self.root.highscores, f)
        self.update_scores()


class NewHighScore(tk.Toplevel):
    """A popup to get name of new high scorer"""
    def __init__(self, root, score):
        super().__init__()
        self.new_high = score
        self.root = root
        self.overrideredirect(1)
        self.geometry(f'+{root.winfo_x()}+{root.winfo_y()+110}')
        tk.Label(self, text="You have the fastest time").pack(padx=20, pady=(15, 0))
        tk.Label(self, text=f"for {root.difficulty.title()} level.").pack(padx=10, pady=0)
        tk.Label(self, text="Please enter your name.").pack(padx=15, pady=(0, 10))
        self.name_var = tk.StringVar()
        tk.Entry(self, textvariable=self.name_var, bg='white').pack(padx=10, fill=tk.X)
        self.name_var.set("Anonymous")
        tk.Button(self, text="OK", command=self.on_click_ok).pack(ipadx=10, pady=10)

    def on_click_ok(self):
        """Callback for ok click"""
        difficulty = self.root.difficulty
        name = self.name_var.get()
        self.root.highscores[self.root.difficulty] = Score(self.new_high, name)
        # save new scores to file
        with open('highscores.data', 'wb') as f:
            pickle.dump(self.root.highscores, f)
        # show new highscores
        HighScores(self.root)
        self.destroy()
    

class AboutMinesweeper(tk.Toplevel):
    """The about menu popup"""
    def __init__(self, root):
        super().__init__()
        self.title('About Minesweeper')
        self.iconbitmap('Images/Opaque/winmine.ico')
        self.geometry(f'325x200+{root.winfo_x()-75}+{root.winfo_y()}')

        self.logo_img = tk.PhotoImage(file='./Images/Opaque/winmine.png')
        self.logo = tk.Label(self, image=self.logo_img, anchor=tk.W)
        self.logo.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.text = tk.Text(self, height=4)
        self.text.tag_configure('bold', font=('TkTextFont', 10, 'bold'))
        self.text.tag_configure('regular', font=('TkTextFont', 10))
        self.text.insert(tk.END, "Minesweeper\n", 'bold')
        self.text.insert(tk.END, "A clone based on the original game built by Robert Donner and Curt Johnson", 'regular')
        self.text.pack(fill=tk.BOTH, padx=10, pady=(0, 10))

        self.ok_btn = tk.Button(self, text='OK', command=self.destroy)
        self.ok_btn.pack(side=tk.RIGHT, ipadx=15, ipady=3, padx=10)

        

        
if __name__ == '__main__':

    game = Game('beginner')
    #NewHighScore(game, 120)
    game.mainloop()

