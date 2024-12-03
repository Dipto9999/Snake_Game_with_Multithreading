# Group#: G6
# Student Names: Muntakim Rahman, Tomaz Zlindra

"""
    This program implements a variety of the snake
    game (https://en.wikipedia.org/wiki/Snake_(video_game_genre))

    The model of Inter-Process Communication (IPC) implemented has been changed from message passing to shared-memory.
    Similar to Labs 5 & 6, we are using mutexes (i.e. locks in a dict) to protect read-write access to the memory instead of the `queue`
    from the original design.

    This entails a separate thread for Game superloop in a reader-writer synchronization problem. Access to the 4 data fields (i.e. game_over, score, prey, move)
    is protected by a critical section. This is updated with logic in the Game class, and read by the GUI class to render its state.

    Note that GUI access has been designed to have non-blocking mutex acquires for all fields other than game_over (i.e. if game has not ended).
    If a certain lock from the dict cannot be acquired (i.e. data being written to when context-switch occurs), it is momentarily skipped in favor of updating other GUI components.
    This is done through scheduling an update every 100ms to behave similarly to the queue in the original program design.

    **IMPORTANT** Tkinter is NOT thread-safe. To handle GUI updates, we use the Tk.after(...) method to achieve scheduling functionality. This is the same as in the original Part 1 design.
"""

import threading

from tkinter import Tk, Canvas, Button
import random, time

class Gui():
    """
        This class takes care of the game's graphic user interface (gui)
        creation and termination.
    """
    def __init__(self):
        """
            The initializer instantiates the main window and
            creates the starting icons for the snake and the prey,
            and displays the initial gamer score.
        """
        #some GUI constants
        scoreTextXLocation = 60
        scoreTextYLocation = 15
        textColour = "white"
        #instantiate and create gui
        self.root = Tk()
        self.canvas = Canvas(self.root, width = WINDOW_WIDTH,
            height = WINDOW_HEIGHT, bg = BACKGROUND_COLOUR)
        self.canvas.pack()
        #create starting game icons for snake and the prey
        self.snakeIcon = self.canvas.create_line(
            (0, 0), (0, 0), fill=ICON_COLOUR, width=SNAKE_ICON_WIDTH)
        self.preyIcon = self.canvas.create_rectangle(
            0, 0, 0, 0, fill=ICON_COLOUR, outline=ICON_COLOUR)
        #display starting score of 0
        self.score = self.canvas.create_text(
            scoreTextXLocation, scoreTextYLocation, fill=textColour,
            text='Your Score: 0', font=("Helvetica","11","bold"))
        #binding the arrow keys to be able to control the snake
        for key in ("Left", "Right", "Up", "Down"):
            self.root.bind(f"<Key-{key}>", game.whenAnArrowKeyIsPressed)
        self.update()

    def update(self):
        '''
            This method handles the state by trying to retrieve
            data from the game and accordingly taking the corresponding
            action. These include : game_over, move, prey, score.
            Before exiting, this method schedules to call itself after a short delay.

            For general gameplay, non-blocking acquires are used to update the GUI. For these to be updated,
            it must be confirmed that the game is not over.
        '''
        def updateSnake() -> None:
            if game.locks["move"].acquire(blocking = False):
                self.canvas.coords(self.snakeIcon, *[coord for point in game.snakeCoordinates for coord in point])
                game.locks["move"].release()
        def updatePrey() -> None:
            if game.locks["prey"].acquire(blocking = False):
                self.canvas.coords(self.preyIcon, *game.preyCoordinates)
                game.locks["prey"].release()
        def updateScore() -> None:
            if game.locks["score"].acquire(blocking = False):
                self.canvas.itemconfigure(self.score, text=f"Your Score: {game.score}")
                game.locks["score"].release()

        game.locks["game_over"].acquire()
        gameNotOver: bool = game.gameNotOver # Read Game State
        game.locks["game_over"].release()

        if gameNotOver:
            updateSnake()
            updatePrey()
            updateScore()
            self.root.after(100, self.update) # Call Function Every 100 ms
        else:
            self.gameOver()

    def gameOver(self):
        """
            This method is used at the end to display a
            game over button.
        """
        gameOverButton = Button(self.canvas, text="Game Over!",
            height = 3, width = 10, font=("Helvetica","14","bold"),
            command=self.root.destroy)
        self.canvas.create_window(200, 100, anchor="nw", window=gameOverButton)

