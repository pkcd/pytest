class Item(object):
    def __init__(self, name, price, weight):
        self.name = name
        self.price = price
        self.weight = weight

    def __hash__(self):
        return hash((self.name, self.price, self.weight))

    def __eq__(self, other):
        return (self.name, self.price, self.weight) == (other.name, other.price, other.weight)

class Coupon(object):
    PERCENTAGE='percentage'
    CONSTANT='constant'

    def __init__(self, mode, amount):
        self.mode = mode
        self.amount = amount

    def getTotal(self, n):
        if self.mode == Coupon.PERCENTAGE:
            if self.amount > 100:
                raise Exception('can not give more than 100% off')
            return (1.0 - (float(self.amount) / 100)) * n
        if self.mode == Coupon.CONSTANT:
            return max(0, n - self.amount)

class Order(object):

    SHIP = 'ship'
    TRUCK = 'truck'
    HELICOPTER = 'helicopter'

    def __init__(self):
        self.items = dict()
        self.coupon = None
        self.shipping = Order.TRUCK
        self.address = None

    def addItem(self, item, amount):
        if not (item in self.items):
            self.items[item] = 0
        self.items[item] += amount

    def removeItem(self, item, amount):
        if not (item in self.items):
            raise Exception('item not in order')
        if self.items[item] < amount:
            raise Exception('not enough items')
        self.items[item] = self.items[item] - amount
        if self.items[item] == 0:
            self.items.pop(item, None)

    def addCoupon(self, coupon):
        self.coupon = coupon

    def setShipping(self, method):
        self.method = method

    def setAddress(self, address):
        self.address = address

    def process(self):
        if not self.address:
            raise Exception('address is not set')
        if not ('New Zealand' in self.address) and self.method == Order.TRUCK:
            raise Exception('Can not ship by truck outside of New Zealand')
        weight = 0.0
        price = 0.0
        for (item, amount) in self.items.items():
            weight += item.weight
            price += amount * item.price

        if weight > 1000 and self.method == Order.HELICOPTER:
            raise Exception('too heavy for a helicopter')

        if self.coupon:
            return self.coupon.getTotal(price)
        else:
            return price

def _typeHint():
    i = Item('', 0.0, 0.0)
    c = Coupon(Coupon.CONSTANT, 0.0)
    c.getTotal(0.0)
    o = Order()
    o.addItem(i,0)
    o.removeItem(i,0)
    o.addCoupon(c)
    o.setShipping(Order.TRUCK)
    o.setAddress('')