import sys
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QGraphicsItem, QWidget, \
    QMenuBar, QDialog
from PySide2.QtGui import QColor, QPolygonF, QLinearGradient, QFont
from PySide2.QtCore import QPointF, QRectF, Qt, SIGNAL, QObject, QEventLoop, QTimer, QThreadPool, QRunnable
import random
import pickle
from xml.dom import minidom

import socket
import sys
from _thread import *



class Server(QRunnable) :  # Server for playing online
    server_running = False
    server = "127.0.0.1"  # localhost
    port = 5555

    def __init__(self) :
        super(Server, self).__init__( )
        Server.server_running = True
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.list_of_requests = []
        self.connected = set( )
        self.idCount = 0

        self.turn = 0
        self.first_turn = 0

        self.new_game = [True, True]

        self.playground_size = 3
        self.game = [Playground(self.playground_size), Playground(self.playground_size)]

        self.starting_position = [
            {"id" : [], "num" : [], "centerx" : [], "centery" : [], "x" : [], "y" : [], "map_size" : []} for _ in
            range(2)]

        self.moves_history = [[], []]
        self.random_elements = [[], []]

        self.game_history = [self.first_turn, self.starting_position, self.moves_history, self.random_elements]

        self.player_moved = [False, False]

        self.is_server = True

        self.xmlhandler = XMLhandler()

    @QtCore.Slot( )
    def run(self) :
        self.start_server( )
        if self.is_server :
            self.server_loop( )

    @QtCore.Slot( )
    def start_server(self) :
        try :
            self.s.bind((Server.server, Server.port))
        except socket.error as e :
            str(e)

        try :
            self.s.listen(2)
            #print("Waiting for a connection, Server Started")
        except OSError :
            self.is_server = False

    @QtCore.Slot( )
    def send_playground(self, conn, p) :
        attr = {"id" : [], "num" : [], "center" : [], "x" : [], "y" : [], "map_size" : [], "score" : 0}
        if self.new_game[p] :
            for element in self.game[p].elements :
                self.starting_position[p]["id"].append(element.id)
                self.starting_position[p]["num"].append(element.num)
                self.starting_position[p]["centerx"].append(element.center[0])
                self.starting_position[p]["centery"].append(element.center[1])
                self.starting_position[p]["x"].append(element.x)
                self.starting_position[p]["y"].append(element.y)
                self.starting_position[p]["map_size"].append(element.map_size)
            self.new_game[p] = False
        for element in self.game[p].elements :
            attr["id"].append(element.id)
            attr["num"].append(element.num)
            attr["center"].append(element.center)
            attr["x"].append(element.x)
            attr["y"].append(element.y)
            attr["map_size"].append(element.map_size)
        attr['score'] = self.game[p].score
        block = pickle.dumps(attr)
        conn.sendall(block)

    @QtCore.Slot( )
    def threaded_client(self, conn, p, gameId) :
        conn.send(str.encode(str(p)))
        reply = ""

        while Server.server_running :
            self.list_of_requests.append(p)
            if len(self.list_of_requests) > 100 :
                if all(elem == p for elem in self.list_of_requests) :
                    Server.server_running = False
                self.list_of_requests = []
            data = conn.recv(4096).decode( )
            if data == "get" :
                self.send_playground(conn, p)
            elif data == "getturn" :
                conn.send(str.encode(str(self.turn)))
            elif data == "online" :
                self.send_playground(conn, not p)
            elif data[:-1] == "restart" :
                self.new_game = [True, True]
                playground_size = int(data[-1])
                self.game = [Playground(playground_size), Playground(playground_size)]
                conn.send(str.encode(str(self.turn)))
            elif data == "getoponentmove" :
                conn.send(str.encode(str(self.moves_history[not p][-1])))
            elif data[:4] == "save" :
                save_path_file = data[4 :]
                self.xmlhandler.define_data(self.first_turn, self.starting_position, self.moves_history, self.random_elements)
                self.xmlhandler.save(True, 2, save_path_file)
                conn.send(str.encode("saved"))
            elif data[:4] == "load" :
                num_of_players, player1_starts, self.starting_position, self.moves_history, self.random_elements, self.score_history = self.xmlhandler.load(data[4:], True)

                empty_elements = [set({}), set({})]
                for i in range(num_of_players) :
                    for j, num in enumerate(self.starting_position[i]["num"]) :
                        if num == 0 :
                            empty_elements[i].add(j)

                self.game[0] = Playground(int(self.starting_position[0]["map_size"][0]))
                self.game[0].empty_elements = empty_elements[0]
                center = (int(self.starting_position[0]["centerx"][0]), int(self.starting_position[0]["centery"][0]))
                map_size = int(self.starting_position[0]["map_size"][0])
                for i, element in enumerate(self.game[0].elements) :
                    element.id = self.starting_position[0]["id"][i]
                    element.num = self.starting_position[0]["num"][i]
                    element.center = center
                    element.x = self.starting_position[0]["x"][i]
                    element.y = self.starting_position[0]["y"][i]
                    element.map_size = map_size

                for i in range(len(self.moves_history[0])) :
                    self.game[0].move(int(self.moves_history[0][i]), int(self.random_elements[0][i]))

                self.game[1] = Playground(int(self.starting_position[1]["map_size"][0]))
                self.game[1].empty_elements = empty_elements[1]
                center = (int(self.starting_position[1]["centerx"][0]), int(self.starting_position[1]["centery"][0]))
                map_size = int(self.starting_position[1]["map_size"][0])
                for i, element in enumerate(self.game[1].elements) :
                    element.id = int(self.starting_position[1]["id"][i])
                    element.num = int(self.starting_position[1]["num"][i])
                    element.center = center
                    element.x = int(self.starting_position[1]["x"][i])
                    element.y = int(self.starting_position[1]["y"][i])
                    element.map_size = int(map_size)

                for i, move in enumerate(self.moves_history[1]) :
                    self.game[1].move(int(move), int(self.random_elements[1][i]))

                conn.send(str.encode(str(player1_starts)))

            elif data :
                self.game[p].move(int(data))
                self.moves_history[p].append(int(data))
                self.random_elements[p].append(self.game[p].random_element)
                self.player_moved[p] = True
                self.send_playground(conn, p)
                if self.turn == p :
                    self.turn = int(not self.turn)

        self.idCount -= 1
        conn.close( )

    @QtCore.Slot( )
    def server_loop(self) :
        while Server.server_running :
            conn, addr = self.s.accept( )

            self.idCount += 1
            p = 0
            gameId = (self.idCount - 1) // 2
            if self.idCount % 2 == 1 :
                pass
            else :
                p = 1

            start_new_thread(self.threaded_client, (conn, p, gameId))


class Network :  # communication functions
    def __init__(self) :
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = Server.server
        self.port = Server.port
        self.addr = (self.server, self.port)
        self.p = self.connect( )

    def getP(self) :
        return self.p

    def connect(self) :
        try :
            self.client.connect(self.addr)
            return self.client.recv(2048).decode( )
        except :
            pass

    def send_string(self, data) :
        try :
            self.client.send(str.encode(data))
            return self.client.recv(2048).decode( )
        except socket.error as e :
            pass
            #print(e)

    def send(self, data) :
        try :
            self.client.send(str.encode(data))
            return pickle.loads(self.client.recv(2048 * 16))
        except socket.error as e :
            pass
            #print(e)


