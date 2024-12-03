# Group#: G6
# Student Names: Muntakim Rahman, Tomaz Zlindra

"""
    This program implements a variety of the snake
    game (https://en.wikipedia.org/wiki/Snake_(video_game_genre))

    The model of Inter-Process Communication (IPC) implemented has been changed from message passing to shared-memory.
    Similar to Labs 5 & 6, we are using mutexes (i.e. locks in a dict) to protect read-write access to the memory instead of the `queue`
    from the original design.

    This entails 2 threads for the GUI and Game in a reader-writer synchronization problem. Access to the 4 values (i.e. game_over, score, prey, move)
    is protected by a critical section. This is updated with logic in the Game class, and read to render the state of the GUI. Note that GUI access has
    been designed to have non-blocking mutex acquires. If a certain lock from the dict cannot be acquired (i.e. data being written to when context-switch occurs), it is
    momentarily skipped in favor of updating other GUI components. This is done in a forever loop (i.e. until game is over) to behave identically to the queue in the original
    program design.
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

    def gameOver(self):
        """
            This method is used at the end to display a
            game over button.
        """
        gameOverButton = Button(self.canvas, text="Game Over!",
            height = 3, width = 10, font=("Helvetica","14","bold"),
            command=self.root.destroy)
        self.canvas.create_window(200, 100, anchor="nw", window=gameOverButton)

class ComponentHandler():
    """
        This class implements the component handler for the game.
    """
    def __init__(self):
        self.game = game
        self.gui = gui
        self.componentHandler()

    def updateGameOverGUI(self) -> bool:
        game.locks["game_over"].acquire()
        gameNotOver: bool = game.gameNotOver # Read Game State
        game.locks["game_over"].release()
        return gameNotOver
    def updateSnakeGUI(self) -> None:
        game.locks["move"].acquire()
        gui.canvas.coords(gui.snakeIcon, *[coord for point in game.snakeCoordinates for coord in point])
        game.locks["move"].release()
    def updatePreyGUI(self) -> None:
        game.locks["prey"].acquire()
        gui.canvas.coords(gui.preyIcon, *game.preyCoordinates)
        game.locks["prey"].release()
    def updateScoreGUI(self) -> None:
        game.locks["score"].acquire()
        gui.canvas.itemconfigure(gui.score, text=f"Your Score: {game.score}")
        game.locks["score"].release()

    def componentHandler(self):
        '''
            This method handles the state by constantly retrieving
            data from the game and accordingly taking the corresponding
            action.
            A task could be: game_over, move, prey, score.
            Each data item
            If the loop has executed, it schedules
            to call itself after a short delay.
        '''
        if self.updateGameOverGUI():
            self.updateSnakeGUI()
            self.updatePreyGUI()
            self.updateScoreGUI()
            self.gui.root.after(100, self.componentHandler)  # Schedule the next update
        else:
            self.gui.gameOver()

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

        self.preyCoordinates: list = self.createNewPrey() # Generate First Prey


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
            captureCoordinates = (
                snakeCoordinates[0] - SNAKE_ICON_WIDTH // 2, # x0
                snakeCoordinates[1] - SNAKE_ICON_WIDTH // 2, # y0
                snakeCoordinates[0] + SNAKE_ICON_WIDTH // 2, # x1
                snakeCoordinates[1] + SNAKE_ICON_WIDTH // 2 # y1
            )

            self.locks["prey"].acquire()
            preyCoordinates: list = self.preyCoordinates.copy() # Read Prey Coordinates for Processing
            self.locks["prey"].release()

            captured: bool = False
            # Checks if Snake Coordinates are in Prey Coordinates (Instance where Prey could be much larger than Snake)
            if (captureCoordinates[0] <= preyCoordinates[2] and captureCoordinates[1] <= preyCoordinates[3]) and (captureCoordinates[0] >= preyCoordinates[0] and captureCoordinates[1] >= preyCoordinates[1]): # Snake Point 0 in Prey
                captured = True
            elif (captureCoordinates[2] >= preyCoordinates[0] and captureCoordinates[3] >= preyCoordinates[1]) and (captureCoordinates[2] <= preyCoordinates[2] and captureCoordinates[3] <= preyCoordinates[3]): # Snake Point 1 in Prey
                captured = True
            # Checks if Prey Coordinates are in Snake Coordinates (Instance where Snake could be much larger than Prey)
            elif (preyCoordinates[2] >= captureCoordinates[0] and preyCoordinates[3] >= captureCoordinates[1]) and (preyCoordinates[2] <= captureCoordinates[2] and preyCoordinates[3] <= captureCoordinates[3]): # Prey Point 0 in Snake
                captured = True
            elif (preyCoordinates[0] <= captureCoordinates[2] and preyCoordinates[1] <= captureCoordinates[3]) and (preyCoordinates[0] >= captureCoordinates[0] and preyCoordinates[1] >= captureCoordinates[1]): # Prey Point 1 in Snake
                captured = True

            if captured:
                self.locks["prey"].acquire()
                self.preyCoordinates = self.createNewPrey()
                self.locks["prey"].release()

                incrementScore()
            return captured

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

    def updateGUI(self, gui: Gui) -> None:
        '''
            This method handles the queue by constantly retrieving
            tasks from it and accordingly taking the corresponding
            action.
            A task could be: game_over, move, prey, score.
            Each item in the queue is a dictionary whose key is
            the task type (for example, "move") and its value is
            the corresponding task value.
            If the queue.empty exception happens, it schedules
            to call itself after a short delay.
        '''
        def updateSnakeGUI() -> None:
            self.locks["move"].acquire()
            gui.canvas.coords(gui.snakeIcon, *[coord for point in self.snakeCoordinates for coord in point])
            self.locks["move"].release()
        def updatePreyGUI() -> None:
            self.locks["prey"].acquire()
            gui.canvas.coords(gui.preyIcon, *self.preyCoordinates)
            self.locks["prey"].release()
        def updateScoreGUI() -> None:
            self.locks["score"].acquire()
            gui.canvas.itemconfigure(gui.score, text=f"Your Score: {game.score}")
            self.locks["score"].release()

        gameNotOver: bool = True
        while gameNotOver:
            if self.locks["game_over"].acquire():
                gameNotOver: bool = self.gameNotOver # Read Game State
                self.locks["game_over"].release()

            if gameNotOver:
                updateSnakeGUI()
                updatePreyGUI()
                updateScoreGUI()
            else:
                gui.gameOver()

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

    def createNewPrey(self) -> list:
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

        return [
            generatedCoordinates[0] - PREY_ICON_WIDTH // 2, # x0
            generatedCoordinates[1] - PREY_ICON_WIDTH // 2, # y0
            generatedCoordinates[0] + PREY_ICON_WIDTH // 2, # x1
            generatedCoordinates[1] + PREY_ICON_WIDTH // 2 # y1
        ]


if __name__ == "__main__":
    #some constants for our GUI
    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 300
    SNAKE_ICON_WIDTH = 15
    PREY_ICON_WIDTH = 10
    #add the specified constant PREY_ICON_WIDTH here

    BACKGROUND_COLOUR = "black"   #you may change this colour if you wish
    ICON_COLOUR = "blue"        #you may change this colour if you wish

    game = Game()        #instantiate the game object
    gui = Gui()    #instantiate the game user interface

    handler = ComponentHandler() #instantiate the component handler

    #start a thread with the main loop of the game
    threading.Thread(target = game.superloop, daemon = True).start()
    #TODO -> Ask Professor if Alright to Update GUI Concurrently Outside Main Thread
    # threading.Thread(target = game.updateGUI, args = {gui, }, daemon = True).start()

    #start the GUI's own event loop
    gui.root.mainloop()