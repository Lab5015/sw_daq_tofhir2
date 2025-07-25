import zmq
from time import sleep

class serialClient:
    def __init__(self,port):
        self.port=port
        context = zmq.Context()
        self.socket = context.socket(zmq.REQ)
        self.socket.connect(port)

    def write(self,msg):
        self.socket.send(msg.encode())        

    def readline(self):
        msg_in = self.socket.recv()
        return str(msg_in.decode('utf-8'))

