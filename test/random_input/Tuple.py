# Ideas:

# Check capability of creating tuples

def vectorAdd(a, b):
    (a1, a2, a3) = a
    (b1, b2, b3) = b
    return (a1 + b1, a2 + b2, a3 + b3)

# Check tuples with various types

def addToList(t):
    n, list = t
    return [x + n for x in list]

# Check polymorphism in tuples

# Check usage of tuple components

def binom(a,b):
    if a == 0 or b == 0:
        raise Exception('boring')
    return (a, b, a*a + 2*a*b + b*b)

def checkBinom(a,b,c):
    if a == 0 or b == 0:
        raise Exception('boring')
    if c == a*a + 2*a*b + b*b:
        return c
    else:
        raise Exception('value does not match')

def _typeHint():
    vectorAdd((0,0,0),(0,0,0))
    addToList((0,[0]))
    binom(0,0)
    checkBinom(0,0,0)