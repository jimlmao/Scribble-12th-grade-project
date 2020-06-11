"""
Made by Amir Wolberg
Classes used: socket, thread, time, PIL and tkinter
"""

from tkinter import *
from tkinter import ttk, colorchooser
import socket
import threading
import time
from PIL import ImageTk, Image

"""
No known bugs - QA required 
add transperancy
"""

'''
classes - each a different interface ((login screen) , (painter word choose) , (painter canvas)
and (watcher canvas+guessing))
'''

# User code


class UserLogin:
    """
    takes care of the login screen widgets and information sending , keeps the information of the user name
    and user role in global variables
    """

    def __init__(self, master):  # master is the root , the window
        """
        defining class variables and building the screen widgets of the login screen
        :param master:
        """
        self.master = master
        self.User = ''
        self.Role = ''

        self.welcome = Label(self.master, text='Welcome to scribble', bg='black', fg='white', font=("Courier", 28))
        self.welcome.pack()

        self.user_name = Label(self.master, text="UserName:", bg='black', fg='white', font=("Courier", 16))
        self.user_name.pack()

        self.user_name = Entry(self.master, bd=1)
        self.user_name.pack()

        self.user_role = Label(self.master,
                               text='Choose your role :', bg='black', fg='white', font=("Courier", 16))
        self.user_role.pack()

        self.watcher_button = Button(self.master, text="Watcher", command=self.add_watcher, bg='black', fg='white')
        self.watcher_button.pack()
        self.watcher_button.place(x=190, y=380)

        self.painter_button = Button(self.master, text="Painter", command=self.add_painter, bg='black', fg='white')
        self.painter_button.pack()
        self.painter_button.place(x=260, y=380)

    def add_watcher(self):
        """
        puts the username chosen and the role watcher into the global variables for name and role
        destroys the login window root
        """
        self.retrieve_input('watcher')
        self.master.destroy()

    def add_painter(self):
        """
         puts the username chosen and the role painter into the global variables for name and role
         destroys the login window root
        """
        self.retrieve_input('painter')
        self.master.destroy()

    def retrieve_input(self, role):
        """
        puts the information entered by the user into global variables that are then sent to the server
        in the main code
        """
        global Role
        global User
        User = self.user_name.get()
        Role = role


# Painter code


class PainterChoose:  # Handles the painter choosing a word to guess
    """
    takes care of the word choosing screen of the painter
    """

    def __init__(self, master):  # master is the root , the window
        """
        defining class variables and building the screen widgets of the word choosing screen
        :param master:
        """
        self.master = master
        self.welcome = Label(self.master, text='You are the painter', bg='Grey', font=("Courier", 20))
        self.welcome.pack()

        self.chosen_word = Message(self.master, text="Choose what to draw:",
                                   bg='Grey', font=("Courier", 14), width=450)
        self.chosen_word.pack()

        self.chosen_word = Entry(self.master, bd=1)
        self.chosen_word.pack()
        self.chosen_word.bind('<KeyPress>', self.enter_press_log)

        enter_button = Button(self.master, text="Enter", command=self.add_text)
        enter_button.pack()

        self.error1 = Label(self.master, text='', bg='Grey', font=("Courier", 14))
        self.lost_connection = Label(self.master, text="", fg='red', font=("Courier", 12))

        self.master.protocol("WM_DELETE_WINDOW", lambda: exit())

    def add_text(self):
        """
        checks if the chosen word is valid and if it is calls the function that sends it to the server
        """

        if len(str(self.chosen_word.get())) > 20:  # if the word is longer than 20 characters
            self.error1.destroy()
            self.error1 = Label(self.master, text='The word must be 20 characters or less', font=("Courier", 14))
            self.error1.pack()

        elif len(str(self.chosen_word.get())) == 0:  # if the word is blank
            self.error1.destroy()
            self.error1 = Label(self.master, text='Word must not be blank', font=("Courier", 14))
            self.error1.pack()

        elif str(self.chosen_word.get()) == '-9':
            # if the word is -9 which is the code for logging off and resetting watcher screen
            self.error1.destroy()
            self.error1 = Label(self.master, text='Word must not be -9', font=("Courier", 14))
            self.error1.pack()

        elif ';' in str(self.chosen_word.get()):
            # if the word has ; which is used to separate guesses in the server
            self.error1.destroy()
            self.error1 = Label(self.master, text='Word must not contain ;', font=("Courier", 14))
            self.error1.pack()

        else:  # if the word is valid
            self.retrieve_input()

    def enter_press_log(self, event):
        """
        if the user presses enter calls the add_text function
        :param event:
        """
        if event.keycode == 13:
            self.add_text()

    def retrieve_input(self):
        """
        sends the chosen word (to draw) to the server
        """
        print("the chosen word is: " + self.chosen_word.get())
        word = self.chosen_word.get()
        # noinspection PyBroadException
        try:
            s.send((str(word)).encode())
            self.master.destroy()
        except Exception:
            print('connection lost...')
            self.lost_connection.destroy()
            self.lost_connection = Label(self.master, text="Connection lost...", fg='red', font=("Courier", 12))
            self.lost_connection.pack()


