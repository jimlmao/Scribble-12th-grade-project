"""
Made by Amir Wolberg
Classes used: socket , select , functools, time , sqlite3, thread and tkinter
"""
import socket
import threading
import select
import time
import sqlite3
from tkinter import *
from functools import partial

"""
No bugs known - need to QA
add option to choose how many watchers can play
"""
"""
Classes
"""


class PaintServer:
    """
    class that takes care of receiving and sending information from the painter to the watchers after the manager
    starts a new game
    """

    def __init__(self):
        """
        defines all of the class variables and starting the incoming_connections function
        """

        self.Background_color = '#ffffff'  # current background color
        self.Pen_color = '#000000'  # current Pen_color
        self.Painted_Coordinates = '000 000 5 1'  # x , y , pen width and mouse state(reset(1) or not reset(0))
        self.Previous_Coordinates = '000 000 5 1'  # the coordinates previously painted
        self.game_time = '0'  # the time from the moment the painter entered a word until someone won

        self.watchers_logged = 0  # watchers currently connected to the server , max is 5
        self.watchers_were_logged = 0  # number of watchers who were present in the game at any point
        self.watchers_enter_database = 0  # tells us how many watchers had their guesses put in self.guess_list

        self.watcher_list = []  # list containing the sockets of all of the logged watchers
        self.watcher_name_list = []  # list containing the names of all of the logged watchers
        self.guess_list = []  # keeps all of the guesses of different clients , has lists in it , in those lists each
        # belonging to a different watcher are the guesses

        self.painter_chosen = False  # True if a painter is online , False if there is no painter
        self.game_over = False  # when a client guesses the right word this changes to True and the game is over

        self.database_information = ''  # keeps all of the details of the painting for the database
        self.Winner = ''  # will contain the name of the winner

        self.start_of_game = None  # contains the time of the game's start , when the latest painter chose a word
        self.guess_word = None  # contains the word that needs to be guessed , the name of the painting
        self.painter_socket = None  # contains the current painter's socket

        self.incoming_connection()

    def incoming_connection(self):  # waits for incoming connections and adds them to the list
        """
        handles each connection from a client to the server using sockets
        starts the threads of either the watcher or painter depending on the information sent to it by the client
        """

        while not self.game_over:
            print('still in incoming_connection')

            read_list = select.select([s], [], [])[0]  # waits for a socket connection

            if self.game_over:
                break

            if read_list:  # if a socket connection was received , takes care of the specific socket
                # noinspection PyBroadException
                try:
                    client_socket, address = s.accept()
                    data = client_socket.recv(4096).decode('utf-8')
                    print(data)  # either name and role of the client or a confirmation to reset the server

                    if data.startswith('reset server'):  # not a client but a msg confirming the game is over
                        continue

                    data_list = data.split(';')
                    role = data_list[0]
                    name = data_list[1]
                    print('user role is:' + role)
                    print('user name is:' + name)

                    # If the role is painter
                    if role == 'painter' and not self.painter_chosen:  # only 1 painter can be online at a time
                        print('the painter is chosen')

                        # noinspection PyBroadException
                        try:
                            client_socket.send('you are now the painter'.encode())
                            self.painter_chosen = True

                            thread_transmit = threading.Thread(target=self.painter_client, args=(client_socket,))
                            thread_transmit.start()
                            # thread that takes information from the painter and sends it to all of the watchers

                        except Exception:  # when the painter disconnects can cause an error and jump to the exception
                            print('jumped error!')
                            self.painter_chosen = False  # the painter has disconnected
                            continue

                    elif role == 'painter' and self.painter_chosen:  # a painter is already online
                        print('reached the limit of painters')
                        # noinspection PyBroadException
                        try:
                            client_socket.send('painter already chosen'.encode())
                        except Exception:
                            print('client disconnected before msg was sent')
                        continue

                    # If the role is watcher ( takes the role as watcher automatically if its anything except painter)
                    else:
                        print(name)
                        print(self.watcher_name_list)

                        if name in self.watcher_name_list:  # can't have multiple watchers with the same name
                            # noinspection PyBroadException
                            try:
                                client_socket.send('Name Taken'.encode())
                            except Exception:
                                print('watcher logged off before name taken was sent')

                        else:  # name is valid and the role is watcher
                            global watcher_number  # the chosen max number of watchers allowed to play
                            if self.watchers_logged < int(watcher_number):
                                # up to x watchers are allowed to be online at the same time

                                # noinspection PyBroadException
                                try:
                                    client_socket.send('You joined'.encode())

                                    if self.painter_chosen:
                                        client_socket.send('painter logged on'.encode())
                                        print('painter is on')
                                        # tells the watchers a painter is logged

                                    if not self.painter_chosen:
                                        client_socket.send('painter logged off'.encode())
                                        print('painter is off')
                                        # tells the watchers there is no painter
                                except Exception:
                                    print('watcher crashed/logged off before starting its thread')
                                    continue

                                self.watchers_logged += 1
                                self.watchers_were_logged += 1
                                self.watcher_name_list.append(name)

                                # noinspection PyBroadException
                                try:
                                    self.painter_socket.send('+watcher'.encode())
                                    # tells painter another watcher logged
                                except Exception:
                                    print('no painter logged yet')

                                print('number of watchers logged: ' + str(self.watchers_logged))
                                self.watcher_list.append(client_socket)

                                thread_watcher = threading.Thread(target=self.watcher_client_receive, args=(
                                    client_socket, name))
                                # thread handling the information sent by the watcher to the server
                                thread_watcher.start()

                            else:  # max watchers already online
                                print('reached the limit of watchers')
                                # noinspection PyBroadException
                                try:
                                    client_socket.send('Game full'.encode())
                                except Exception:
                                    print('client logged off so Game full was not sent')
                                continue
                except Exception:
                    print('an error occurred in incoming_connections , moving on to the next client')
                    continue

    def painter_client(self, painter_socket: socket.socket):
        """
        Handles receiving information from the painter client and broadcasting it to the watchers
        :param painter_socket:
        """
        for watcher in self.watcher_list:
            watcher.send('painter logged on'.encode())  # tells the watchers a painter has logged

        # noinspection PyBroadException
        try:
            data_word = painter_socket.recv(21)  # word mut not be longer than 20 characters
            data_word = data_word.decode()
            if data_word == '-9':
                # If The word entered was blank it sends '-9' and the painter is kicked or if painter logged off
                print('connection aborted , word entered was blank , painter kicked')
                self.painter_chosen = False
                self.painter_socket = None
                for watcher in self.watcher_list:
                    watcher.send('painter logged off'.encode())  # tells the watchers a painter has logged off
            else:
                self.guess_word = str(data_word)  # what the painter is drawing
                print("the word to guess is: " + self.guess_word)

        except Exception:
            self.painter_socket = None
            self.painter_chosen = False
            for watcher in self.watcher_list:
                watcher.send('painter logged off'.encode())  # tells the watchers a painter has logged off
            print('jumped error! (1) painter crashed/logged off')

        if self.painter_chosen:  # if the painter has not been kicked out continue

            self.start_of_game = time.time()  # when the painter logs the game has officially started
            print('game has started time is : ' + str(self.start_of_game))

            for watcher in self.watcher_list:
                watcher.send('painter logged on'.encode())  # tells the watchers a painter has logged
            self.painter_socket = painter_socket  # painter has gone through the validation process, its socket is kept

            print('num :' + str(self.watchers_logged))
            # noinspection PyBroadException
            try:
                self.painter_socket.send(('num :' + str(self.watchers_logged)).encode())
                # tells the painter how many watchers are logged
            except Exception:
                self.painter_socket = None
                self.painter_chosen = False
                for watcher in self.watcher_list:
                    watcher.send('painter logged off'.encode())  # tells the watchers a painter has logged off
                print('jumped error! (2) painter crashed/logged off')

            if self.painter_chosen:  # if the painter has not been kicked out start its loop
                while not self.game_over:
                    print('still in painter_client')
                    # noinspection PyBroadException
                    try:
                        '''
                        maximum length of the 2 digit number representing the msgs length 
                        each number is a header for a certain type of information:
                       -3 for painter logging out, -9 for resetting watcher screen, -1 for deleting,
                        15-26 for painted coordinates, 14 for pen color , 28 for background color
                        '''
                        data = painter_socket.recv(2)  # maximum length of the 2 digit number - header
                        data = data.decode()  # also checks if at any given moment the painter crashed

                    except Exception:  # error occurred, the painter has timed out (disconnected)
                        print('jumped error! (3) painter crashed/logged off')
                        self.painter_chosen = False  # the painter has disconnected
                        self.painter_socket = None
                        for watcher in self.watcher_list:
                            watcher.send('painter logged off'.encode())  # tells the watchers the painter has logged off
                        break

                    # noinspection PyBroadException
                    try:

                        if self.game_over:
                            break

                        if data == '-3':  # meaning the current painter has closed the tab and logged out
                            print('painter logged out')
                            for watcher in self.watcher_list:
                                watcher.send('painter logged off'.encode())  # tells the watchers painter has logged off
                            self.painter_chosen = False
                            self.painter_socket = None
                            break

                        if data == '-9':  # -9 is code for resetting the watchers screen happens when a new painter logs
                            print('resetting screen')
                            self.database_information = ''  # empties database painting information
                            for client in self.watcher_list:
                                client.send('reset_screen'.encode())  # reset_screen code for resetting watchers screen

                        if data == '-1':  # -1 is the code for deleting (clearing the screen)
                            print('delete')
                            self.database_information = 'Pen:' + self.Pen_color + ';' + 'Background:' +\
                                                        self.Background_color + ';'  # removes the painted coordinates
                            for client in self.watcher_list:
                                client.send('Delete'.encode())

                        if 27 > int(data) > 14:  # meaning it has to be a coordinate (+ width of pen + mouse state)
                            # Coordinates: xxx yyy www m - the template in which its sent
                            data = painter_socket.recv(int(data))
                            data = data.decode()
                            print(data[13:])  # return coordinates x ,y and pen width + mouse state
                            self.Painted_Coordinates = data[13:]
                            self.database_information += 'Coordinates:' + self.Painted_Coordinates + ';'
                            if not (self.Previous_Coordinates == self.Painted_Coordinates):  # so it doesn't resend
                                for client in self.watcher_list:
                                    client.send(('Coordinates:' + self.Painted_Coordinates).encode())
                                self.Previous_Coordinates = self.Painted_Coordinates

                        if data == '14':  # 'color: '
                            data = painter_socket.recv(14)  # size of 14
                            data = data.decode()
                            print(data[7:])  # color changed to
                            self.Pen_color = data[7:]
                            self.database_information += 'Pen:' + self.Pen_color + ';'
                            pen_send = ('Pen:' + self.Pen_color)
                            for client in self.watcher_list:
                                client.send(pen_send.encode())

                        if data == '28':  # background_color:
                            data = painter_socket.recv(28)  # size of 28
                            data = data.decode()
                            print(data[21:])  # background changed to
                            self.Background_color = data[21:]
                            self.database_information += 'Background:' + self.Background_color + ';'
                            background_send = ('Background:' + self.Background_color)
                            for client in self.watcher_list:
                                client.send(background_send.encode())

                    except Exception:  # happens when the painter disconnects or times out
                        print('jumped error!(4) painter crashed/logged off')
                        for watcher in self.watcher_list:
                            watcher.send('painter logged off'.encode())  # tells the watchers the painter has logged off
                        self.painter_chosen = False  # the painter has disconnected
                        self.painter_socket = None
                        break

    def watcher_client_receive(self, watcher_socket: socket.socket, watcher_name):
        """
        Handles information received from the watcher (mainly guesses)
        Handles information sent to the watcher by the server (not by the painter)
        also keeps watcher guesses to add to the database
        :param watcher_socket:
        :param watcher_name:
        """
        guess_word_list = []  # list of all of the watcher's guesses

        time.sleep(0.2)  # cool down needed after the last packet sent to the watcher (if painter is on or not)
        if len(self.database_information) != 0:  # meaning the game has started before the watcher joined
            # noinspection PyBroadException
            try:
                watcher_socket.send('Game information incoming'.encode())  # warning watcher client to prepare for info

                watcher_socket.send(self.Pen_color.encode())  # sends the currently pen color to the watcher

                self.database_information += 'stop;'  # tells watcher when to stop receiving information - header
                watcher_socket.send(self.database_information.encode())
            except Exception:
                print("watcher connection lost (1)")

        while not self.game_over:
            print('still in watcher_client_receive')
            # noinspection PyBroadException
            try:
                data = watcher_socket.recv(1024)  # also checks at any given moment if the watcher did not crash
                data = data.decode()

                if data.startswith('end'):  # meaning the game has ended and the watcher entered the leader boards
                    break

                if data.startswith('/close'):  # meaning the watcher closed the tab
                    self.watchers_logged -= 1  # a watcher has disconnected
                    self.watcher_name_list.remove(watcher_name)
                    self.watcher_list.remove(watcher_socket)
                    watcher_socket.send('/close'.encode())  # the connection has been shut down successfully
                    # noinspection PyBroadException
                    try:
                        self.painter_socket.send('-watcher'.encode())  # informs the painter a watcher has logged off
                    except Exception:
                        print('error occurred - the painter has not logged yet so we can not send it information')
                    break

                if data.startswith('guessed:'):  # a guess sent by the watcher
                    word_guessed = str(data[8:])

                    # noinspection PyBroadException
                    try:
                        if word_guessed == self.guess_word:  # if the watcher guessed correctly
                            current_time = time.time()
                            time_of_guess = current_time - self.start_of_game
                            time_format = time.strftime("%M:%S", time.gmtime(time_of_guess))  # the time of guess
                            print(time_format)

                            guess_data = watcher_name + '  = > correct guess : ' + str(data[8:]) + ' , ' +\
                                                        str(time_format)
                            guess_word_list.append(guess_data)  # enters guessed word

                            print('the client has guessed the word')
                            self.game_over = True  # the client has guessed the correct word and the game is over
                            self.Winner = watcher_name
                            self.game_time = str(time_format)
                            print(self.Winner)
                            thread_over = threading.Thread(target=self.game_ended)
                            thread_over.start()
                            break

                        else:
                            current_time = time.time()
                            time_of_guess = current_time - self.start_of_game
                            time_format = time.strftime("%M:%S", time.gmtime(time_of_guess))  # the time of guess
                            print(time_format)

                            guess_data = watcher_name + ' => wrong guess : ' + str(data[8:]) + ', ' + str(time_format)
                            guess_word_list.append(guess_data)  # enters guessed word

                            watcher_socket.send('wrong'.encode())
                            print('guess again')

                    except Exception:
                        print('error occurred - no painter has logged yet and the game did not start yet')
            except Exception:
                print('watcher connection lost (2)')
                self.watchers_logged -= 1  # a watcher has disconnected or crashed
                self.watcher_name_list.remove(watcher_name)
                self.watcher_list.remove(watcher_socket)
                # noinspection PyBroadException
                try:
                    self.painter_socket.send('-watcher'.encode())  # informs the painter a watcher has logged off
                except Exception:
                    print('error occurred - the painter has logged yet so we can not send it information')
                break

        print('appending guesses of ' + watcher_name)
        self.guess_list.append(guess_word_list)
        self.watchers_enter_database += 1  # another watcher's guesses were put into self.guess_list
        print(self.watchers_enter_database)

    def game_ended(self):
        """
        takes care of what happens when a watcher wins and the game
        is over
        """
        time.sleep(0.1)

        print('Game has ended going into leader boards')
        for client in self.watcher_list:  # Tells all watchers the game is over
            # noinspection PyBroadException
            try:
                self.game_over_socket(client)
            except Exception:
                print('a watcher has crashed - game over information to it not sent')

        if self.painter_chosen:
            # noinspection PyBroadException
            try:
                self.game_over_socket(self.painter_socket)  # if a painter is logged tells him the game is over
            except Exception:
                print('painter logged off/crashed , did not send winning screen')

        print(self.database_information)  # paintings details at the end of the game that go into the database

        '''
        this part waits 5 seconds for all of the watchers to confirm they have entered their guesses into the
        self.guess_list variable , if 1 or more haven't done it in under 5 seconds the server does not keep
        their guesses in the database 
        '''
        time_counter = 0
        game_watcher_guesses_data = ''
        while True:
            time_counter += 1

            time.sleep(1)  # this while loop can run up to 5 times , with this its about 5 seconds
            print(self.watchers_enter_database)
            print(self.watchers_logged)
            print(self.watchers_were_logged)  # whenever a watcher starts the thread that at the end of he gets
            # uploaded into the database self.watchers_were_logged grows by 1 , which is why we use it to
            # compare to self.watchers_enter_database which at the end of said thread grows by 1

            if self.watchers_enter_database >= self.watchers_were_logged or time_counter > 4:
                # makes sure all watchers have entered their information into the database
                for user in self.guess_list:
                    for guess in user:
                        game_watcher_guesses_data += guess + ' ; '
                if time_counter > 4:  # 1 or more users timed out and took more than 5 seconds to confirm
                    print('One or more of the users data has not entered the database because they timed out')
                    game_watcher_guesses_data += 'Note - 1 or more users have timed out of the game ;'
                conn = sqlite3.connect('scribble_database.db')
                conn.execute("INSERT INTO paintings VALUES (NULL, ?, ?, ?);",
                             (self.guess_word, self.database_information, game_watcher_guesses_data))
                conn.commit()
                conn.close()
                print('Record created successfully')
                for sock in self.watcher_list:
                    # noinspection PyBroadException
                    try:
                        sock.send('database updated'.encode())  # tells the watchers the database has been
                        #  updated and that they can now send the server the reset signal
                    except Exception:
                        print('watcher crashed or logged off , database confirmation not sent to it')
                # the database had been updated with this game's information
                break

    def game_over_socket(self, socket_: socket.socket):
        """
        receives a socket and tells it the game is over , then sends the winner and length of the game
        :param socket_:
        """
        socket_.send('game over'.encode())  # informs that the game is over
        time.sleep(0.01)
        print('== > sending the winner : ' + self.Winner)
        socket_.send(self.Winner.encode())  # tells players who won
        time.sleep(0.01)
        print('== > sending the length of the game: ' + self.game_time)
        socket_.send(self.game_time.encode())  # sends the length of the game


