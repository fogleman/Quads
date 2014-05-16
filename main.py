from PIL import Image, ImageDraw
import heapq
import random

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
    def is_leaf(self):
        l, t, r, b = self.box
        return int(r - l <= 1 or b - t <= 1)
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
        self.push(quad)
    def push(self, quad):
        score = -quad.error
        # score = random.random()
        # score = -quad.error + (random.random() - 0.5) * 8
        heapq.heappush(self.quads, (quad.leaf, score, quad))
    def pop(self):
        return heapq.heappop(self.quads)
    def split(self):
        leaf, error, quad = self.pop()
        children = quad.split()
        for child in children:
            self.push(child)
    def render(self, path):
        im = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(im)
        for leaf, error, quad in self.quads:
            l, t, r, b = quad.box
            draw.rectangle((l, t, r - 1, b - 1), quad.color)
        del draw
        im.save(path, 'PNG')

def main():
    model = Model('me.jpg')
    for i in range(2048):
        model.split()
        if i % 64 == 0:
            model.render('frames/%06d.png' % i)
    model.render('output.png')

if __name__ == '__main__':
    main()
