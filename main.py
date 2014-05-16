from PIL import Image, ImageDraw
import heapq
import random
import struct
import zlib

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
        self.children = []
    @property
    def area(self):
        l, t, r, b = self.box
        return (r - l) * (b - t)
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
        self.children = [tl, tr, bl, br]
        return self.children
    def serialize(self):
        result = []
        if self.children:
            result.append(struct.pack('<B', 0))
            for child in self.children:
                result.append(child.serialize())
        else:
            result.append(struct.pack('<B', 1))
            result.append(struct.pack('<BBB', *self.color))
        return ''.join(result)

class Model(object):
    def __init__(self, path):
        self.im = Image.open(path).convert('RGB')
        self.width, self.height = self.im.size
        self.quads = []
        self.root = Quad(self, (0, 0, self.width, self.height), 0)
        self.error_numerator = self.root.error * self.root.area
        self.error_denominator = self.root.area
        self.push(self.root)
    def total_error(self):
        return self.error_numerator / self.error_denominator
    def push(self, quad):
        score = -quad.error * (quad.area ** 0.125)
        # score = random.random()
        # score = -quad.error + (random.random() - 0.5) * 8
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
        im = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 0, self.width, self.height), (0, 0, 0))
        for leaf, score, quad in self.quads:
            l, t, r, b = quad.box
            draw.rectangle((l, t, r - 2, b - 2), quad.color)
        del draw
        im.save(path, 'PNG')
    def serialize(self):
        result = self.root.serialize()
        result = zlib.compress(result)
        return result

def main():
    model = Model('starry.png')
    previous = None
    for i in range(8192):
        error = model.total_error()
        if previous is None or previous - error > 1:
            print i, error
            model.render('frames/%06d.png' % i)
            previous = error
        model.split()
    model.render('output.png')

if __name__ == '__main__':
    main()