class Game():
    '''
        This class implements most of the game functionalities.
    '''
    def __init__(self):
        """
           This initializer sets the initial snake coordinate list, movement
           direction, and arranges for the first prey to be created.
        """
        self.locks = {
            "game_over": threading.Lock(),
            "move": threading.Lock(),
            "prey": threading.Lock(),
            "score": threading.Lock(),
        }
        self.writecount: int = 0

        #starting length and location of the snake
        #note that it is a list of tuples, each being an
        # (x, y) tuple. Initially its size is 5 tuples.
        self.snakeCoordinates = [(495, 55), (485, 55), (475, 55),
                                 (465, 55), (455, 55)]
        #initial direction of the snake
        self.direction = "Left"
        self.gameNotOver = True
        self.score: int = 0

        self.createNewPrey() # Generate First Prey

    def superloop(self) -> None:
        """
            This method implements a main loop
            of the game. It constantly generates "move"
            tasks to cause the constant movement of the snake.
            Use the SPEED constant to set how often the move tasks
            are generated.
        """
        SPEED = 0.15     #speed of snake updates (sec)
        while True:
            #complete the method implementation below
            time.sleep(SPEED)
            self.move()

    def whenAnArrowKeyIsPressed(self, e) -> None:
        """
            This method is bound to the arrow keys
            and is called when one of those is clicked.
            It sets the movement direction based on
            the key that was pressed by the gamer.
            Use as is.
        """
        currentDirection = self.direction
        #ignore invalid keys
        if (currentDirection == "Left" and e.keysym == "Right" or
            currentDirection == "Right" and e.keysym == "Left" or
            currentDirection == "Up" and e.keysym == "Down" or
            currentDirection == "Down" and e.keysym == "Up"):
            return
        self.direction = e.keysym

    def move(self) -> None:
        """
            This method implements what is needed to be done
            for the movement of the snake.
            It generates a new snake coordinate.
            If based on this new movement, the prey has been
            captured, it adds a task to the queue for the updated
            score and also creates a new prey.
            It also calls a corresponding method to check if
            the game should be over.
            The snake coordinates list (representing its length
            and position) should be correctly updated.
        """
        def isCaptured(snakeCoordinates) -> bool:
            self.locks["prey"].acquire()
            preyCoordinates: tuple = self.preyCoordinates # Read Prey Coordinates for Processing
            self.locks["prey"].release()

            captureCoordinates = (
                snakeCoordinates[0] - SNAKE_ICON_WIDTH // 2, # x0
                snakeCoordinates[1] - SNAKE_ICON_WIDTH // 2, # y0
                snakeCoordinates[0] + SNAKE_ICON_WIDTH // 2, # x1
                snakeCoordinates[1] + SNAKE_ICON_WIDTH // 2 # y1
            )

            isCaptured: bool = False
            # Checks if Snake Coordinates are in Prey Coordinates (Instance where Prey could be much larger than Snake)
            if (captureCoordinates[0] <= preyCoordinates[2] and captureCoordinates[1] <= preyCoordinates[3]) and (captureCoordinates[0] >= preyCoordinates[0] and captureCoordinates[1] >= preyCoordinates[1]): # Snake Point 0 in Prey
                isCaptured = True
            elif (captureCoordinates[2] >= preyCoordinates[0] and captureCoordinates[3] >= preyCoordinates[1]) and (captureCoordinates[2] <= preyCoordinates[2] and captureCoordinates[3] <= preyCoordinates[3]): # Snake Point 1 in Prey
                isCaptured = True
            # Checks if Prey Coordinates are in Snake Coordinates (Instance where Snake could be much larger than Prey)
            elif (preyCoordinates[2] >= captureCoordinates[0] and preyCoordinates[3] >= captureCoordinates[1]) and (preyCoordinates[2] <= captureCoordinates[2] and preyCoordinates[3] <= captureCoordinates[3]): # Prey Point 0 in Snake
                isCaptured = True
            elif (preyCoordinates[0] <= captureCoordinates[2] and preyCoordinates[1] <= captureCoordinates[3]) and (preyCoordinates[0] >= captureCoordinates[0] and preyCoordinates[1] >= captureCoordinates[1]): # Prey Point 1 in Snake
                isCaptured = True
            return isCaptured

        def moveSnake(isPreyCaptured: bool, newCoordinates: tuple) -> None:
            self.locks["move"].acquire()
            if isPreyCaptured:
                self.snakeCoordinates = [*self.snakeCoordinates, newCoordinates] # Append New Snake Head
            else:
                self.snakeCoordinates = [*self.snakeCoordinates[1:], newCoordinates] # Move Snake
            self.locks["move"].release()

        def incrementScore() -> None:
            self.locks["score"].acquire()
            self.score += 1
            self.locks["score"].release()

        NewSnakeCoordinates = self.calculateNewCoordinates()

        self.isGameOver(NewSnakeCoordinates)

        preyCaptured: bool = isCaptured(NewSnakeCoordinates)
        moveSnake(isPreyCaptured = preyCaptured, newCoordinates = NewSnakeCoordinates)

        if preyCaptured:
            self.createNewPrey()
            incrementScore()

    def calculateNewCoordinates(self) -> tuple:
        """
            This method calculates and returns the new
            coordinates to be added to the snake
            coordinates list based on the movement
            direction and the current coordinate of
            head of the snake.
            It is used by the move() method.
        """

        self.locks["move"].acquire()
        lastX, lastY = self.snakeCoordinates[-1] # Read Snake Coordinates for Processing
        self.locks["move"].release()

        #complete the method implementation below
        if self.direction == "Left":
            lastX -= SNAKE_ICON_WIDTH
        elif self.direction == "Right":
            lastX += SNAKE_ICON_WIDTH
        elif self.direction == "Up":
            lastY -= SNAKE_ICON_WIDTH
        else:
            lastY += SNAKE_ICON_WIDTH
        return (lastX, lastY)

    def isGameOver(self, snakeCoordinates) -> None:
        """
            This method checks if the game is over by
            checking if now the snake has passed any wall
            or if it has bit itself.
            If that is the case, it updates the gameNotOver
            field and also adds a "game_over" task to the queue.
        """
        x, y = snakeCoordinates
        #complete the method implementation below

        x_collision: bool = (x <= 0) or (x >= WINDOW_WIDTH)
        y_collision: bool = (y <= 0) or (y >= WINDOW_HEIGHT)

        if (x_collision) or (y_collision) or ((x, y) in self.snakeCoordinates[:-1]):
            self.locks["game_over"].acquire()
            self.gameNotOver = False
            self.locks["game_over"].release()
        return

    def createNewPrey(self) -> None:
        """
            This methods picks an x and a y randomly as the coordinate
            of the new prey and uses that to calculate the
            coordinates (x - 5, y - 5, x + 5, y + 5). [you need to replace 5 with a constant]
            It then adds a "prey" task to the queue with the calculated
            rectangle coordinates as its value. This is used by the
            queue handler to represent the new prey.
            To make playing the game easier, set the x and y to be THRESHOLD
            away from the walls.
        """
        THRESHOLD = 15

        generatedCoordinates: tuple = (random.randint(THRESHOLD, WINDOW_WIDTH - THRESHOLD), random.randint(THRESHOLD, WINDOW_HEIGHT - THRESHOLD))

        self.locks["prey"].acquire()
        self.preyCoordinates = (
            generatedCoordinates[0] - PREY_ICON_WIDTH // 2, # x0
            generatedCoordinates[1] - PREY_ICON_WIDTH // 2, # y0
            generatedCoordinates[0] + PREY_ICON_WIDTH // 2, # x1
            generatedCoordinates[1] + PREY_ICON_WIDTH // 2 # y1
        )
        self.locks["prey"].release()

if __name__ == "__main__":
    #some constants for our GUI
    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 300
    SNAKE_ICON_WIDTH = 15
    PREY_ICON_WIDTH = 10 # add the specified constant PREY_ICON_WIDTH here

    BACKGROUND_COLOUR = "black" # you may change this colour if you wish
    ICON_COLOUR = "blue"        # you may change this colour if you wish

    game = Game() # instantiate the game object
    gui = Gui() # instantiate the game user interface

    threading.Thread(target = game.superloop, daemon = True).start() # start a thread with the superloop of the game
    gui.root.mainloop() # start the GUI's own event loop