class Dialog_Save_Load(QDialog) :  # Dialog window for saving and loading files
    def __init__(self, mainWindow, parent=None) :
        super(Dialog_Save_Load, self).__init__(parent)

        self.mainWindow = mainWindow

        self.setWindowTitle("Options")

        self.resize(498, 314)
        self.textEdit = QtWidgets.QTextEdit(self)
        self.textEdit.setGeometry(QtCore.QRect(30, 110, 431, 31))
        self.textEdit.setObjectName("textEdit")
        font = QtGui.QFont( )
        font.setPointSize(10)
        self.textEdit.setFont(font)
        self.label = QtWidgets.QLabel(self)
        self.label.setGeometry(QtCore.QRect(100, 70, 47, 13))
        self.label.setText("")
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self)
        self.label_2.setGeometry(QtCore.QRect(120, 70, 231, 21))
        font = QtGui.QFont( )
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.pushButton = QtWidgets.QPushButton(self)
        self.pushButton.setGeometry(QtCore.QRect(170, 200, 131, 51))
        self.pushButton.setObjectName("pushButton")
        self.label_3 = QtWidgets.QLabel(self)
        self.label_3.setGeometry(QtCore.QRect(200, 270, 281, 20))
        font = QtGui.QFont( )
        font.setPointSize(10)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.checkBox = QtWidgets.QCheckBox(self)
        self.checkBox.setGeometry(QtCore.QRect(190, 150, 91, 41))
        font = QtGui.QFont( )
        font.setPointSize(9)
        self.checkBox.setFont(font)
        self.checkBox.setObjectName("checkBox")

        self.path = "history.xml"

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

        QObject.connect(self.pushButton, SIGNAL('clicked()'), self.handle_path)

    def retranslateUi(self, Dialog_Save_Load) :
        _translate = QtCore.QCoreApplication.translate
        Dialog_Save_Load.setWindowTitle(_translate("Dialog_Save_Load", "Dialog_Save_Load"))
        self.label_2.setText(_translate("Dialog_Save_Load", "Enter the path to the .xml file :"))
        self.pushButton.setText(_translate("Dialog_Save_Load", "OK"))
        self.textEdit.setText(_translate("Dialog_Save_Load", "history.xml"))
        self.label_3.setText(_translate("Dialog_Save_Load",
                                        "<html><head/><body><p><span style=\" color:#ff0000;\">Error</span></p></body></html>"))
        self.checkBox.setText(_translate("Dialog_Save_Load", "Animation"))
        self.label_3.setVisible(False)
        if self.mainWindow.saving == True or Server.server_running :
            self.checkBox.setVisible(False)

    def handle_path(self) :
        path = self.textEdit.toPlainText( )
        if path[-4 :] == ".xml" :
            if self.mainWindow.loading :
                try :
                    with open(path, 'r') as file :
                        pass

                    if self.checkBox.isChecked( ) :
                        self.mainWindow.animate = True
                    else :
                        self.mainWindow.animate = False
                    self.mainWindow.load_game(path)
                    self.label_3.setVisible(True)
                    self.label_3.setText('File loaded')

                except FileNotFoundError :
                    self.label_3.setVisible(True)
                    self.label_3.setText(
                        '"<html><head/><body><p><span style=\" color:#ff0000;\">File doesn\'t exist</span></p></body></html>"')

            elif self.mainWindow.saving :
                self.mainWindow.save_game(path)
                self.label_3.setVisible(True)
                self.label_3.setText('File saved')


class Dialog(QDialog) :  # Dialog window after clicking on "options" in the menu
    def __init__(self, mainWindow, parent=None) :
        super(Dialog, self).__init__(parent)

        self.mainWindow = mainWindow

        self.setWindowTitle("Options")

        self.resize(400, 300)
        self.ipAddress = QtWidgets.QLabel(self)
        self.ipAddress.setGeometry(QtCore.QRect(40, 120, 91, 16))
        font = QtGui.QFont( )
        font.setPointSize(10)
        self.ipAddress.setFont(font)
        self.ipAddress.setObjectName("ipAddress")
        self.mapSizeLabel = QtWidgets.QLabel(self)
        self.mapSizeLabel.setGeometry(QtCore.QRect(40, 60, 71, 21))
        font = QtGui.QFont( )
        font.setPointSize(10)
        self.mapSizeLabel.setFont(font)
        self.mapSizeLabel.setObjectName("mapSizeLabel")
        self.listeningPort = QtWidgets.QLabel(self)
        self.listeningPort.setGeometry(QtCore.QRect(40, 170, 111, 21))
        font = QtGui.QFont( )
        font.setPointSize(10)
        self.listeningPort.setFont(font)
        self.listeningPort.setObjectName("listeningPort")
        self.ipTextEdit = QtWidgets.QTextEdit(self)
        self.ipTextEdit.setGeometry(QtCore.QRect(240, 110, 104, 31))
        self.ipTextEdit.setObjectName("ipTextEdit")
        self.portTextEdit_3 = QtWidgets.QTextEdit(self)
        self.portTextEdit_3.setGeometry(QtCore.QRect(240, 160, 104, 31))
        self.portTextEdit_3.setObjectName("portTextEdit_3")
        self.saveButton = QtWidgets.QPushButton(self)
        self.saveButton.setGeometry(QtCore.QRect(80, 230, 93, 28))
        self.saveButton.setObjectName("saveButton")
        self.mapSpinBox = QtWidgets.QSpinBox(self)
        self.mapSpinBox.setGeometry(QtCore.QRect(240, 60, 42, 22))
        self.mapSpinBox.setObjectName("mapSpinBox")
        self.mapSpinBox.setRange(3, 6)
        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

        self.ipTextEdit.setText(Server.server)
        self.portTextEdit_3.setText(str(Server.port))

        QObject.connect(self.saveButton, SIGNAL('clicked()'), self.setMapSize)
        QObject.connect(self.saveButton, SIGNAL('clicked()'), self.setServer)

    def retranslateUi(self, Dialog) :
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.ipAddress.setText(_translate("Dialog", "(Server) IP Address:"))
        self.mapSizeLabel.setText(_translate("Dialog", "Map size:"))
        self.listeningPort.setText(_translate("Dialog", "(Server) Listening port:"))
        self.saveButton.setText(_translate("Dialog", "Save"))

    def setMapSize(self) :
        self.mainWindow.playground_size = int(self.mapSpinBox.text( ))
        self.mainWindow.new_game( )

    def setServer(self) :
        Server.server = self.ipTextEdit.toPlainText( )
        Server.port = int(self.portTextEdit_3.toPlainText( ))


class Playground :  # the main class of the game, containing all the elements on the board
    def __init__(self, size) :
        self.size = size
        self.center = (260, 245)
        self.reserved_locations = {self.center}

        self.generative_locations = {self.center}
        self.neighbours_distance = [(-40, -80), (40, -80), (-80, 0), (80, 0), (-40, 80), (40, 80)]
        self.neighbours = []
        self.elements = []
        self.empty_elements = set( )
        self.num_of_elem = 2
        self.num_of_spawn_elem = 1
        self.score = 0
        self.random_element = 0

        Node.static_counter = 0
        self.__generate_locations( )
        self.__create_elements( )

    def __generate_locations(self) :  # generating locations of all elements on the board
        new_reserved_locations = [{self.center}]
        for _ in range(self.size - 1) :
            new_reserved_locations.append(set({}))
            for loc in new_reserved_locations[-2] :
                for n in self.neighbours_distance :
                    neighbour_loc = tuple(map(lambda i, j : i + j, loc, n))
                    new_reserved_locations[-1].add(neighbour_loc)

            self.reserved_locations = self.reserved_locations.union(new_reserved_locations[-1])

    def __create_elements(self) :  # creating self.num_of_elem elements on the board
        self.reserved_locations.remove(self.center)
        elements_with_points = random.sample(self.reserved_locations, self.num_of_elem)
        for i, loc in enumerate(self.reserved_locations) :
            if loc in elements_with_points :
                self.elements.append(Node(self.center, *loc, 2, self.size))
            else :
                self.empty_elements.add(i)
                self.elements.append(Node(self.center, *loc, 0, self.size))

        list_reserved_locations = list(self.reserved_locations)

        for l, loc in enumerate(self.reserved_locations) :
            self.neighbours.append([None for _ in self.neighbours_distance])
            for k, n in enumerate(self.neighbours_distance) :
                neighbour_loc = tuple(map(lambda i, j : i + j, loc, n))
                if neighbour_loc in self.reserved_locations :
                    self.neighbours[-1][k] = list_reserved_locations.index(neighbour_loc)
            self.elements[l].define_neighbours(neighbours=self.neighbours[-1])

    def get_neighbours_chain(self, element_id,
                             direction) :  # getting id of elements in given direction in regard to given element
        id = element_id
        neighbours_chain = []
        while self.elements[id].neighbours[direction] is not None :
            neighbours_chain.append(self.elements[id].neighbours[direction])
            id = self.elements[id].neighbours[direction]

        return neighbours_chain

    def summon_new_element(self, desired_new_element) :  # new random element after move
        try :
            if desired_new_element is None :
                for _ in range(self.num_of_spawn_elem) :
                    list_empty_elements = list(self.empty_elements)
                    self.random_element = random.choice(list_empty_elements)
                    self.empty_elements.remove(self.random_element)
                    self.elements[self.random_element].update_element(2)
            else :
                self.empty_elements.remove(desired_new_element)
                self.elements[desired_new_element].update_element(2)

        except IndexError :
            pass
            #print("Can't move")

    def refresh_elements(self) :
        for element in self.elements :
            element.just_updated = False

    def move(self, direction, desired_new_element=None) :  # direction => 0 - UL , 1 - UR, 2 - L, 3 - R, 4 - DL, 5 - DR
        active_elements = set({})
        for i, element in enumerate(self.elements) :
            if element.num > 0 :
                active_elements.add(i)
        for _ in range(6) :
            for i, element in enumerate(self.elements) :
                if element.num > 0 :
                    try :
                        neighbours_ahead = self.get_neighbours_chain(i, direction)
                        if self.elements[neighbours_ahead[0]].num == 0 :
                            self.elements[neighbours_ahead[0]].update_element(element.num)
                            element.num = 0
                            self.empty_elements.remove(element.neighbours[direction])
                            active_elements.add(element.neighbours[direction])
                            self.empty_elements.add(i)
                            active_elements.remove(i)
                        elif self.elements[neighbours_ahead[0]].num == element.num :
                            if len(neighbours_ahead) == 1 :
                                if not self.elements[neighbours_ahead[0]].just_updated and not element.just_updated :
                                    self.elements[neighbours_ahead[0]].update_element(element.num * 2)
                                    self.score += element.num * 2
                                    element.num = 0
                                    self.empty_elements.add(i)
                                    active_elements.remove(i)
                                else :
                                    if element in active_elements :
                                        active_elements.remove(element)
                            if len(neighbours_ahead) > 1 :
                                if self.elements[neighbours_ahead[1]].num != self.elements[neighbours_ahead[0]].num \
                                        and not self.elements[
                                    neighbours_ahead[0]].just_updated and not element.just_updated :
                                    self.elements[neighbours_ahead[0]].update_element(element.num * 2)
                                    self.score += element.num * 2
                                    element.num = 0
                                    self.empty_elements.add(i)
                                    active_elements.remove(i)
                                    active_elements.add(neighbours_ahead[0])
                        elif self.elements[neighbours_ahead[0]].num != element.num :
                            if element in active_elements :
                                active_elements.remove(element)
                    except (TypeError, IndexError) as e :
                        if element in active_elements :
                            active_elements.remove(element)
                    except ValueError :
                        pass

        self.summon_new_element(desired_new_element)
        self.refresh_elements( )