class Painter:
    """
    takes care of the painter screen , widgets and painting
    and also sends all of the painting information to the server
    """

    def __init__(self, master):  # master is the root , the window
        """
        defining class variables and building the screen widgets of the painter
        :param master:
        """
        self.master = master
        # values for parameters used to paint
        self.color_fg = 'black'
        self.color_bg = 'white'
        self.pen_width = 5
        self.old_x = None
        self.old_y = None

        # values used in drawing the widgets later
        self.controls = None
        self.slider = None
        self.menu = Menu(self.master)
        self.color_menu = Menu(self.menu)

        # values received from or sent to the server
        self.winner_name = ''  # the name of the winner of the game
        self.time_of_game = ''  # the length of time it took for the game to end
        self.resetting_mouse = '1'  # 0 meaning the mouse is not reset , 1 meaning it is
        self.game_over = False  # if the game is over turns to True
        self.watchers_logged = 0  # number of watchers playing the game

        # setting up the canvas and label that shows the number of watchers watching
        self.c = Canvas(self.master, width=500, height=420, bg=self.color_bg, )
        self.c.pack(fill=BOTH, expand=False)
        self.watcher_label = Label(self.master, text=str(self.watchers_logged) + ' Watchers playing')
        self.watcher_label.pack()

        # calls the function responsible for the threads of the painter class
        self.painter_threading()

        # biding the mouse as the drawing tool
        self.c.bind('<B1-Motion>', self.paint)  # drawing the line
        self.c.bind('<ButtonRelease-1>', self.reset)  # when you release the button it stops painting

    def painter_threading(self):
        """
        handles the threads of the painter class
        """
        thread_gui = threading.Thread(target=self.draw_widgets)  # takes care of drawing the painting and sending it
        thread_end_game = threading.Thread(target=self.receive_data)  # takes care of receiving data from the server
        thread_gui.start()
        thread_end_game.start()

    def receive_data(self):
        """
        takes care of any data sent from the server to the painter
        also builds new widgets or changes old ones according to what the server instructs
        """
        while True:
            # noinspection PyBroadException
            try:
                data_painter = s.recv(10)
                data_painter = data_painter.decode()
                print(data_painter)

                if data_painter.startswith('num :'):  # tells the painter how many watchers logged before he did
                    self.watchers_logged = int(data_painter[5:])
                    print(str(self.watchers_logged) + ' Watchers playing')
                    self.watcher_label.configure(text=str(self.watchers_logged) + ' Watchers playing')

                if data_painter.startswith('+watcher'):  # informs the painter a watcher joined
                    self.watchers_logged += 1
                    self.watcher_label.configure(text=str(self.watchers_logged) + ' Watchers playing')

                if data_painter.startswith('-watcher'):  # informs the painter a watcher left
                    self.watchers_logged -= 1
                    self.watcher_label.configure(text=str(self.watchers_logged) + ' Watchers playing')

                if data_painter.startswith('game over'):  # tells the painter someone guessed the word and game over
                    data_winner = s.recv(4096)
                    data_winner = data_winner.decode()
                    print('the winner is ' + data_winner)
                    data_time_of_game = s.recv(4096).decode()
                    self.time_of_game = data_time_of_game  # the time it took from the moment the painter joined until
                    # someone guessed the word and won the game
                    self.game_over = True
                    self.winner_name = data_winner  # the name of the winner

                    # Building the leader boards screen of the painter
                    self.master.configure(background='blue')
                    self.c.delete(ALL)
                    self.watcher_label.destroy()
                    self.slider.destroy()
                    self.controls.destroy()
                    self.menu.destroy()
                    self.color_menu.destroy()
                    self.master.geometry("500x500")

                    # takes care of the leader boards image background
                    pic_2 = Image.open("leader_boards.png")
                    img_2 = pic_2.resize((500, 500), Image.ANTIALIAS)
                    img_2.save("leader_boards.png")
                    pic_2 = Image.open("leader_boards.png")
                    tk_pic_2 = ImageTk.PhotoImage(pic_2)
                    end_screen_label = Label(self.master, image=tk_pic_2)
                    end_screen_label.place(x=0, y=0, relwidth=1, relheight=1)
                    self.c.pack()

                    # takes care of the leader boards labels showing the winner's name and time
                    label1 = Label(self.master, text="Game Over!", bg='White', fg='Black', font=("Courier", 35))
                    label1.pack()
                    label2 = Label(self.master, text="The winner is:", bg='White', fg='Black', font=("Courier", 16))
                    label2.pack()
                    label2.place(x=163, y=50)
                    label3 = Message(self.master, text=self.winner_name, bg='Yellow', fg='Black', font=("Courier", 14),
                                     width=150)
                    label3.pack()
                    label3.place(x=195, y=80)
                    label4 = Label(self.master, text=self.time_of_game, font=("Courier", 12), bg='Black', fg='White')
                    label4.pack()
                    label4.place(x=228, y=279)

                    s.close()  # game is over disconnecting from the server
                    break
            except Exception:
                print('connection with server lost...')
                lost_connection = Label(self.master, text="Connection lost...", fg='red', font=("Courier", 12))
                lost_connection.pack()
                break

    def paint(self, e):
        """
        draws the lines and sends the coordinates and width of the drawn lines to the server
        :param e:
        """

        # Drawing the lines
        if self.old_x and self.old_y:
            self.c.create_line(self.old_x, self.old_y, e.x, e.y, width=self.pen_width, fill=self.color_fg,
                               capstyle=ROUND, smooth=True)
        self.old_x = e.x
        self.old_y = e.y

        # Sending the painted Coordinates(x y) + pen width (5-100) + whether the mouse is reset(1) or not(0)

        if -99 < e.x < 999 and -99 < e.y < 999:  # The coordinates must be no longer than triple digit numbers or
            # the server will kick the painter and have an error (because of the header size set for coordinates)

            pen_list_width = str(self.pen_width).split('.')
            pen_send_width = pen_list_width[0]  # Doesnt take all of the numbers (only the ones before the dot(5-100))
            line_info = ('Coordinates: ' + str(e.x) + ' ' + str(e.y) + ' ' + pen_send_width + ' ' +
                         self.resetting_mouse)
            # Coordinates = x coordinate y coordinate pen width (5-100) and whether the mouse is reset(1) or not(0)
            print(line_info)
            s.send(str(len(line_info)).encode())  # Header sending the length of the incoming message
            s.send(line_info.encode())  # Sends the server the line_info
            self.resetting_mouse = '0'

        else:  # if the coordinates went past their limit - reset the mouse
            self.resetting_mouse = '1'

    def reset(self, w):  # Resetting x and y when you stop clicking
        """
        when the painter stops clicking the mouse (painting) resets the old_x and old_y coordinates and changes
        the resetting_mouse parameter to 1 (meaning the mouse is reset)
        :param w:
        """
        self.old_x = None
        self.old_y = None
        print(w)
        print('resetting')
        self.resetting_mouse = '1'

    def change_width(self, e):  # changes the pen width
        """
        change Width of the pen through slider
        :param e:
        """
        self.pen_width = e

    def clear(self):
        """
        deletes all lines drawn on the canvas and tels the server it did so
        """

        self.c.delete(ALL)
        print('delete')
        s.send('-1'.encode())  # CODE FOR DELETING - -1

    def change_fg(self):  # changing the pen color
        """
        changes the color of the pen and sends the new pen color to the server
        """

        self.color_fg = colorchooser.askcolor(color=self.color_fg)[1]

        # sending the pen color
        pen_color = ('color: ' + str(self.color_fg))
        print(pen_color)
        s.send(str(len(pen_color)).encode())  # header , length of pen_color , must be '14'
        s.send(pen_color.encode())  # sends the new pen color

    def change_bg(self):  # changing the background color canvas
        """
        changes the background color or the canvas and sends the new background color to the server
        """

        self.color_bg = colorchooser.askcolor(color=self.color_bg)[1]
        self.c['bg'] = self.color_bg

        # sends the new background color to the server
        back_color = ('background_color_is: ' + str(self.color_bg))
        print(back_color)
        s.send(str(len(back_color)).encode())  # sends length , header of msg , its '28'
        s.send(back_color.encode())  # sends the new background color to the server

    def draw_widgets(self):
        """
        responsible for drawing the painter's widgets and menus and linking them to the right commands
        """

        self.controls = Frame(self.master, padx=5, pady=1)
        self.slider = ttk.Scale(self.controls, from_=5, to=100, command=self.change_width, orient=VERTICAL)
        self.slider.set(self.pen_width)
        self.slider.grid(row=0, column=1, ipadx=30)
        self.controls.pack(side=LEFT)

        self.master.config(menu=self.menu)
        self.menu.add_cascade(label='Colors', menu=self.color_menu)
        self.color_menu.add_command(label='Brush Color', command=self.change_fg)
        self.color_menu.add_command(label='Background Color', command=self.change_bg)
        option_menu = Menu(self.menu)
        self.menu.add_cascade(label='Options', menu=option_menu)
        option_menu.add_command(label='Clear Canvas', command=self.clear)
        option_menu.add_command(label='Exit', command=self.master.destroy)


