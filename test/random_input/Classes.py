class A(object):
    def __init__(self):
        self.x = 0
        self.y = 0

    def __init__(self, x):
        self.x = x
        self.y = 0

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def compare(self, o):
        if self is o:
            return 'IDENTICAL'
        if self.x == o.x and self.y == o.y:
            return 'EQUAL'
        if self.x < o.x or (self.x == o.x and self.y < o.y):
            return 'LESS'
        else:
            return 'GREATER'

class B(A):
    def __init__(self):
        self.x = 0
        self.y = 0
    
    def add(self, o):
        return B(self.x + o.x, self.y + o.y)

    def sub(self, o):
        return B(self.x - o.x, self.y - o.y)

def sum(list):
    result = B(0,0)
    for o in list:
        if o.x > 0:
            result = result.add(o)
        else:
            result = result.sub(o)

def _typeHint():
    B(0)
    B(0,0)
    sum([B()])