class Node(QGraphicsItem) :  # class for generating an element
    static_counter = 0

    def __init__(self, center=None, x=None, y=None, num=None, map_size=None, id=None, parent=None) :
        QGraphicsItem.__init__(self, parent)
        self.id = Node.static_counter if id is None else id
        Node.static_counter += 1
        self.num = num
        self.center = center
        self.x, self.y = x, y
        self.width, self.height = 50, 50
        self.map_size = map_size
        self.scale = 0.8 ** (self.map_size - 3)
        self.neighbours = None
        self.just_updated = False

    def boundingRect(self) :
        if self.map_size == 3 :
            return QRectF(50, 40, 500, 500)
        elif self.map_size == 4 :
            return QRectF(0, -10, 500, 500)
        elif self.map_size == 5 :
            return QRectF(-50, -60, 500, 500)
        elif self.map_size == 6 :
            return QRectF(-95, -100, 500, 500)

    def paint(self, painter, option, widget) :
        cx = self.x
        cy = self.y
        scale = self.scale
        points = [QPointF(cx * scale, (cy + 30) * scale), QPointF((cx + 40) * scale, cy * scale),
                  QPointF((cx + 80) * scale, (cy + 30) * scale), QPointF((cx + 80) * scale, (cy + 80) * scale),
                  QPointF((cx + 40) * scale, (cy + 110) * scale), QPointF(cx * scale, (cy + 80) * scale)]

        grad = QLinearGradient(0, 0, 0, 0)

        if self.num == 2 :
            color1 = QColor(238, 228, 218)
        elif self.num == 4 :
            color1 = QColor(237, 224, 200)
        elif self.num == 8 :
            color1 = QColor(242, 177, 121)
        elif self.num == 16 :
            color1 = QColor(245, 149, 99)
        elif self.num == 32 :
            color1 = QColor(246, 124, 95)
        elif self.num == 64 :
            color1 = QColor(246, 94, 59)
        elif self.num == 128 :
            color1 = QColor(237, 207, 114)
        elif self.num == 256 :
            color1 = QColor(237, 204, 114)
        elif self.num == 512 :
            color1 = QColor(239, 198, 80)
        elif self.num == 1024 :
            color1 = QColor(237, 197, 64)
        elif self.num == 2048 :
            color1 = QColor(238, 193, 46)
        else :
            color1 = QColor(205, 193, 180)

        if (self.x, self.y) == self.center :
            color1 = QColor(110, 110, 110)

        grad.setColorAt(0, color1)
        painter.setBrush(grad)
        painter.drawPolygon(QPolygonF.fromList(points))

        if self.num :
            sansFont = QFont("Decorative", 12 * self.scale + 2, QFont.Bold)
            painter.setPen(QColor(80, 80, 80))
            painter.setFont(sansFont)
            pad = 33
            if 1 <= self.num / 10 < 10 :
                pad -= 4
            elif 1 <= self.num / 100 < 10 :
                pad -= 10
            elif 1 <= self.num / 1000 < 10 :
                pad -= 27

            painter.drawText(QPointF((cx + pad) * scale, (cy + 60) * scale), str(self.num))

    def define_neighbours(self, neighbours) :
        self.neighbours = neighbours

    def update_element(self, num) :
        if self.num != 0 and num != 0 :
            self.just_updated = True
        self.num = num
        self.update( )

