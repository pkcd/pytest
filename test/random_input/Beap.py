class Beap:
    
    def __init__(self):
        self.__data = []
        self.__insertPos = (1, 0)
    
    def contains(self, x):
        return self.__contains__(x)
    
    def __iter__(self):
        return self.__data.__iter__()
    
    def __contains__(self, x):
        if len(self.__data) == 0: return False
        
        (i, j) = self.__insertPos
        pos = (i, 0)
        if 0==j:
            pos = (i-1, 0)
        
        
        while not self.__invalid(pos):
            if self.__at(pos) == x:
                return True
            elif self.__at(pos) < x:
                nPos = self.__rightChild(pos)
                if self.__invalid(nPos):
                    nPos = self.__rightParent(pos)
                pos = nPos
            elif self.__at(pos) > x:
                pos = self.__rightParent(pos)
        
        return False
    
    def insertAll(self, xs):
        assert isinstance(xs, list)
        for x in xs:
            self.insert(x)
    
    def insert(self, x):
        # insert it
        self.__data.append(x)
        (i, j) = self.__insertPos
        self.__insertPos = (i, j+1)
        if j+1 >= i:
            self.__insertPos = (i+1, 0)
        # sift up
        self.__sift((i, j))
    
    def __at(self, pos):
        p = self.__arrayPos(pos)
        return self.__data[p]

    def __set(self, pos, x):
        p = self.__arrayPos(pos)
        self.__data[p] = x
    
    def __sift(self, pos):
        lP = self.__leftParent(pos)
        rP = self.__rightParent(pos)
        if self.__invalid(lP):
            lP = rP
        if self.__invalid(rP):
            rP = lP
        if self.__invalid(rP) and self.__invalid(lP):
            return
        if self.__at(pos) < self.__at(lP) or self.__at(pos) < self.__at(rP):
            if self.__at(lP) < self.__at(rP):
                x = self.__at(rP)
                self.__set(rP, self.__at(pos))
                self.__set(pos, x)
                self.__sift(rP)
                return
            else:
                x = self.__at(lP)
                self.__set(lP, self.__at(pos))
                self.__set(pos, x)
                self.__sift(lP)
                return
    
    def __arrayPos(self, pos):
        (i, j) = pos
        return ((i*(i-1))/2) + j
    
    def __leftParent(self, pos):
        (i, j) = pos
        return (i-1, j-1)
    
    def __rightParent(self, pos):
        (i, j) = pos
        return (i-1, j)
    
    def __leftChild(self, pos):
        (i, j) = pos
        return (i+1, j)
    
    def __rightChild(self, pos):
        (i, j) = pos
        return (i+1, j+1)
    
    def __invalid(self, pos):
        (i, j) = pos
        if i <= 0:
            return True
        if j >= i or j < 0:
            return True
        if self.__arrayPos(pos) >= len(self.__data):
            return True
        return False
    
def __typeHints():
    beap = Beap()
    beap.insertAll([1])
    beap.insert(42)
    for x in [1, 42]:
        assert x in beap
    assert beap.contains(1)