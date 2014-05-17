from PIL import Image, ImageDraw
import heapq
import sys

MODE_RECTANGLE = 1
MODE_ELLIPSE = 2
MODE_ROUNDED_RECTANGLE = 3

MODE = MODE_RECTANGLE
ITERATIONS = 1024
LEAF_SIZE = 4
SHOW_GRID = True
GRID_COLOR = (0, 0, 0)
SAVE_FRAMES = False
ERROR_RATE = 0.5
AREA_POWER = 0.25
SCALE = 1

def weighted_average(hist):
    total = sum(hist)
    value = sum(i * x for i, x in enumerate(hist)) / total
    error = sum(x * (value - i) ** 2 for i, x in enumerate(hist)) / total
    error = error ** 0.5
    return value, error

def color_from_histogram(hist):
    r, re = weighted_average(hist[:256])
    g, ge = weighted_average(hist[256:512])
    b, be = weighted_average(hist[512:768])
    e = re * 0.2989 + ge * 0.5870 + be * 0.1140
    return (r, g, b), e

def rounded_rectangle(draw, box, radius, color):
    l, t, r, b = box
    x = radius * 2
    z = radius
    draw.ellipse((l, t, l + x, t + x), color)
    draw.ellipse((r - x, t, r, t + x), color)
    draw.ellipse((l, b - x, l + x, b), color)
    draw.ellipse((r - x, b - x, r, b), color)
    draw.rectangle((l, t + z, r, b - z), color)
    draw.rectangle((l + z, t, r - z, b), color)

class Quad(object):
    def __init__(self, model, box):
        self.model = model
        self.box = box
        hist = self.model.im.crop(self.box).histogram()
        self.color, self.error = color_from_histogram(hist)
        self.leaf = self.is_leaf()
        self.area = self.compute_area()
    def is_leaf(self):
        l, t, r, b = self.box
        return int(r - l <= LEAF_SIZE or b - t <= LEAF_SIZE)
    def compute_area(self):
        l, t, r, b = self.box
        return (r - l) * (b - t)
    def split(self):
        l, t, r, b = self.box
        lr = l + (r - l) / 2
        tb = t + (b - t) / 2
        tl = Quad(self.model, (l, t, lr, tb))
        tr = Quad(self.model, (lr, t, r, tb))
        bl = Quad(self.model, (l, tb, lr, b))
        br = Quad(self.model, (lr, tb, r, b))
        return (tl, tr, bl, br)

class Model(object):
    def __init__(self, path):
        self.im = Image.open(path).convert('RGB')
        self.width, self.height = self.im.size
        self.quads = []
        quad = Quad(self, (0, 0, self.width, self.height))
        self.error_sum = quad.error * quad.area
        self.push(quad)
    def average_error(self):
        return self.error_sum / (self.width * self.height)
    def push(self, quad):
        score = -quad.error * (quad.area ** AREA_POWER)
        heapq.heappush(self.quads, (quad.leaf, score, quad))
    def pop(self):
        return heapq.heappop(self.quads)
    def split(self):
        leaf, score, quad = self.pop()
        self.error_sum -= quad.error * quad.area
        children = quad.split()
        for child in children:
            self.push(child)
            self.error_sum += child.error * child.area
    def render(self, path):
        m = SCALE
        dx, dy = (1, 1) if SHOW_GRID else (0, 0)
        im = Image.new('RGB', (self.width * m + dx, self.height * m + dy))
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 0, self.width * m, self.height * m), GRID_COLOR)
        for leaf, score, quad in self.quads:
            l, t, r, b = quad.box
            box = (l * m + dx, t * m + dy, r * m - 1, b * m - 1)
            if MODE == MODE_ELLIPSE:
                draw.ellipse(box, quad.color)
            elif MODE == MODE_ROUNDED_RECTANGLE:
                radius = (r - l) / 4
                rounded_rectangle(draw, box, radius, quad.color)
            else:
                draw.rectangle(box, quad.color)
        del draw
        im.save(path, 'PNG')

def main():
    args = sys.argv[1:]
    if len(args) != 1:
        print 'Usage: python main.py input_image'
        return
    model = Model(args[0])
    previous = None
    for i in range(ITERATIONS):
        error = model.average_error()
        if previous is None or previous - error > ERROR_RATE:
            print i, error
            if SAVE_FRAMES:
                model.render('frames/%06d.png' % i)
            previous = error
        model.split()
    model.render('output.png')

if __name__ == '__main__':
    main()