class Ui_MainWindow(object) :
    def setupUi(self, MainWindow) :
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1558, 737)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.graphicsView1 = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView1.setGeometry(QtCore.QRect(280, 80, 600, 600))
        self.graphicsView1.setObjectName("graphicsView1")
        self.graphicsView2 = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView2.setGeometry(QtCore.QRect(920, 80, 600, 600))
        self.graphicsView2.setObjectName("graphicsView2")
        self.Player1 = QtWidgets.QLabel(self.centralwidget)
        self.Player1.setGeometry(QtCore.QRect(280, 30, 111, 41))
        font = QtGui.QFont( )
        font.setPointSize(18)
        self.Player1.setFont(font)
        self.Player1.setObjectName("Player1")
        self.Turn1 = QtWidgets.QLabel(self.centralwidget)
        self.Turn1.setGeometry(QtCore.QRect(430, 30, 111, 41))
        font = QtGui.QFont( )
        font.setPointSize(10)
        self.Turn1.setFont(font)
        self.Turn1.setObjectName("Turn1")
        self.line = QtWidgets.QFrame(self.centralwidget)
        self.line.setGeometry(QtCore.QRect(890, 80, 20, 591))
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.Player2 = QtWidgets.QLabel(self.centralwidget)
        self.Player2.setGeometry(QtCore.QRect(920, 30, 111, 41))
        font = QtGui.QFont( )
        font.setPointSize(18)
        self.Player2.setFont(font)
        self.Player2.setObjectName("Player2")
        self.Turn2 = QtWidgets.QLabel(self.centralwidget)
        self.Turn2.setGeometry(QtCore.QRect(1070, 30, 111, 41))
        font = QtGui.QFont( )
        font.setPointSize(10)
        self.Turn2.setFont(font)
        self.Turn2.setObjectName("Turn1")
        self.Score1 = QtWidgets.QLabel(self.centralwidget)
        self.Score1.setGeometry(QtCore.QRect(640, 30, 111, 41))
        font = QtGui.QFont( )
        font.setPointSize(18)
        self.Score1.setFont(font)
        self.Score1.setObjectName("Score1")
        self.Score2 = QtWidgets.QLabel(self.centralwidget)
        self.Score2.setGeometry(QtCore.QRect(1270, 30, 111, 41))
        font = QtGui.QFont( )
        font.setPointSize(18)
        self.Score2.setFont(font)
        self.Score2.setObjectName("Score2")
        self.Score1_1 = QtWidgets.QLabel(self.centralwidget)
        self.Score1_1.setGeometry(QtCore.QRect(740, 30, 111, 41))
        font = QtGui.QFont( )
        font.setPointSize(18)
        self.Score1_1.setFont(font)
        self.Score1_1.setObjectName("score1_1")
        self.Score2_1 = QtWidgets.QLabel(self.centralwidget)
        self.Score2_1.setGeometry(QtCore.QRect(1370, 30, 111, 41))
        font = QtGui.QFont( )
        font.setPointSize(18)
        self.Score2_1.setFont(font)
        self.Score2_1.setObjectName("score2_1")
        self.UpLeftButton = QtWidgets.QPushButton(self.centralwidget)
        self.UpLeftButton.setGeometry(QtCore.QRect(40, 80, 93, 41))
        self.UpLeftButton.setObjectName("UpLeftButton")
        self.UpRightButton = QtWidgets.QPushButton(self.centralwidget)
        self.UpRightButton.setGeometry(QtCore.QRect(170, 80, 93, 41))
        self.UpRightButton.setObjectName("UpRightButton")
        self.LeftButton = QtWidgets.QPushButton(self.centralwidget)
        self.LeftButton.setGeometry(QtCore.QRect(40, 130, 93, 41))
        self.LeftButton.setObjectName("LeftButton")
        self.RightButton = QtWidgets.QPushButton(self.centralwidget)
        self.RightButton.setGeometry(QtCore.QRect(170, 130, 93, 41))
        self.RightButton.setObjectName("RightButton")
        self.DownLeftButton = QtWidgets.QPushButton(self.centralwidget)
        self.DownLeftButton.setGeometry(QtCore.QRect(40, 180, 93, 41))
        self.DownLeftButton.setObjectName("DownLeftButton")
        self.DownRightButton = QtWidgets.QPushButton(self.centralwidget)
        self.DownRightButton.setGeometry(QtCore.QRect(170, 180, 93, 41))
        self.DownRightButton.setObjectName("DownRightButton")
        self.new_gameButton = QtWidgets.QPushButton(self.centralwidget)
        self.new_gameButton.setGeometry(QtCore.QRect(40, 260, 221, 41))
        self.new_gameButton.setObjectName("new_gameButton")
        self.save_gameButton = QtWidgets.QPushButton(self.centralwidget)
        self.save_gameButton.setGeometry(QtCore.QRect(40, 310, 221, 41))
        self.save_gameButton.setObjectName("save_gameButton")
        self.load_gameButton = QtWidgets.QPushButton(self.centralwidget)
        self.load_gameButton.setGeometry(QtCore.QRect(40, 360, 221, 41))
        self.load_gameButton.setObjectName("load_gameButton")
        self.GameHistoryTextEdit = QtWidgets.QTextEdit(self.centralwidget)
        self.GameHistoryTextEdit.setGeometry(QtCore.QRect(40, 460, 221, 221))
        self.GameHistoryTextEdit.setObjectName("GameHistoryTextEdit")
        self.GameHistoryLabel = QtWidgets.QLabel(self.centralwidget)
        self.GameHistoryLabel.setEnabled(True)
        self.GameHistoryLabel.setGeometry(QtCore.QRect(110, 430, 121, 21))
        font = QtGui.QFont( )
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        self.GameHistoryLabel.setFont(font)
        self.GameHistoryLabel.setObjectName("GameHistoryLabel")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1558, 26))
        self.menubar.setObjectName("menubar")
        self.menuOptions = QtWidgets.QMenu(self.menubar)
        self.menuOptions.setObjectName("menuOptions")
        self.menuLAN_game = QtWidgets.QMenu(self.menubar)
        self.menuLAN_game.setObjectName("menuLAN_game")
        self.menuConnect_with_2nd_player = QtWidgets.QMenu(self.menubar)
        self.menuConnect_with_2nd_player.setObjectName("menuConnect_with_2nd_player")
        self.menuSingle_game = QtWidgets.QMenu(self.menubar)
        self.menuSingle_game.setObjectName("menuSingle_game")
        self.menuOffline_game = QtWidgets.QMenu(self.menubar)
        self.menuOffline_game.setObjectName("menuOffline_game")
        self.menuUndo1 = QtWidgets.QMenu(self.menubar)
        self.menuUndo1.setObjectName("menuUndo1")
        self.menuUndo2 = QtWidgets.QMenu(self.menubar)
        self.menuUndo2.setObjectName("menuUndo2")

        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menubar.addAction(self.menuOptions.menuAction( ))
        self.menubar.addAction(self.menuLAN_game.menuAction( ))
        self.menubar.addAction(self.menuConnect_with_2nd_player.menuAction( ))
        self.menubar.addAction(self.menuSingle_game.menuAction( ))
        self.menubar.addAction(self.menuOffline_game.menuAction( ))
        self.menubar.addAction(self.menuUndo1.menuAction( ))
        self.menubar.addAction(self.menuUndo2.menuAction( ))

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow) :
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("2048 Hex", "2048 Hex"))
        self.Player1.setText(_translate("2048 Hex", "Player 1"))
        self.Turn1.setText(_translate("2048 Hex", "Your turn"))
        self.Turn1.setVisible(False)
        self.Player2.setText(_translate("2048 Hex", "Player 2"))
        self.Turn2.setText(_translate("2048 Hex", "Your turn"))
        self.Turn2.setVisible(False)
        self.Score1.setText(_translate("2048 Hex", "Score:"))
        self.Score2.setText(_translate("2048 Hex", "Score:"))
        self.Score1_1.setText(_translate("2048 Hex", "0"))
        self.Score2_1.setText(_translate("2048 Hex", "0"))
        self.UpLeftButton.setText(_translate("2048 Hex", "Up Left"))
        self.UpRightButton.setText(_translate("2048 Hex", "Up Right"))
        self.LeftButton.setText(_translate("2048 Hex", "Left"))
        self.RightButton.setText(_translate("2048 Hex", "Right"))
        self.DownLeftButton.setText(_translate("2048 Hex", "Down Left"))
        self.DownRightButton.setText(_translate("2048 Hex", "Down Right"))
        self.new_gameButton.setText(_translate("2048 Hex", "New game"))
        self.save_gameButton.setText(_translate("2048 Hex", "Save Game"))
        self.load_gameButton.setText(_translate("2048 Hex", "Load Game"))
        self.GameHistoryLabel.setText(_translate("2048 Hex", "Game history"))
        self.menuOptions.setTitle(_translate("2048 Hex", "Options"))
        self.menuLAN_game.setTitle(_translate("2048 Hex", "LAN game"))
        self.menuConnect_with_2nd_player.setTitle(_translate("2048 Hex", "Connect with 2nd player"))
        self.menuSingle_game.setTitle(_translate("2048 Hex", "Offline singleplayer"))
        self.menuOffline_game.setTitle(_translate("2048 Hex", "Offline multiplayer"))
        self.menuUndo1.setTitle(_translate("2048 Hex", "Undo (Player1)"))
        self.menuUndo2.setTitle(_translate("2048 Hex", "Undo (Player2)"))

