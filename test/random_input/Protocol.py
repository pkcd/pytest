class Protocol(object):
    def __init__(self):
        self.connected = False
        self.authenticated = False

    def connect(self, ip):
        if self.connected:
            raise Exception('already connected')
        if ip == [196, 168, 47, 11]:
            self.connected = True
        return self.connected

    def authenticate(self, user, password):
        if self.authenticated:
            raise Exception('already authenticated')
        if not self.connected:
            raise Exception('not connected')
        if not (user == 'johndoe'):
            raise Exception('unknown user')
        if not (password == '1234'):
            raise Exception('wrong password')

    def send(self, message, length):
        if not self.authenticated:
            raise Exception('not authenticated')
        if len(message) != length:
            raise Exception('wrong length')

    def disconnect(self):
        self.connected = False
        self.authenticated = False

def _typeHint():
    p = Protocol()
    p.connect([0,0,0,0])
    p.authenticate('','')
    p.send('', 0)