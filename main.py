from PIL import Image, ImageDraw
import heapq
import sys

ITERATIONS = 1024
LEAF_SIZE = 4
SHOW_GRID = True
GRID_COLOR = (0, 0, 0)
SAVE_FRAMES = False
ERROR_RATE = 0.5

def weighted_average(hist):
    count = sum(i * x for i, x in enumerate(hist))
    total = sum(hist)
    return count / total

def color_from_histogram(hist):
    r = weighted_average(hist[:256])
    g = weighted_average(hist[256:512])
    b = weighted_average(hist[512:768])
    return (r, g, b)

def component_error(hist, value):
    count = sum(x * (value - i) ** 2 for i, x in enumerate(hist))
    total = sum(hist)
    return (count / total) ** 0.5

def error(hist, color):
    r = component_error(hist[:256], color[0])
    g = component_error(hist[256:512], color[1])
    b = component_error(hist[512:768], color[2])
    return r * 0.2989 + g * 0.5870 + b * 0.1140

class Quad(object):
    def __init__(self, model, box, depth):
        self.model = model
        self.box = box
        self.depth = depth
        hist = self.model.im.crop(self.box).histogram()
        self.color = color_from_histogram(hist)
        self.error = error(hist, self.color)
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
        depth = self.depth + 1
        tl = Quad(self.model, (l, t, lr, tb), depth)
        tr = Quad(self.model, (lr, t, r, tb), depth)
        bl = Quad(self.model, (l, tb, lr, b), depth)
        br = Quad(self.model, (lr, tb, r, b), depth)
        return (tl, tr, bl, br)

class Model(object):
    def __init__(self, path):
        self.im = Image.open(path).convert('RGB')
        self.width, self.height = self.im.size
        self.quads = []
        quad = Quad(self, (0, 0, self.width, self.height), 0)
        self.error_numerator = quad.error * quad.area
        self.error_denominator = quad.area
        self.push(quad)
    def total_error(self):
        return self.error_numerator / self.error_denominator
    def push(self, quad):
        score = -quad.error * (quad.area ** 0.125)
        heapq.heappush(self.quads, (quad.leaf, score, quad))
    def pop(self):
        return heapq.heappop(self.quads)
    def split(self):
        leaf, score, quad = self.pop()
        self.error_numerator -= quad.error * quad.area
        children = quad.split()
        for child in children:
            self.push(child)
            self.error_numerator += child.error * child.area
    def render(self, path):
        dx, dy = (1, 1) if SHOW_GRID else (0, 0)
        im = Image.new('RGB', (self.width + dx, self.height + dy))
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 0, self.width, self.height), GRID_COLOR)
        for leaf, score, quad in self.quads:
            l, t, r, b = quad.box
            draw.rectangle((l + dx, t + dy, r - 1, b - 1), quad.color)
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
        error = model.total_error()
        if previous is None or previous - error > ERROR_RATE:
            print i, error
            if SAVE_FRAMES:
                model.render('frames/%06d.png' % i)
            previous = error
        model.split()
    model.render('output.png')

if __name__ == '__main__':
    main()