class MainWindow(QMainWindow,
                 Ui_MainWindow) :  # main class containing information about everything going on in the program
    def __init__(self, parent=None) :
        QMainWindow.__init__(self, parent=parent)

        self.setupUi(self)

        self.solo_game = True
        self.is_lan_game = False
        self.server_on = False
        self.is_connected = False
        self.playground_size = 3
        self.center = (260, 245)
        self.turn = 'A'
        self.first_turn = 'A'
        self.starting_position = [
            {"id" : [], "num" : [], "centerx" : [], "centery" : [], "x" : [], "y" : [], "map_size" : []} for _ in
            range(2)]
        self.moves_history = [[], []]
        self.score_history = [[], []]
        self.random_elements = [[], []]
        self.score = [0, 0]
        self.create_left_offline_scene( )

        self.saving = False
        self.loading = False

        QMenuBar.connect(self.menuOptions, SIGNAL('aboutToShow()'), self.show_dialog)
        QMenuBar.connect(self.menuLAN_game, SIGNAL('aboutToShow()'), self.lan_game)
        QMenuBar.connect(self.menuSingle_game, SIGNAL('aboutToShow()'), self.play_single)
        QMenuBar.connect(self.menuOffline_game, SIGNAL('aboutToShow()'), self.play_offline)
        QMenuBar.connect(self.menuConnect_with_2nd_player, SIGNAL('aboutToShow()'), self.connect_online)
        QMenuBar.connect(self.menuUndo1, SIGNAL('aboutToShow()'), lambda : self.undo_move(0))
        QMenuBar.connect(self.menuUndo2, SIGNAL('aboutToShow()'), lambda : self.undo_move(1))

        QObject.connect(self.new_gameButton, SIGNAL('clicked()'), self.new_game)
        QObject.connect(self.save_gameButton, SIGNAL('clicked()'), self.show_save_dialog)
        QObject.connect(self.load_gameButton, SIGNAL('clicked()'), self.show_load_dialog)

        QObject.connect(self.UpLeftButton, SIGNAL('clicked()'), lambda : self.move_instruction(0))
        QObject.connect(self.UpRightButton, SIGNAL('clicked()'), lambda : self.move_instruction(1))
        QObject.connect(self.LeftButton, SIGNAL('clicked()'), lambda : self.move_instruction(2))
        QObject.connect(self.RightButton, SIGNAL('clicked()'), lambda : self.move_instruction(3))
        QObject.connect(self.DownLeftButton, SIGNAL('clicked()'), lambda : self.move_instruction(4))
        QObject.connect(self.DownRightButton, SIGNAL('clicked()'), lambda : self.move_instruction(5))

        self.key_pressed = {"player1" : [0 for _ in range(4)], "player2" : [0 for _ in range(4)]}
        self.movement_keys = {"player1" : [Qt.Key_W, Qt.Key_S, Qt.Key_A, Qt.Key_D],
                              "player2" : [Qt.Key_I, Qt.Key_K, Qt.Key_J, Qt.Key_L]}
        self.in_turns = True

        self.animate = False
        self.animation_counter = [0, 0]
        self.animation_turn = 0
        self.timer = QTimer(self)
        self.xmlhandler = XMLhandler()

    def show_save_dialog(self) :
        self.loading = False
        self.saving = True
        dialog = Dialog_Save_Load(self)
        dialog.show( )
        dialog.exec_( )

    def show_load_dialog(self) :
        self.loading = True
        self.saving = False
        dialog = Dialog_Save_Load(self)
        dialog.show( )
        dialog.exec_( )

    def play_single(self) :
        self.Turn1.setText("")
        self.Turn2.setText("")
        Server.server_running = False
        self.solo_game = True
        self.is_lan_game = False
        self.is_connected = False
        self.Score1_1.setText("0")
        self.Score2_1.setText("0")
        self.GameHistoryTextEdit.clear( )
        self.turn = 'A'
        self.first_turn = 'A'
        self.__new_gameHistory( )
        try :
            self.scene_right.clear( )
        except :
            pass
        self.create_left_offline_scene( )

    def __new_gameHistory(self) :
        self.starting_position = [
            {"id" : [], "num" : [], "centerx" : [], "centery" : [], "x" : [], "y" : [], "map_size" : []} for _ in range(2)]
        self.moves_history = [[], []]
        self.score_history = [[], []]
        self.random_elements = [[], []]

    def undo_move(self, player_num) :
        try :
            ref_player = "player" + str(player_num + 1)

            self.key_pressed[ref_player] = list(map(lambda x : x * 0, self.key_pressed[ref_player]))
            empty_elements = set({})

            for j, num in enumerate(self.starting_position[player_num]["num"]) :
                if num == 0 :
                    empty_elements.add(j)

            ref_scene = QGraphicsScene( )
            ref_playground = Playground(int(self.starting_position[player_num]["map_size"][0]))
            ref_playground.empty_elements = empty_elements

            center = (
                int(self.starting_position[player_num]["centerx"][0]), int(self.starting_position[0]["centery"][0]))
            map_size = int(self.starting_position[player_num]["map_size"][0])

            for i, element in enumerate(ref_playground.elements) :
                element.id = int(self.starting_position[player_num]["id"][i])
                element.num = int(self.starting_position[player_num]["num"][i])
                element.center = center
                element.x = int(self.starting_position[player_num]["x"][i])
                element.y = int(self.starting_position[player_num]["y"][i])
                element.map_size = int(map_size)
                ref_scene.addItem(element)

            for i in range(len(self.moves_history[player_num]) - 1) :
                ref_playground.move(int(self.moves_history[player_num][i]), int(self.random_elements[player_num][i]))

            if player_num :
                self.scene_right = ref_scene
                self.playground_right = ref_playground
                self.scene_right.addItem(Node(center, *center, None, map_size))
                self.graphicsView2.setScene(self.scene_right)
            else :
                self.scene_left = ref_scene
                self.playground_left = ref_playground
                self.scene_left.addItem(Node(center, *center, None, map_size))
                self.graphicsView1.setScene(self.scene_left)

            self.key_pressed[ref_player] = list(map(lambda x : x * 0, self.key_pressed[ref_player]))

            try :
                self.moves_history[player_num].pop(-1)
                self.random_elements[player_num].pop(-1)
                self.score_history[player_num].pop(-1)
                if player_num :
                    self.Score2_1.setText(str(self.score_history[player_num][-1]))
                else :
                    self.Score1_1.setText(str(self.score_history[player_num][-1]))

            except IndexError :
                if player_num :
                    self.Score2_1.setText("0")
                else :
                    self.Score1_1.setText("0")
                #print(f"Player {player_num + 1}: This is starting position")
        except (AttributeError, IndexError) as e :
            pass
            #print("Info: You need to be in \"multiplayer\" mode to do this action")

    def save_game(self, path) :
        if self.is_lan_game :
            x = self.n.send_string("save" + path)
        else :
            self.xmlhandler.define_data(self.first_turn, self.starting_position, self.moves_history, self.random_elements, self.score_history)
            num_of_players = 1 if self.solo_game else 2
            self.xmlhandler.save(False, num_of_players, path)

    def load_game(self, path) :
        if self.is_lan_game :
            x = self.n.send_string("load" + path)
        else :

            num_of_players, player1_starts, self.starting_position, self.moves_history, self.random_elements, self.score_history = self.xmlhandler.load(
                path)

            empty_elements = [set({}), set({})]
            for i in range(num_of_players) :
                for j, num in enumerate(self.starting_position[i]["num"]) :
                    if num == 0 :
                        empty_elements[i].add(j)

            if num_of_players == 1 :
                try :
                    self.scene_right.clear( )
                except :
                    pass

            self.scene_left = QGraphicsScene( )
            self.playground_left = Playground(int(self.starting_position[0]["map_size"][0]))
            self.playground_left.empty_elements = empty_elements[0]
            center = (int(self.starting_position[0]["centerx"][0]), int(self.starting_position[0]["centery"][0]))
            map_size = int(self.starting_position[0]["map_size"][0])
            for i, element in enumerate(self.playground_left.elements) :
                element.id = self.starting_position[0]["id"][i]
                element.num = self.starting_position[0]["num"][i]
                element.center = center
                element.x = self.starting_position[0]["x"][i]
                element.y = self.starting_position[0]["y"][i]
                element.map_size = map_size
                self.scene_left.addItem(element)

            self.scene_left.addItem(Node(center, *center, None, map_size))
            self.graphicsView1.setScene(self.scene_left)

            if num_of_players == 1 :
                self.Turn1.setVisible(False)
                self.Turn2.setVisible(False)
                if not self.animate :
                    for i in range(len(self.moves_history[0])) :
                        self.playground_left.move(int(self.moves_history[0][i]), int(self.random_elements[0][i]))

                    try :
                        self.Score1_1.setText(str(self.score_history[0][-1]))
                    except IndexError :
                        self.Score1_1.setText(str("0"))
                else :
                    self.animation_counter = [0, 0]

                    def show_moves(timer) :
                        try :
                            self.playground_left.move(int(self.moves_history[0][self.animation_counter[0]]),
                                                      int(self.random_elements[0][self.animation_counter[0]]))
                            self.Score1_1.setText(str(self.score_history[0][self.animation_counter[0]]))
                        except IndexError :
                            timer.stop( )
                        self.animation_counter[0] += 1
                        if self.animation_counter[0] == len(self.moves_history[0]) :
                            timer.stop( )

                    self.timer = QTimer(self)
                    self.connect(self.timer, SIGNAL("timeout()"), lambda : show_moves(self.timer))
                    self.timer.start(1000)
            else :
                self.scene_right = QGraphicsScene( )
                self.playground_right = Playground(int(self.starting_position[1]["map_size"][0]))
                self.playground_right.empty_elements = empty_elements[1]
                center = (int(self.starting_position[1]["centerx"][0]), int(self.starting_position[1]["centery"][0]))
                map_size = int(self.starting_position[1]["map_size"][0])
                for i, element in enumerate(self.playground_right.elements) :
                    element.id = int(self.starting_position[1]["id"][i])
                    element.num = int(self.starting_position[1]["num"][i])
                    element.center = center
                    element.x = int(self.starting_position[1]["x"][i])
                    element.y = int(self.starting_position[1]["y"][i])
                    element.map_size = int(map_size)
                    self.scene_right.addItem(element)

                self.scene_right.addItem(Node(center, *center, None, map_size))
                self.graphicsView2.setScene(self.scene_right)

                if not self.animate :
                    for i in range(len(self.moves_history[0])) :
                        self.playground_left.move(int(self.moves_history[0][i]), int(self.random_elements[0][i]))

                    try :
                        self.Score1_1.setText(str(self.score_history[0][-1]))
                    except IndexError :
                        self.Score1_1.setText(str("0"))

                    for i, move in enumerate(self.moves_history[1]) :
                        self.playground_right.move(int(move), int(self.random_elements[1][i]))

                    try :
                        self.Score2_1.setText(str(self.score_history[1][-1]))
                    except IndexError :
                        self.Score2_1.setText(str("0"))

                    turn = 1 if (len(self.moves_history[0]) + len(self.moves_history[1]) + player1_starts) % 2 else 0
                    self.turn = 'A' if turn else 'B'
                    self.set_turn_text(self.turn == 'A')
                else :
                    self.animation_turn = player1_starts
                    self.animation_counter = [0, 0]

                    def show_moves_multiplayer(timer) :
                        if self.animation_turn :
                            try :
                                self.set_turn_text(False)
                                self.playground_left.move(int(self.moves_history[0][self.animation_counter[0]]),
                                                          int(self.random_elements[0][self.animation_counter[0]]))
                                self.Score1_1.setText(str(self.score_history[0][self.animation_counter[0]]))
                            except IndexError :
                                if self.animation_counter[1] == len(self.moves_history[1]) :
                                    timer.stop( )
                            self.animation_counter[0] += 1
                            if self.animation_counter[0] == len(self.moves_history[0]) and self.animation_counter[
                                1] == len(self.moves_history[1]) :
                                timer.stop( )
                            self.animation_turn = not self.animation_turn
                        else :
                            try :
                                self.set_turn_text(True)
                                self.playground_right.move(int(self.moves_history[1][self.animation_counter[1]]),
                                                           int(self.random_elements[1][self.animation_counter[1]]))
                                self.Score2_1.setText(str(self.score_history[1][self.animation_counter[1]]))
                            except IndexError :
                                if self.animation_counter[0] == len(self.moves_history[0]) :
                                    timer.stop( )
                            self.animation_counter[1] += 1
                            if self.animation_counter[0] == len(self.moves_history[0]) and self.animation_counter[
                                1] == len(self.moves_history[1]) :
                                timer.stop( )
                            self.animation_turn = not self.animation_turn

                    self.timer = QTimer(self)
                    self.connect(self.timer, SIGNAL("timeout()"), lambda : show_moves_multiplayer(self.timer))
                    self.timer.start(1000)

    def lan_game(self) :
        if not self.server_on :
            self.server_on = True
            try :
                self.server = Server( )
                self.threadpool = QThreadPool( )
                self.threadpool.start(self.server)
            except OSError :
                pass
            try :
                self.is_lan_game = True
                self.solo_game = False
                try :
                    self.scene_right.clear( )
                except :
                    pass
                self.Score1_1.setText("0")
                self.Score2_1.setText("0")
                self.Turn1.setVisible(False)
                self.Turn2.setVisible(False)

                self.n = Network( )
                self.player = int(self.n.getP( ))
                self.turn = int(self.n.send_string("getturn"))

                self.scene_left = QGraphicsScene( )
                serv_elems = self.n.send("get")

                self.update_playground_from_server(serv_elems, "left")
                self.graphicsView1.setScene(self.scene_left)
            except TypeError :
                self.is_lan_game = False
                self.solo_game = True
                #print("Info: Server not running")
        else :
            pass

    def add_oponent_log(self) :
        oponent_move = int(self.n.send_string("getoponentmove"))
        if oponent_move == 0 :
            self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Upper-left</b>")
        elif oponent_move == 1 :
            self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Upper-right</b>")
        elif oponent_move == 2 :
            self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Left</b>")
        elif oponent_move == 3 :
            self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Right</b>")
        elif oponent_move == 4 :
            self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Down-left</b>")
        elif oponent_move == 5 :
            self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Down-right</b>")

    def set_turn_text(self, condition) :
        if condition :
            self.Turn1.setVisible(True)
            self.Turn2.setVisible(False)
        else :
            self.Turn1.setVisible(False)
            self.Turn2.setVisible(True)

    def update_playground_from_server(self, serv_elems, side) :
        if side == "left" :
            self.scene_left = QGraphicsScene( )
            self.scene_left.clear( )
            for i in range(len(serv_elems["id"])) :
                element = Node(serv_elems["center"][i], serv_elems["x"][i], serv_elems["y"][i],
                               serv_elems["num"][i],
                               serv_elems["map_size"][i], serv_elems["id"][i])
                self.scene_left.addItem(element)

            self.scene_left.addItem(
                Node(serv_elems["center"][0], *serv_elems["center"][0], None, serv_elems["map_size"][0]))

            self.Score1_1.setText(str(serv_elems["score"]))
            self.graphicsView1.setScene(self.scene_left)
        elif side == "right" :
            self.scene_right = QGraphicsScene( )
            self.scene_right.clear( )
            for i in range(len(serv_elems["id"])) :
                element = Node(serv_elems["center"][i], serv_elems["x"][i], serv_elems["y"][i],
                               serv_elems["num"][i],
                               serv_elems["map_size"][i], serv_elems["id"][i])
                self.scene_right.addItem(element)

            self.scene_right.addItem(
                Node(serv_elems["center"][0], *serv_elems["center"][0], None, serv_elems["map_size"][0]))

            self.Score2_1.setText(str(serv_elems["score"]))
            self.graphicsView2.setScene(self.scene_right)

    def show_dialog(self) :
        dialog = Dialog(self)
        dialog.show( )
        dialog.exec_( )

    def connect_online(self) :
        try :
            self.is_connected = True
            condition = (self.turn == self.player)
            self.set_turn_text(condition)
            self.GameHistoryTextEdit.clear( )
            loop = QEventLoop( )
            while self.is_connected and Server.server_running :
                self.play_online( )
                QTimer.singleShot(2000, loop.quit)
                loop.exec_( )
            self.GameHistoryTextEdit.append(
                "2nd player has left the game, server stopped \nTo play online, please restart the game")
            self.threadpool.releaseThread( )
        except AttributeError :
            self.GameHistoryTextEdit.append("Info: Not connected to server")

    def play_online(self) :
        try :
            self.update_playground_from_server(self.n.send("get"), "left")
            self.update_playground_from_server(self.n.send("online"), "right")
            turn_buf = int(self.n.send_string("getturn"))
            if turn_buf != self.turn :
                self.add_oponent_log( )
            self.turn = turn_buf
            condition = self.turn == self.player
            self.set_turn_text(condition)
        except :
            self.threadpool.releaseThread( )

    def play_offline(self) :
        Server.server_running = False
        self.is_lan_game = False
        self.is_connected = False
        self.first_turn = 'A'
        self.turn = self.first_turn

        self.__new_gameHistory( )

        self.GameHistoryTextEdit.clear( )
        self.Score1_1.setText("0")
        self.Score2_1.setText("0")
        self.solo_game = False
        self.create_left_offline_scene( )
        self.create_right_offline_scene( )
        self.set_turn_text(True)

    def create_left_offline_scene(self) :
        self.scene_left = QGraphicsScene( )
        self.playground_left = Playground(self.playground_size)
        for element in self.playground_left.elements :
            self.scene_left.addItem(element)
            self.starting_position[0]["id"].append(element.id)
            self.starting_position[0]["num"].append(element.num)
            self.starting_position[0]["centerx"].append(element.center[0])
            self.starting_position[0]["centery"].append(element.center[1])
            self.starting_position[0]["x"].append(element.x)
            self.starting_position[0]["y"].append(element.y)
            self.starting_position[0]["map_size"].append(element.map_size)

        self.scene_left.addItem(Node(self.center, *self.center, None, self.playground_size))
        self.graphicsView1.setScene(self.scene_left)

    def create_right_offline_scene(self) :
        self.scene_right = QGraphicsScene( )
        self.playground_right = Playground(self.playground_size)
        for element in self.playground_right.elements :
            self.scene_right.addItem(element)
            self.starting_position[1]["id"].append(element.id)
            self.starting_position[1]["num"].append(element.num)
            self.starting_position[1]["centerx"].append(element.center[0])
            self.starting_position[1]["centery"].append(element.center[1])
            self.starting_position[1]["x"].append(element.x)
            self.starting_position[1]["y"].append(element.y)
            self.starting_position[1]["map_size"].append(element.map_size)

        self.scene_right.addItem(Node(self.center, *self.center, None, self.playground_size))
        self.graphicsView2.setScene(self.scene_right)

    def new_game(self) :
        if not self.solo_game :
            self.set_turn_text(True)
            self.first_turn = 'A'
            self.turn = self.first_turn

        self.__new_gameHistory( )
        self.GameHistoryTextEdit.clear( )
        if not self.is_lan_game :
            self.create_left_offline_scene( )
            if not self.solo_game :
                self.create_right_offline_scene( )
            self.Score1_1.setText("0")
            self.Score2_1.setText("0")
        else :
            s = self.n.send_string("restart" + str(self.playground_size))
            serv_elems = self.n.send("get")
            self.update_playground_from_server(serv_elems, "left")

    def move_instruction(self, num) :
        if self.is_lan_game :
            move_condition = True if self.turn == self.player else False
        else :
            move_condition = True if self.turn == 'A' or self.solo_game else False

        if move_condition :
            self.key_pressed["player1"] = list(map(lambda x : x * 0, self.key_pressed["player1"]))

            if num == 0 :
                self.GameHistoryTextEdit.append("<b style=\"color:#407294;\">A: Upper-left</b>")
                if self.is_lan_game :
                    self.update_playground_from_server(self.n.send("0"), "left")
                    self.turn = not self.turn
                else :
                    self.playground_left.move(0)
                    self.Score1_1.setText(str(self.playground_left.score))
                    self.turn = 'B'
                    if not self.solo_game :
                        self.set_turn_text(self.turn == 'A')
                self.moves_history[0].append(0)
                self.score_history[0].append(self.playground_left.score)
                self.random_elements[0].append(self.playground_left.random_element)
            elif num == 1 :
                self.GameHistoryTextEdit.append("<b style=\"color:#407294;\">A: Upper-right</b>")
                if self.is_lan_game :
                    self.update_playground_from_server(self.n.send("1"), "left")
                    self.turn = not self.turn
                else :
                    self.playground_left.move(1)
                    self.Score1_1.setText(str(self.playground_left.score))
                    self.turn = 'B'
                    if not self.solo_game :
                        self.set_turn_text(self.turn == 'A')
                self.moves_history[0].append(1)
                self.score_history[0].append(self.playground_left.score)
                self.random_elements[0].append(self.playground_left.random_element)
            elif num == 4 :
                self.GameHistoryTextEdit.append("<b style=\"color:#407294;\">A: Down-left</b>")
                if self.is_lan_game :
                    self.update_playground_from_server(self.n.send("4"), "left")
                    self.turn = not self.turn
                else :
                    self.playground_left.move(4)
                    self.Score1_1.setText(str(self.playground_left.score))
                    self.turn = 'B'
                    if not self.solo_game :
                        self.set_turn_text(self.turn == 'A')
                self.moves_history[0].append(4)
                self.score_history[0].append(self.playground_left.score)
                self.random_elements[0].append(self.playground_left.random_element)
            elif num == 5 :
                self.GameHistoryTextEdit.append("<b style=\"color:#407294;\">A: Down-right</b>")
                if self.is_lan_game :
                    self.update_playground_from_server(self.n.send("5"), "left")
                    self.turn = not self.turn
                else :
                    self.playground_left.move(5)
                    self.Score1_1.setText(str(self.playground_left.score))
                    self.turn = 'B'
                    if not self.solo_game :
                        self.set_turn_text(self.turn == 'A')
                self.moves_history[0].append(5)
                self.score_history[0].append(self.playground_left.score)
                self.random_elements[0].append(self.playground_left.random_element)
            elif num == 2 :
                self.GameHistoryTextEdit.append("<b style=\"color:#407294;\">A: Left</b>")
                if self.is_lan_game :
                    self.update_playground_from_server(self.n.send("2"), "left")
                    self.turn = not self.turn
                else :
                    self.playground_left.move(2)
                    self.Score1_1.setText(str(self.playground_left.score))
                    self.turn = 'B'
                    if not self.solo_game :
                        self.set_turn_text(self.turn == 'A')
                self.moves_history[0].append(2)
                self.score_history[0].append(self.playground_left.score)
                self.random_elements[0].append(self.playground_left.random_element)
            elif num == 3 :
                self.GameHistoryTextEdit.append("<b style=\"color:#407294;\">A: Right</b>")
                if self.is_lan_game :
                    self.update_playground_from_server(self.n.send("3"), "left")
                    self.turn = not self.turn
                else :
                    self.playground_left.move(3)
                    self.Score1_1.setText(str(self.playground_left.score))
                    self.turn = 'B'
                    if not self.solo_game :
                        self.set_turn_text(self.turn == 'A')
                self.moves_history[0].append(3)
                self.score_history[0].append(self.playground_left.score)
                self.random_elements[0].append(self.playground_left.random_element)

    def keyPressEvent(self, e) :
        if e.key( ) == Qt.Key_Escape :
            self.close( )

        try :
            if self.is_lan_game :
                move_condition = True if self.turn == self.player else False
            else :
                move_condition = True if self.turn == 'A' or self.solo_game else False

            if move_condition and e.key( ) in self.movement_keys["player1"] or not self.in_turns :
                if e.key( ) == Qt.Key_D :
                    self.key_pressed["player1"][3] = 1
                elif e.key( ) == Qt.Key_A :
                    self.key_pressed["player1"][1] = 1
                elif e.key( ) == Qt.Key_W :
                    self.key_pressed["player1"][0] = 1
                elif e.key( ) == Qt.Key_S :
                    self.key_pressed["player1"][2] = 1

                if self.key_pressed["player1"][0] and self.key_pressed["player1"][1] :
                    self.move_instruction(0)
                elif self.key_pressed["player1"][0] and self.key_pressed["player1"][3] :
                    self.move_instruction(1)
                elif self.key_pressed["player1"][2] and self.key_pressed["player1"][1] :
                    self.move_instruction(4)
                elif self.key_pressed["player1"][2] and self.key_pressed["player1"][3] :
                    self.move_instruction(5)
                elif self.key_pressed["player1"][1] :
                    self.move_instruction(2)
                elif self.key_pressed["player1"][3] :
                    self.move_instruction(3)
                self.Score1_1.setText(str(self.playground_left.score))

            if self.playground_right :
                if self.turn == 'B' and e.key( ) in self.movement_keys["player2"] or not self.in_turns :
                    if e.key( ) == Qt.Key_L :
                        self.key_pressed["player2"][3] = 1
                    elif e.key( ) == Qt.Key_J :
                        self.key_pressed["player2"][1] = 1
                    elif e.key( ) == Qt.Key_I :
                        self.key_pressed["player2"][0] = 1
                    elif e.key( ) == Qt.Key_K :
                        self.key_pressed["player2"][2] = 1

                    if self.key_pressed["player2"][0] and self.key_pressed["player2"][1] :
                        self.key_pressed["player2"] = list(map(lambda x : x * 0, self.key_pressed["player2"]))
                        self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Upper-left</b>")
                        self.playground_right.move(0)
                        self.turn = 'A'
                        if not self.solo_game :
                            self.set_turn_text(self.turn == 'A')
                        self.moves_history[1].append(0)
                        self.score_history[1].append(self.playground_right.score)
                        self.random_elements[1].append(self.playground_right.random_element)
                    elif self.key_pressed["player2"][0] and self.key_pressed["player2"][3] :
                        self.key_pressed["player2"] = list(map(lambda x : x * 0, self.key_pressed["player2"]))
                        self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Upper-right</b>")
                        self.playground_right.move(1)
                        self.turn = 'A'
                        if not self.solo_game :
                            self.set_turn_text(self.turn == 'A')
                        self.moves_history[1].append(1)
                        self.score_history[1].append(self.playground_right.score)
                        self.random_elements[1].append(self.playground_right.random_element)
                    elif self.key_pressed["player2"][2] and self.key_pressed["player2"][1] :
                        self.key_pressed["player2"] = list(map(lambda x : x * 0, self.key_pressed["player2"]))
                        self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Down-left</b>")
                        self.playground_right.move(4)
                        self.turn = 'A'
                        if not self.solo_game :
                            self.set_turn_text(self.turn == 'A')
                        self.moves_history[1].append(4)
                        self.score_history[1].append(self.playground_right.score)
                        self.random_elements[1].append(self.playground_right.random_element)
                    elif self.key_pressed["player2"][2] and self.key_pressed["player2"][3] :
                        self.key_pressed["player2"] = list(map(lambda x : x * 0, self.key_pressed["player2"]))
                        self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Down-right</b>")
                        self.playground_right.move(5)
                        self.turn = 'A'
                        if not self.solo_game :
                            self.set_turn_text(self.turn == 'A')
                        self.moves_history[1].append(5)
                        self.score_history[1].append(self.playground_right.score)
                        self.random_elements[1].append(self.playground_right.random_element)
                    elif self.key_pressed["player2"][1] :
                        self.key_pressed["player2"] = list(map(lambda x : x * 0, self.key_pressed["player2"]))
                        self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Left</b>")
                        self.playground_right.move(2)
                        self.turn = 'A'
                        if not self.solo_game :
                            self.set_turn_text(self.turn == 'A')
                        self.moves_history[1].append(2)
                        self.score_history[1].append(self.playground_right.score)
                        self.random_elements[1].append(self.playground_right.random_element)
                    elif self.key_pressed["player2"][3] :
                        self.key_pressed["player2"] = list(map(lambda x : x * 0, self.key_pressed["player2"]))
                        self.GameHistoryTextEdit.append("<b style=\"color:#800000;\">B: Right</b>")
                        self.playground_right.move(3)
                        self.turn = 'A'
                        if not self.solo_game :
                            self.set_turn_text(self.turn == 'A')
                        self.moves_history[1].append(3)
                        self.score_history[1].append(self.playground_right.score)
                        self.random_elements[1].append(self.playground_right.random_element)
                    self.Score2_1.setText(str(self.playground_right.score))
        except AttributeError :
            pass

    def keyReleaseEvent(self, e) :
        if e.key( ) == Qt.Key_D :
            self.key_pressed["player1"][3] = 0
        elif e.key( ) == Qt.Key_A :
            self.key_pressed["player1"][1] = 0
        elif e.key( ) == Qt.Key_W :
            self.key_pressed["player1"][0] = 0
        elif e.key( ) == Qt.Key_S :
            self.key_pressed["player1"][2] = 0

        if e.key( ) == Qt.Key_L :
            self.key_pressed["player2"][3] = 0
        elif e.key( ) == Qt.Key_J :
            self.key_pressed["player2"][1] = 0
        elif e.key( ) == Qt.Key_I :
            self.key_pressed["player2"][0] = 0
        elif e.key( ) == Qt.Key_K :
            self.key_pressed["player2"][2] = 0