# Watcher Code


class Watcher:  # class that only allows to guess and watch the drawing
    """
    Takes care of the watcher client , sends info , receives info and presents it to the player.
    """

    global ip  # ip of the server
    global port  # port number to connect to

    def __init__(self, master, w):  # master is the root , the window
        """
        defining class variables and building the screen widgets of the watcher
        :param master:
        :param w:
        """
        self.w = w
        self.master = master
        self.old_x = '0'
        self.old_y = '0'
        self.Background_color = '#ffffff'  # current background color
        self.Pen_color = '#000000'  # current Pen_color
        self.Painted_Coordinates = '000 000 5 1'  # x y pen_width and mouse state - 1 for reset 0 for not
        self.Guess_sent = True  # if its true no guess has been sent yet , otherwise the user has started guessing
        self.Winner = ''  # name of the winner
        self.game_time = ''  # the length of the game
        self.action_list = []  # paints the game if you joined late
        self.still_redrawing = False  # False when the action list is done being read and True when its still being read
        self.game_over = False  # Turns True when the game is over and some has won

        self.guess = Label(self.master, text='Guess', bg='khaki4', font=("Courier", 28))
        self.guess.pack()

        self.enter_guess = Label(self.master, text="Enter your guess here:", bg='khaki4', font=("Courier", 12))
        self.enter_guess.pack()

        self.guess_word = Entry(self.master, bd=1)
        self.guess_word.pack()
        self.guess_word.bind('<KeyPress>', self.enter_send)

        self.enter_button = Button(self.master, text=">>>>", command=self.add_text, bg='black', fg='white')
        self.enter_button.pack()

        self.sent_guess = Label(self.master, text="Guess sent", bg='khaki4', fg='white', font=("Courier", 10))

        self.wrong_guess = Label(self.master, text="Guess sent", bg='khaki4', fg='white', font=("Courier", 10))

        self.painter_logged = Label(self.master, text='', bg='khaki4', font=("Courier", 14))
        self.painter_logged.pack()

        thread_watcher = threading.Thread(target=self.watcher_info,)
        thread_watcher.start()

    def watcher_info(self):
        """
        takes care of data sent to the watcher by the server
        """
        while True:
            # noinspection PyBroadException
            try:
                data_watcher = s.recv(40)  # receives info
                data_watcher = data_watcher.decode("utf-8")
                print(data_watcher)

                if data_watcher.startswith('Game information incoming'):
                    pen_color_info = s.recv(7)
                    pen_color_info = pen_color_info.decode()
                    print(pen_color_info)
                    self.Pen_color = pen_color_info

                    self.still_redrawing = True  # now entering the redrawing phase
                    game_info = s.recv(1000000).decode()  # receives info
                    while 'stop;' not in game_info:  # takes the information of the entire game so far , can be large
                        game_info += s.recv(1000000).decode()  # receives info
                    print(game_info)
                    self.action_list = game_info.split(';')
                    thread_drawn_so_far = threading.Thread(target=self.drawn_so_far)
                    thread_drawn_so_far.start()

                if data_watcher.startswith('wrong'):
                    self.wrong_guess.destroy()
                    self.wrong_guess = Label(self.master, text="Wrong guess try again", bg='khaki4', fg='white',
                                             font=("Courier", 10))
                    self.wrong_guess.pack()

                if data_watcher.startswith('/close'):  # once u close the tab the server tells u to log out as well ,
                    # UNLESS the game is already over and then tab closes on its own and u go to leader boards
                    print('window closed')
                    break

                if data_watcher.startswith('painter logged on'):  # the painter is online
                    self.painter_logged.destroy()
                    self.painter_logged = Label(self.master, text='Painter Online', bg='khaki4', fg='green',
                                                font=("Courier", 14))
                    self.painter_logged.pack()

                if data_watcher.startswith('painter logged off'):  # the painter is offline
                    self.painter_logged.destroy()
                    self.painter_logged = Label(self.master, text='Painter Offline', bg='khaki4', fg='red',
                                                font=("Courier", 14))
                    self.painter_logged.pack()

                if data_watcher == 'game over':  # game is over someone won
                    print(data_watcher)
                    time.sleep(0.01)
                    data_winner_name = s.recv(4096)  # receives info
                    data_winner_name = data_winner_name.decode("utf-8")
                    self.Winner = data_winner_name  # name of the winner is saved
                    print(self.Winner)
                    data_game_time = s.recv(4096).decode()
                    self.game_time = str(data_game_time)
                    self.game_over = True  # Game is over
                    self.end_screen()  # goes into the leader boards
                    break

                if data_watcher == 'Game full':  # the game is full
                    print('| The game is full try again later |')
                    break

                if data_watcher.startswith('Pen:'):  # pen color
                    print(data_watcher[4:])  # takes only the color
                    self.Pen_color = data_watcher[4:]
                    if self.still_redrawing:
                        self.action_list.append('Pen:' + self.Pen_color)
                    else:
                        print('changed pen color')

                if data_watcher.startswith('Background:'):  # background color
                    print(data_watcher[11:])  # self.change_bg(data[11:])  # takes only the color
                    self.Background_color = data_watcher[11:]
                    if self.still_redrawing:
                        self.action_list.append('Background:' + self.Background_color)
                    else:
                        self.w['bg'] = self.Background_color
                    print('background changed to' + self.Background_color)

                if data_watcher.startswith('Delete'):  # Delete or not
                    print('delete')  # self.clear()  # YOU Need to clear right away and then change it back to false
                    print('deleting stuff')
                    if self.still_redrawing:
                        self.action_list.append('delete')
                    else:
                        self.w.delete(ALL)

                if data_watcher.startswith('reset_screen'):  # a new painter joined , resetting the watcher's screen
                    if self.still_redrawing:
                        self.action_list.append('reset_screen')
                    else:
                        print('resetting screen')
                        self.Background_color = '#ffffff'
                        self.w['bg'] = self.Background_color
                        self.w.delete(ALL)
                        self.Pen_color = '#000000'

                if data_watcher.startswith('Coordinates:') and len(data_watcher) < 27:  # Len shorter than 27 in case it
                    # sends extra info
                    print(data_watcher[12:])  # takes only the coordinates + pen width
                    self.Painted_Coordinates = data_watcher[12:]
                    if self.still_redrawing:
                        self.action_list.append('Coordinates:' + self.Painted_Coordinates)
                    else:
                        painted_list = self.Painted_Coordinates.split(' ')
                        x_ = painted_list[0]
                        y_ = painted_list[1]
                        pen_width = painted_list[2]  # pen_width is the pen width
                        reset = painted_list[3]
                        if reset == '0':
                            self.w.create_line(self.old_x, self.old_y, x_, y_, fill=self.Pen_color, width=pen_width,
                                               capstyle=ROUND, smooth=True)
                        if reset == '1':
                            self.w.create_line(x_, y_, str(int(x_) - 0.00001), str(int(y_) - 0.00001),
                                               fill=self.Pen_color, width=pen_width, capstyle=ROUND, smooth=True)
                        self.old_x = x_
                        self.old_y = y_
            except Exception:
                if not self.game_over:
                    print('connection lost...')
                    lost_connection = Label(self.master, text="Connection lost...", bg='khaki4', fg='red', font=(
                        "Courier", 12))
                    lost_connection.pack()
                else:
                    print('exception invalid , game already over')
                break

    def end_screen(self):
        """
        builds the watcher's leader boards screen
        +
        tells the server that the watcher has gone into the leader boards successfully and that it can now reset
        """
        self.w.delete(ALL)
        self.sent_guess.destroy()
        self.enter_guess.destroy()
        self.wrong_guess.destroy()
        self.guess.destroy()
        self.guess_word.destroy()
        self.enter_button.destroy()
        self.painter_logged.destroy()
        self.master.geometry("500x500")

        self.w.configure(bg='Grey')
        self.w.create_line(200, 120, 200, 220, fill='yellow', width=5,
                           capstyle=ROUND, smooth=True)
        self.w.create_line(200, 120, 300, 120, fill='yellow', width=5,
                           capstyle=ROUND, smooth=True)
        self.w.create_line(300, 120, 300, 220, fill='yellow', width=5,
                           capstyle=ROUND, smooth=True)
        label0 = Label(self.master, text="1", bg='Grey', fg='Yellow', font=("Courier", 32))
        label0.pack()
        label0.place(x=235, y=150)

        label1 = Label(self.master, text="Game Over!", bg='Khaki4', fg='Black', font=("Courier", 35))
        label1.pack()
        label2 = Label(self.master, text="The winner is:", bg='Grey', fg='Black', font=("Courier", 16))
        label2.pack()
        label2.place(x=163, y=50)
        label3 = Message(self.master, text=self.Winner, bg='Grey', fg='Black', font=("Courier", 14), width=150)
        label3.pack()
        label3.place(x=200, y=85)
        label4 = Label(self.master, text='Time of guess: ' + self.game_time,  font=("Courier", 12), bg='Grey',
                       fg='White')
        label4.pack()
        label4.place(x=180, y=280)

        s.send('end'.encode())  # tells the server it went smoothly into the leader boards
        data_database_updated = s.recv(1024).decode()  # waiting to hear from the server , when the client hears
        # from the server it knows that the data base has finished updating and the server can be told to reset now
        print(data_database_updated)
        s.close()  # game over disconnecting

        s_reset = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Af_inet - ipv4 ,sock_stream - tcp
        s_reset.connect((ip, port))  # new socket connected to tell the server to reset
        s_reset.send('reset server'.encode())
        s_reset.close()

    def add_text(self):
        """
        tells the watcher the guess was sent
        calls the function that sends the guess to the server
        """
        self.wrong_guess.destroy()
        self.sent_guess.destroy()
        self.sent_guess = Label(self.master, text="Sending guess...", bg='khaki4', fg='white', font=("Courier", 10))
        self.sent_guess.pack()
        self.retrieve_input()

    def retrieve_input(self):
        """
        sends the watcher's guess to the server
        """
        print(self.guess_word.get())
        if ';' not in self.guess_word.get():
            # noinspection PyBroadException
            try:
                s.send(('guessed:' + str(self.guess_word.get())).encode())
                self.sent_guess.destroy()
                self.sent_guess = Label(self.master, text="Guess sent", bg='khaki4', fg='white',
                                        font=("Courier", 10))
                self.sent_guess.pack()
            except Exception:
                print('guess did not make it to the server')
                self.sent_guess.destroy()
                self.sent_guess = Label(self.master, text="try again, guess not sent", bg='khaki4', fg='white', font=(
                    "Courier", 10))
                self.sent_guess.pack()
        else:
            self.sent_guess.destroy()
            self.sent_guess = Label(self.master, text="guess must not contain ;", bg='khaki4', fg='white', font=(
                "Courier", 10))
            self.sent_guess.pack()

    def enter_send(self, event):
        """
        sends guess when you press enter
        :param event:
        """
        if event.keycode == 13:
            self.add_text()

    def drawn_so_far(self):
        """
        Draws the game up until the watcher catches on and gets the game
        broadcast to him live
        """
        first_line = True  # is True for the first line drawn
        old_x_drawn = '0'
        old_y_drawn = '0'
        pen_color = '#000000'
        for act in self.action_list:
            if act.startswith('Coordinates:'):  # paints the coordinates
                draw = act[12:]
                draw_list = draw.split(' ')
                x = draw_list[0]
                y = draw_list[1]
                pen_width = draw_list[2]  # pen_width is the pen width
                reset = draw_list[3]
                if reset == '0' and not first_line:  # meaning the mouse has not reset
                    self.w.create_line(old_x_drawn, old_y_drawn,
                                       x, y, fill=pen_color, width=pen_width, capstyle=ROUND, smooth=True)
                if reset == '1' or first_line:  # meaning the mouse has reset
                    self.w.create_line(x, y, str(int(x) - 0.00001), str(int(y) - 0.00001),
                                       fill=pen_color, width=pen_width, capstyle=ROUND, smooth=True)
                    first_line = False  # we are past the first line drawn
                old_x_drawn = x
                old_y_drawn = y

            if act.startswith('Pen:'):  # changes the pen color
                pen_color = act[4:]
                print('pen color changed to' + pen_color)

            if act.startswith('delete'):  # deletes coordinates painted thus far
                print('delete')
                self.w.delete(ALL)

            if act.startswith('reset_screen'):
                print('resetting screen')
                self.Background_color = '#ffffff'
                self.w['bg'] = self.Background_color
                self.w.delete(ALL)
                pen_color = '#000000'

            if act.startswith('Background:'):  # changes background color
                self.w['bg'] = act[11:]
                print('background changed to' + act[11:])

            if self.game_over:  # the game is over stop drawing
                break

        self.Pen_color = pen_color
        self.old_x = old_x_drawn
        self.old_y = old_y_drawn
        self.still_redrawing = False


