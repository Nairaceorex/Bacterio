import socket
import time
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker

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


class Player(Base):
    __tablename__ = "gamers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(250))
    address = Column(String)
    x = Column(Integer, default=500)
    y = Column(Integer, default=500)
    size = Column(Integer, default=50)
    errors = Column(Integer, default=0)
    abs_speed = Column(Integer, default=1)
    speed_x = Column(Integer, default=0)
    speed_y = Column(Integer, default=0)

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


players = {}
while True:
    try:
        # проверяем желающих войти в игру
        new_socket, addr = main_socket.accept()  # принимаем входящие
        print('Подключился', addr)
        new_socket.setblocking(False)
        player = Player("Имя", addr)
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

    time.sleep(1)

    time.sleep(1)
