import socket
import time
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker
import pygame

main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Настраиваем сокет
main_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Отключаем пакетирование
main_socket.bind(("localhost", 10000))  # IP и порт привязываем к порту
main_socket.setblocking(False)  # Непрерывность, не ждём ответа
main_socket.listen(5)  # Прослушка входящих соединений, 5 одновременных подключений
print("Сокет создался")

engine = create_engine("postgresql+psycopg2://naira:11111@localhost/rebotica")
Session = sessionmaker(bind=engine)
Base = declarative_base()
s = Session()

pygame.init()
WIDHT_ROOM, HEIGHT_ROOM = 4000, 4000
WIDHT_SERVER, HEIGHT_SERVER = 300, 300
FPS = 100

screen = pygame.display.set_mode((WIDHT_SERVER, HEIGHT_SERVER))
pygame.display.set_caption("Сервер")
clock = pygame.time.Clock()


def find(vector: str):
    first = None
    for num, sign in enumerate(vector):
        if sign == "<":
            first = num
        if sign == ">" and first is not None:
            second = num
            result = map(int, vector[first + 1:second].split(","))
            return result
    return ""


def find_color(info: str):
    first = None
    for num, sign in enumerate(info):
        if sign == "<":
            first = num
        if sign == ">" and first is not None:
            second = num
            result = info[first + 1:second].split(",")
            return result
    return ""


class Player(Base):
    __tablename__ = "gamers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250))
    address = Column(String)
    x = Column(Integer, default=500)
    y = Column(Integer, default=500)
    size = Column(Integer, default=50)
    errors = Column(Integer, default=0)
    abs_speed = Column(Integer, default=2)
    speed_x = Column(Integer, default=2)
    speed_y = Column(Integer, default=2)
    color = Column(String(250), default="red")  # Добавили цвет
    w_vision = Column(Integer, default=800)
    h_vision = Column(Integer, default=600)

    def __init__(self, name, address):
        self.name = name
        self.address = address


Base.metadata.create_all(engine)


class LocalPlayer:
    def __init__(self, id, name, sock, addr):
        self.id = id
        self.db: Player = s.get(Player, self.id)
        self.sock = sock
        self.name = name
        self.address = addr
        self.x = 500
        self.y = 500
        self.size = 50
        self.errors = 0
        self.abs_speed = 1
        self.speed_x = 0
        self.speed_y = 0
        self.color = "red"
        self.w_vision = 800
        self.h_vision = 600

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y

        # Синхронизируем с БД
        self.db.x = self.x
        self.db.y = self.y
        self.db.speed_x = self.speed_x
        self.db.speed_y = self.speed_y
        s.merge(self.db)
        s.commit()

    def change_speed(self, vector):
        vector = find(vector)
        if vector[0] == 0 and vector[1] == 0:
            self.speed_x = self.speed_y = 0
        else:
            vector = vector[0] * self.abs_speed, vector[1] * self.abs_speed
            self.speed_x = vector[0]
            self.speed_y = vector[1]


players = {}
server_works = True
while server_works:
    clock.tick(FPS)

    try:
        # проверяем желающих войти в игру
        new_socket, addr = main_socket.accept()  # принимаем входящие
        print('Подключился', addr)
        new_socket.setblocking(False)
        login = new_socket.recv(1024).decode()
        player = Player("Имя", addr)
        if login.startswith("color"):
            data = find_color(login[6:])
            player.name, player.color = data
        s.merge(player)
        s.commit()

        addr = f'({addr[0]},{addr[1]})'
        data = s.query(Player).filter(Player.address == addr)
        for user in data:
            player = LocalPlayer(user.id, "Имя", new_socket, addr)
            players[user.id] = player

    except BlockingIOError:
        pass

    # Считываем команды игроков
    for id in list(players):
        try:
            data = players[id].sock.recv(1024).decode()
            print("Получил", data)
            players[id].change_speed(data)
        except:
            pass

    # Отправляем статус игрового поля
    for id in list(players):
        try:
            players[id].sock.send("Игра".encode())
        except:
            players[id].sock.close()
            del players[id]
            # Так же удаляем строчку из БД
            s.query(Player).filter(Player.id == id).delete()
            s.commit()
            print("Сокет закрыт")

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            server_works = False
    screen.fill('black')
    for id in list(players):
        player = players[id]
        x = player.x * WIDHT_SERVER // WIDHT_ROOM
        y = player.y * HEIGHT_SERVER // HEIGHT_ROOM
        size = player.size * WIDHT_SERVER // WIDHT_ROOM
        pygame.draw.circle(screen, player.color, (x, y), size)

    for id in list(players):
        player = players[id]
        players[id].update()

    pygame.display.update()

pygame.quit()
main_socket.close()
s.query(Player).delete()
s.commit()