'''
Main code
'''
if __name__ == '__main__':
    '''
    Globals
    '''
    global Role  # the role chosen by the user
    global User  # the user name
    ip = '127.0.0.1'  # ip of the server
    port = 5001  # port number to connect to

    '''
    Functions
    '''
    def on_closing_watcher(socket_: socket.socket):  # Informs the server a watcher has left
        """
        takes care of what happens when the watcher closes the window and randomly disconnects
        :param socket_:
        """
        # noinspection PyBroadException
        try:
            socket_.send('/close'.encode())
            print('window closed')
        except Exception:
            print('game already over , server reset/server crashed')

    def painter_chosen():  # takes care of what happens when you are the painter
        """
        takes care of what happens when you choose to be the painter
        first enters the painter choose class in which the painter chooses what to draw
        and then enters the drawing board class of the painter
        after the game is over or if the painter disconnects closes the socket and informs the server that the painter
        left
        """
        # WORD CHOOSING ROOT
        root_painter_word = Tk()
        root_painter_word.title("Painter")
        root_painter_word.wm_iconbitmap('scribble_logo.ico')
        root_painter_word.geometry("450x150")
        root_painter_word.resizable(width=False, height=False)
        root_painter_word.configure(background='Grey')
        PainterChoose(root_painter_word)  # the window in which you choose what to draw
        root_painter_word.mainloop()
        # resetting the watcher's screen whenever a painter is chosen
        # noinspection PyBroadException
        try:
            s.send('-9'.encode())  # -9 is the code for resetting the settings of the watcher or if its sent instead of
            # a word it lets the server know the painter logged out
        except Exception:
            print('connection lost...')

        # whenever a new painter logs - DRAWING ROOT

        root_painter = Tk()
        Painter(root_painter)  # the root in which you draw
        root_painter.title('Painter')
        root_painter.geometry("500x580")
        root_painter.resizable(width=False, height=False)
        root_painter.wm_iconbitmap('scribble_logo.ico')

        root_painter.mainloop()
        # noinspection PyBroadException
        try:
            s.send('-3'.encode())  # -3 code for logging off tells the server the painter has logged out
        except Exception:
            print('game already ended so no need to inform the server that the painter has logged out')
        s.close()

    def watcher_chosen():  # takes care of what happens if you're a watcher
        """
        builds the watcher tk window and canvas and then runs the watcher class
        when the watcher disconnects class the function that tells the server the watcher has disconnected
        """
        # WATCHING ROOT
        root_watch = Tk()
        root_watch.title('Watcher')
        root_watch.wm_iconbitmap('watcher_logo.ico')
        root_watch.configure(bg='khaki4')
        root_watch.resizable(width=False, height=False)
        w = Canvas(root_watch, width=500, height=420, bg="white", )
        w.pack(fill=BOTH, expand=False)
        Watcher(root_watch, w)
        root_watch.mainloop()
        on_closing_watcher(s)

    '''
    Main
    '''

    restart_painter = False  # if there is already a painter turns True
    restart_watcher = False  # if there are already 5 watchers turns True
    restart_user = False  # if user name is invalid turns True
    restart_name = False  # if the name is already taken turns True
    server_closed = False  # if the server is not open turns True

    while True:
        root = Tk()  # builds the base root , the logging window
        root.title("Scribble")
        root.wm_iconbitmap('scribble_logo.ico')
        root.geometry("500x500")
        root.resizable(width=False, height=False)
        root.configure(background='Black')
        C = Canvas(root, bg="black", height=250, width=300)

        pic = Image.open("login_screen.png")
        img = pic.resize((500, 500), Image.ANTIALIAS)
        img.save("login_screen.png")
        pic = Image.open("login_screen.png")
        tk_pic = ImageTk.PhotoImage(pic)

        background_label = Label(root, image=tk_pic)
        background_label.place(x=0, y=0, relwidth=1, relheight=1)
        C.pack()

        UserLogin(root)  # calls the class taking care of the login window

        if server_closed is True:  # if the server is closed
            closed_server = Message(root, text="The server is closed at the moment , please try another time...", font=(
                                                                                            "Courier", 7), width=200)
            closed_server.pack()
            closed_server.place(x=150, y=430)
            server_closed = False
            Role = None  # resets the role
            User = None  # resets the nickname

        if restart_painter is True:  # if there is already a painter
            chosen_painter = Message(root, text="there is already a painter please choose a different role", font=(
                                                                                            "Courier", 7), width=200)
            chosen_painter.pack()
            chosen_painter.place(x=150, y=430)
            restart_painter = False
            Role = None  # resets the role
            User = None  # resets the nickname 

        if restart_watcher is True:  # if there are already 5 watchers
            chosen_watcher = Message(root, text="the max amount of watchers was reached please choose a different role",
                                     font=("Courier", 7), width=200)
            chosen_watcher.pack()
            chosen_watcher.place(x=150, y=430)
            restart_watcher = False
            Role = None  # resets the role
            User = None  # resets the nickname

        if restart_name is True:  # if the watcher's user name is already taken
            taken_name = Message(root, text="This user name is already taken please choose a different one",
                                 font=("Courier", 7), width=200)
            taken_name.pack()
            taken_name.place(x=150, y=430)
            restart_name = False
            Role = None  # resets the role
            User = None  # resets the nickname

        if restart_user is True:  # if the username entered is invalid
            invalid_name = Message(root,
                                   text="user name is invalid (contains ';'/' ' , blank or is longer than 10 characters"
                                        "), please enter a different user name", font=("Courier", 7), width=200)
            invalid_name.pack()
            invalid_name.place(x=150, y=430)
            restart_user = False
            Role = None  # resets the role
            User = None  # resets the nickname

        root.mainloop()
        # noinspection PyBroadException
        try:
            if Role is None:  # role must be either watcher or painter
                break
        except Exception:
            print('role is not defined yet , window closed')
            break

        else:
            client_role = Role  # either painter or watcher
            user_name = User  # name of the user
            user_name_checker = False  # checks the validity of the user name entered

            if ' ' in user_name or ';' in user_name:  # checks if the user name contains spaces (' ') or ';'
                user_name_checker = True

            if not type(user_name) is str:  # making sure there isn't a syntax error when checking length of user_name
                user_name = str(user_name)
                print(user_name)

            if not type(client_role) is str:  # making sure there isn't a syntax error when adding to client_role
                client_role = str(client_role)
                print(client_role)

            if len(user_name) > 10 or len(user_name) == 0 or user_name_checker:
                # if the user name is too long or is 0 letters or contains ';'/' ' restarts
                restart_user = True
                continue

            else:  # user name is valid
                user_info = client_role + ';' + user_name  # separated by a ';'

                # sockets - establishing connection
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Af_inet - ipv4 ,sock_stream - tcp
                # noinspection PyBroadException
                try:
                    s.connect((ip, port))
                    s.send(user_info.encode())  # sends the user info to the server (user name and desired role)
                except Exception:  # server is closed
                    server_closed = True
                    continue

                if client_role == 'painter':  # what happens when you choose painter as your role
                    # noinspection PyBroadException
                    try:
                        data = s.recv(100)
                    except Exception:  # if the server is closed/crashed
                        print('server closed/crashed')
                        server_closed = True
                        continue

                    data = data.decode()
                    if data == 'you are now the painter':  # meaning there is no other painter logged to the server atm
                        painter_chosen()  # you are now the painter , runs the painter function
                        break
                    else:  # there is already another painter logged to the server , restarts
                        print('there is already a painter, restart and choose a different role')
                        restart_painter = True
                        continue

                else:  # what happens when you choose watcher as your role
                    # noinspection PyBroadException
                    try:
                        data = s.recv(10)  # either game full , name taken or you joined
                    except Exception:  # if the server is closed/crashed
                        print('server closed/crashed')
                        server_closed = True
                        continue

                    data = data.decode()
                    print(data)

                    if data == 'Game full':  # meaning there are 5 watchers logged in , restarts.
                        restart_watcher = True
                        continue
                    if data == 'Name Taken':  # the user name you chose is already taken by another watcher , restarts.
                        restart_name = True
                        continue
                    else:  # meaning there are less than the max number of watchers logged in and the name is not taken
                        watcher_chosen()  # you are now a watcher , runs the watcher function
                        break