class XMLhandler :
    def __init__(self) :
        self.__new_data()

    def __new_data(self):
        self.first_turn = 0
        self.starting_position = [
            {"id" : [], "num" : [], "centerx" : [], "centery" : [], "x" : [], "y" : [], "map_size" : []} for _ in
            range(2)]
        self.moves_history = [[], []]
        self.random_elements = [[], []]
        self.score_history = [[], []]

    def define_data(self, first_turn, starting_position, moves_history, random_elements, score_history = None) :
        self.first_turn = first_turn
        self.starting_position = starting_position
        self.moves_history = moves_history
        self.random_elements = random_elements
        self.score_history = score_history

    def save(self, is_lan, num_of_players, path) :
        self.root = minidom.Document( )

        data = self.root.createElement('data')
        num_of_players = str(num_of_players)
        data.setAttribute('num_of_players', num_of_players)
        self.root.appendChild(data)

        players = [self.root.createElement('player1')]
        data.appendChild(players[0])
        if not num_of_players == 1 :
            players.append(self.root.createElement('player2'))
            data.appendChild(players[1])

            if is_lan:
                players[1].setAttribute('starts', str(self.first_turn))
                players[0].setAttribute('starts', str(abs(self.first_turn - 1)))
            else:
                if self.first_turn == 'A' and not is_lan :
                    players[1].setAttribute('starts', '0')
                elif not is_lan:
                    players[1].setAttribute('starts', '1')

        if self.first_turn == 'A' or num_of_players == 1 and not is_lan:
            players[0].setAttribute('starts', '1')
        else :
            players[0].setAttribute('starts', '0')

        for i, player in enumerate(players) :
            for item in self.starting_position[i].items( ) :
                key, elems = item
                node = self.root.createElement(key + str(i))
                player.appendChild(node)
                node.setAttribute("quantity", str(len(self.starting_position[i][key])))
                for j, elem in enumerate(elems) :
                    value = self.root.createElement(key + str(i) + "_" + str(j))
                    text = self.root.createTextNode(str(elem))
                    value.appendChild(text)
                    node.appendChild(value)

        for i, player in enumerate(players) :
            node = self.root.createElement('moves' + str(i))
            node.setAttribute("quantity", str(len(self.moves_history[i])))
            player.appendChild(node)
            for j, move in enumerate(self.moves_history[i]) :
                value = self.root.createElement("move" + str(i) + "_" + str(j))
                text = self.root.createTextNode(str(move))
                value.appendChild(text)
                node.appendChild(value)

        for i, player in enumerate(players) :
            node = self.root.createElement('random_elements' + str(i))
            node.setAttribute("quantity", str(len(self.random_elements[i])))
            player.appendChild(node)
            for j, random_element in enumerate(self.random_elements[i]) :
                value = self.root.createElement("random_element" + str(i) + "_" + str(j))
                text = self.root.createTextNode(str(random_element))
                value.appendChild(text)
                node.appendChild(value)

        if not is_lan:
            for i, player in enumerate(players) :
                node = self.root.createElement('score' + str(i))
                node.setAttribute("quantity", str(len(self.random_elements[i])))
                player.appendChild(node)
                for j, score in enumerate(self.score_history[i]) :
                    value = self.root.createElement("score" + str(i) + "_" + str(j))
                    text = self.root.createTextNode(str(score))
                    value.appendChild(text)
                    node.appendChild(value)

        xml_str = self.root.toprettyxml(indent="\t")

        save_path_file = path

        with open(save_path_file, "w") as f :
            f.write(xml_str)

    def load(self, path, is_lan = False):
        mydoc = minidom.parse(path)
        self.__new_data()

        player = mydoc.getElementsByTagName('player1')
        self.first_turn = int(player[0].attributes['starts'].value)

        data = mydoc.getElementsByTagName('data')
        num_of_players = int(data[0].attributes['num_of_players'].value)


        for i in range(num_of_players) :
            for key in self.starting_position[i] :
                item = mydoc.getElementsByTagName(key + str(i))
                for j in range(int(item[0].attributes['quantity'].value)) :
                    value = mydoc.getElementsByTagName(key + str(i) + "_" + str(j))
                    self.starting_position[i][key].append(int(value[0].firstChild.data))

        for i in range(num_of_players) :
            item = mydoc.getElementsByTagName("moves" + str(i))
            for j in range(int(item[0].attributes['quantity'].value)) :
                value = mydoc.getElementsByTagName("move" + str(i) + "_" + str(j))
                self.moves_history[i].append(value[0].firstChild.data)

        for i in range(num_of_players) :
            item = mydoc.getElementsByTagName("random_elements" + str(i))
            for j in range(int(item[0].attributes['quantity'].value)) :
                value = mydoc.getElementsByTagName("random_element" + str(i) + "_" + str(j))
                self.random_elements[i].append(value[0].firstChild.data)
        if not is_lan:
            for i in range(num_of_players) :
                item = mydoc.getElementsByTagName("score" + str(i))
                for j in range(int(item[0].attributes['quantity'].value)) :
                    value = mydoc.getElementsByTagName("score" + str(i) + "_" + str(j))
                    self.score_history[i].append(value[0].firstChild.data)

        return num_of_players, self.first_turn, self.starting_position, self.moves_history,  self.random_elements, self.score_history


if __name__ == "__main__" :
    app = QApplication(sys.argv)
    w = MainWindow( )
    w.show( )
    sys.exit(app.exec_( ))