class Manager:
    """
    takes care of the manager window , handling the database information and presenting previous games
    in addition to being responsible for opening the server for a new game
    """

    def __init__(self):
        """
        creates the widgets and parameters used in the Manager class
        """

        # Parameters that change when the painting is drawn , used to present the painting
        self.pen_color = 'Black'
        self.background_color = 'White'
        self.old_x = '0'
        self.old_y = '0'
        self.shown_games_list = []

        # Defining the tk window and canvas
        self.master = Tk()
        self.master.title("Scribble server")
        self.master.wm_iconbitmap('scribble_logo.ico')
        self.master.geometry("850x500")
        self.master.resizable(width=False, height=False)
        self.master.configure(background='Black')
        self.w = Canvas(self.master, width=500, height=420, bg="white", )
        self.w.pack()
        self.w.place(x=340, y=7)

        # defining what happens if you close the window
        self.master.protocol("WM_DELETE_WINDOW", lambda: exit())

        # finding all available game ids in the data base
        conn_0 = sqlite3.connect('scribble_database.db')
        cur_0 = conn_0.cursor()
        cur_0.execute("SELECT * FROM paintings")

        rows_0 = cur_0.fetchall()  # rows_0 holds all of the rows in the database table(paintings)

        # Defining labels who are currently unused
        self.painting_name = Label(self.master, text='', bg='Black', fg='White', font=20)  # the name of shown painting
        self.action_label = Label(self.master, text='', bg='Black', fg='Red')  # label describing the action taken

        # Defining labels currently in use

        # displays available game IDs in menu bars

        self.menu_bar = Menu(self.master)
        self.guess_menu = Menu(self.menu_bar)
        self.file_menu = Menu(self.menu_bar, tearoff=1)
        self.command_list = []
        for row_0 in rows_0:  # for each row in the table
            self.command_list.append(row_0[0])  # adds the Game id (the first item in every row of the table)
            self.file_menu.add_command(label=str(row_0[0]),
                                       command=partial(self.insert_game, str(row_0[0])))
            print(row_0[0])

        self.menu_bar.add_cascade(label="Available game IDs: ", menu=self.file_menu)  # shows available game ids
        self.menu_bar.add_cascade(label="Guesses of displayed games: ", menu=self.guess_menu)

        self.master.config(menu=self.menu_bar)  # puts the menu bar in the tk window

        # displaying a new game
        label_ = Label(self.master, text="Enter the ID of the game you want to display: ", bg='Black', fg='White')
        label_.pack()
        label_.place(x=5, y=10)

        self.game_number = Entry(self.master, bd=1)  # here the id of the game the manager wishes to present is written
        self.game_number.pack()
        self.game_number.place(x=55, y=35)
        self.game_number.bind('<KeyPress>', self.enter_press_log_show)

        self.enter_button = Button(self.master, text="Display", command=lambda: self.show_game(self.game_number.get()))
        self.enter_button.pack()
        self.enter_button.place(x=95, y=60)

        # deleting a specific game ID
        label_1 = Label(self.master, text="Enter the ID of the game you want to delete: ", bg='Black', fg='White')
        label_1.pack()
        label_1.place(x=5, y=120)

        self.delete_id = Entry(self.master, bd=1)  # here the id of the game the manager wishes to delete is written
        self.delete_id.pack()
        self.delete_id.place(x=55, y=145)
        self.delete_id.bind('<KeyPress>', self.enter_press_log_delete)

        self.delete_id_button = Button(self.master, text="Delete",
                                       command=lambda: self.delete_a_game(self.delete_id.get()))
        self.delete_id_button.pack()
        self.delete_id_button.place(x=95, y=170)

        # choosing the number of watchers in the following game
        label_watcher = Label(self.master, text="Choose how many watchers can play next game (default 5)", bg='Black',
                              fg='White')
        label_watcher.pack()
        label_watcher.place(x=5, y=230)

        self.watcher_numb = Entry(self.master, bd=1)  # here the number of watchers
        self.watcher_numb.pack()
        self.watcher_numb.place(x=55, y=255)
        self.watcher_numb.bind('<KeyPress>', self.enter_press_log_watcher)

        self.watcher_button = Button(self.master, text="Enter", command=self.choose_watcher_num)
        self.watcher_button.pack()
        self.watcher_button.place(x=95, y=280)

        self.label_watcher_error = Label(self.master, text="", bg='Black', fg='White')

        # start game button - opens the server for a new game
        self.start_button = Button(self.master, text="Start a new game", bg='Black', fg='Green',
                                   command=lambda: self.master.destroy())
        self.start_button.pack()
        self.start_button.place(x=5, y=350)

        # delete button - empties database
        self.delete_button = Button(self.master, text="Empty database", bg='Black', fg='Orange',
                                    command=self.delete_all_games)
        self.delete_button.place(x=5, y=400)

        # power off button - turns off the server
        self.close_server = Button(self.master, text="Power off", bg='Black', fg='Red', command=lambda: exit())
        self.close_server.pack()
        self.close_server.place(x=5, y=450)

        self.master.mainloop()

    def enter_press_log_watcher(self, event):  # makes it so you can use enter instead of having to press the button
        """
        when the enter key is pressed calls the choose_watcher_num() function with the number of watchers entered
        :param event:
        """
        if event.keycode == 13:
            self.choose_watcher_num()

    def choose_watcher_num(self):
        """"
        takes care of making the number of watchers allowed in the next game what the manager chose
        """
        global watcher_number
        # noinspection PyBroadException
        try:
            if 10 > int(self.watcher_numb.get()) > 0:  # if the num is between 1-9
                self.label_watcher_error.destroy()
                watcher_number = self.watcher_numb.get()
                print('watcher number is now ' + self.watcher_numb.get())
            else:
                print('invalid size')
                self.label_watcher_error.destroy()
                self.label_watcher_error = Label(self.master, text="watcher number must be between 1 and 9", bg='Black',
                                                 fg='red')
                self.label_watcher_error.pack()
                self.label_watcher_error.place(x=25, y=310)
        except Exception:
            print('invalid type not int')
            self.label_watcher_error.destroy()
            self.label_watcher_error = Label(self.master, text="watcher number must be an int type", bg='Black',
                                             fg='red')
            self.label_watcher_error.pack()
            self.label_watcher_error.place(x=25, y=310)

    def insert_game(self, id_of_game):
        """
        shows the game (number: id_of_game) and inserts its Id into the display entry
        :param id_of_game:
        """
        self.show_game(id_of_game)
        self.game_number.delete(0, 'end')
        self.game_number.insert(0, id_of_game)

    def show_game(self, game_id):  # takes care of showing the chosen game
        """
        takes care of showing the chosen game
        draws the painting of the game
        adds all of the game's guesses to the guesses menu bar
        and shows the name of the game
        :param game_id:
        """

        # resetting the screen
        self.action_label.destroy()
        self.painting_name.destroy()
        self.w['bg'] = 'White'
        self.w.delete(ALL)

        # Getting all of the chosen game's information from the database
        conn_1 = sqlite3.connect('scribble_database.db')
        cur_1 = conn_1.cursor()
        cur_1.execute("SELECT * FROM paintings")

        rows_1 = cur_1.fetchall()

        game_name = ''  # the word the users have to guess in the game
        painting = ''  # all of the painting information that is needed to redraw it
        guesses = ''  # all of the users guesses
        correct_game_id = False  # checks if the game id is correct , if its in the database
        shown_game_id = True  # checks if the game was already shown before

        # column (0) is 'ID' column (1) is 'painting_name' column (2) is 'painting' and column (3) is 'guesses'
        for row_1 in rows_1:
            if str(row_1[0]) == str(game_id):
                game_name = str(row_1[1])
                painting = str(row_1[2])
                guesses = str(row_1[3])
                correct_game_id = True

        if correct_game_id:  # if the game id is in the database
            print(painting)
            print(game_name)
            print(guesses)

            if game_id not in self.shown_games_list:
                shown_game_id = False  # the game was not shown before
                self.shown_games_list.append(game_id)

            self.action_label.destroy()

            painting_list = painting.split(';')  # 'Coordinates:' or 'Pen:' or 'Background:' or 'stop' (ignores 'stop')

            # Draws the painting
            for act in painting_list:
                print(act)

                if act.startswith('Coordinates:'):  # paints the coordinates
                    draw = act[12:]
                    draw_list = draw.split(' ')
                    x = draw_list[0]
                    y = draw_list[1]
                    pen_width = draw_list[2]  # pen_width is the pen width
                    reset = draw_list[3]
                    if reset == '0':  # meaning the mouse has not reset
                        self.w.create_line(self.old_x, self.old_y,
                                           x, y, fill=self.pen_color, width=pen_width, capstyle=ROUND, smooth=True)
                    if reset == '1':  # meaning the mouse has reset
                        self.w.create_line(x, y, str(int(x) - 0.00001), str(int(y) - 0.00001),
                                           fill=self.pen_color, width=pen_width, capstyle=ROUND, smooth=True)
                    self.old_x = x
                    self.old_y = y

                if act.startswith('Pen:'):  # changes the pen color
                    self.pen_color = act[4:]
                    print('pen color changed to' + self.pen_color)

                if act.startswith('Background:'):  # changes background color
                    self.background_color = act[11:]
                    self.w['bg'] = self.background_color
                    print('background changed to' + self.background_color)

            # resets the colors
            self.pen_color = 'Black'
            self.background_color = 'White'

            # puts the painting's name on the screen
            self.painting_name = Message(self.master, text=game_name, bg='Black', fg='White', anchor='se', font=20,
                                         width=300)
            self.painting_name.pack()
            self.painting_name.place(x=500, y=440)

            # shows the guesses by each user and at what time since the start of the game they were made
            if not shown_game_id:  # if it was already shown that means the guesses are already at the guesses menu bar

                guess_menu = Menu(self.guess_menu, tearoff=1)

                guesses_list = guesses.split(';')
                for guess in guesses_list:  # puts all guesses in guess menu
                    guess_menu.add_command(label=str(guess), command=lambda: print('working'))  # shows guesses

                self.guess_menu.add_cascade(label='Guesses for the word "' + game_name + '" Game ID: ' + game_id,
                                            menu=guess_menu)
                self.master.config(menu=self.menu_bar)

        else:  # invalid game id (not found in the database)
            print('invalid game ID')
            self.action_label.destroy()
            self.action_label = Message(self.master, text='Error: Invalid game ID', bg='Black', fg='Red',
                                        font=20, width=330)
            self.action_label.pack()
            self.action_label.place(x=500, y=440)

    def enter_press_log_show(self, event):  # makes it so you can use enter instead of having to press the button
        """
        when the enter key is pressed calls the show_game function with the game id entered
        :param event:
        """
        if event.keycode == 13:
            self.show_game(self.game_number.get())

    def enter_press_log_delete(self, event):  # makes it so you can use enter instead of having to press the button
        """
        when enter is pressed calls the delete_a_game function with the game id entered
        :param event:
        """
        if event.keycode == 13:
            self.delete_a_game(self.delete_id.get())

    def delete_all_games(self):
        """
        Delete all rows in the sql database table
        and deletes all guesses/available game ids from their menus
        conn: Connection to the SQLite database
        """

        # Deletes all rows from the database table
        conn_2 = sqlite3.connect('scribble_database.db')
        sql_2 = 'DELETE FROM paintings'
        cur_2 = conn_2.cursor()
        cur_2.execute(sql_2)
        conn_2.commit()

        # clears screen
        self.action_label.destroy()
        self.painting_name.destroy()
        self.w['bg'] = 'White'
        self.w.delete(ALL)

        # clears all guesses/available game ids from their menus
        self.menu_bar.destroy()
        self.action_label = Message(self.master, text='Database emptied', bg='Black', fg='orange', font=20,
                                    width=330)
        self.action_label.pack()
        self.action_label.place(x=500, y=440)
        self.menu_bar = Menu(self.master)
        self.guess_menu = Menu(self.menu_bar)
        self.file_menu = Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label="Available game IDs: ", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Guesses of displayed games: ", menu=self.guess_menu)
        self.master.config(menu=self.menu_bar)

    def delete_a_game(self, id_delete):
        """
        Delete a row in the sql database table
        and remakes the menus without the deleted game id/guesses
        conn: Connection to the SQLite database
        """

        # deletes a row from the sql database table
        conn_3 = sqlite3.connect('scribble_database.db')
        sql_3 = ('DELETE FROM paintings WHERE ID = ' + "'" + id_delete + "'")
        cur_3 = conn_3.cursor()
        cur_3.execute(sql_3)
        conn_3.commit()
        print('deleting game number: ' + id_delete)

        cur_3 = conn_3.cursor()
        cur_3.execute("SELECT * FROM paintings")
        rows_3 = cur_3.fetchall()  # rows_3 holds all of the database table rows in it

        # noinspection PyBroadException
        try:  # if the id was shown before
            self.shown_games_list.remove(id_delete)
            print('deleted the game id ' + id_delete + ' from the shown game list')

        except Exception:  # if the id was not shown yet
            print('Id not shown yet')

        # remakes the menus without the deleted game id/guesses
        self.menu_bar.destroy()
        self.menu_bar = Menu(self.master)
        self.guess_menu = Menu(self.menu_bar)
        self.file_menu = Menu(self.menu_bar, tearoff=1)

        for row_3 in rows_3:  # for each row in the database table - remakes the shown game ids menu without deleted id
            self.file_menu.add_command(label=str(row_3[0]),
                                       command=partial(self.insert_game, str(row_3[0])))  # shows available game ids
            print(str(row_3[0]))  # row_3[0] holds the game id

        self.menu_bar.add_cascade(label="Available game IDs: ", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Guesses of displayed games: ", menu=self.guess_menu)

        self.master.config(menu=self.menu_bar)

        print(self.shown_games_list)
        for restore_game_id in self.shown_games_list:  # remakes the guesses menu without the deleted game guesses
            if restore_game_id == id_delete:
                print('Id must not be restored because it was deleted')
            else:
                self.reset_game_guesses_menu(restore_game_id)
            print(restore_game_id)

    def reset_game_guesses_menu(self, game_id_renew):
        """
        remakes each cascade in the shown game guesses menu
        puts all of the game_id_renew guesses in said cascade
        :param game_id_renew:
        """
        conn_4 = sqlite3.connect('scribble_database.db')
        cur_4 = conn_4.cursor()
        cur_4.execute("SELECT * FROM paintings")

        rows_4 = cur_4.fetchall()  # rows_4 holds all of the database table rows in it

        guesses_1 = ''
        game_name_1 = ''

        for row_4 in rows_4:  # runs on the database table to find the specific game who's id is game_id_renew
            if str(row_4[0]) == str(game_id_renew):
                game_name_1 = str(row_4[1])  # the name of the game who's id is game_id_renew
                guesses_1 = str(row_4[3])  # the guesses of the game who's id is game_id_renew

        guess_menu = Menu(self.guess_menu, tearoff=1)

        guesses_list_1 = guesses_1.split(';')
        for guess_1 in guesses_list_1:  # goes over every guess of the game and puts it in the menu
            guess_menu.add_command(label=str(guess_1), command=lambda: print('working'))  # shows guesses

        self.guess_menu.add_cascade(label='Guesses for the word "' + game_name_1 + '" Game ID: ' + game_id_renew,
                                    menu=guess_menu)
        self.master.config(menu=self.menu_bar)


"""
Main
"""
global watcher_number  # holds the max number of watchers allowed to play in the game

while True:

    watcher_number = '5'  # by default 5 watchers can play
    print("default number of watchers " + watcher_number)
    Manager()
    print('Opened server for a new game')

    # Setting up sockets

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Af_inet - ipv4 ,sock_stream - tcp , sock_dgram - udp
    s.bind(('127.0.0.1', 5001))  # which ip and port the server will run from
    s.listen(100)  # queue of 100 (up to 100 clients can wait in line to connect to the server)

    PaintServer()

    s.close()

    print('server reset successful')
