from PIL import Image, ImageDraw
from collections import Counter
import heapq
import sys

MODES = {'MODE_RECTANGLE': 1, 'MODE_ELLIPSE': 2, 'MODE_ROUNDED_RECTANGLE': 3}


def weighted_average(hist):
    total = sum(hist)
    value = sum(i * x for i, x in enumerate(hist)) // total  # cast to an int because of python 3
    error = (sum(x * (value - i) ** 2 for i, x in enumerate(hist)) // total) ** 0.5
    return value, error


def color_from_histogram(hist):
    r, re = weighted_average(hist[:256])
    g, ge = weighted_average(hist[256:512])
    b, be = weighted_average(hist[512:768])
    e = re * 0.2989 + ge * 0.5870 + be * 0.1140
    return (r, g, b), e


def rounded_rectangle(draw, box, radius, color):
    l, t, r, b = box
    d = radius * 2
    draw.ellipse((l, t, l + d, t + d), color)
    draw.ellipse((r - d, t, r, t + d), color)
    draw.ellipse((l, b - d, l + d, b), color)
    draw.ellipse((r - d, b - d, r, b), color)
    d = radius
    draw.rectangle((l, t + d, r, b - d), color)
    draw.rectangle((l + d, t, r - d, b), color)


class Quad(object):
    def __init__(self, model, box, depth):
        self.model = model
        self.box = box
        self.depth = depth
        hist = self.model.im.crop(self.box).histogram()
        self.color, self.error = color_from_histogram(hist)
        self.leaf = self.is_leaf()
        self.area = self.compute_area()
        self.children = []

    def is_leaf(self):
        l, t, r, b = self.box
        return int(r - l <= self.model.get_leaf_size() or b - t <= self.model.get_leaf_size())

    def compute_area(self):
        l, t, r, b = self.box
        return (r - l) * (b - t)

    def split(self):
        l, t, r, b = self.box
        lr = l + (r - l) // 2
        tb = t + (b - t) // 2
        depth = self.depth + 1
        tl = Quad(self.model, (l, t, lr, tb), depth)
        tr = Quad(self.model, (lr, t, r, tb), depth)
        bl = Quad(self.model, (l, tb, lr, b), depth)
        br = Quad(self.model, (lr, tb, r, b), depth)
        self.children = (tl, tr, bl, br)
        return self.children

    def get_leaf_nodes(self, max_depth=None):
        if not self.children:
            return [self]
        if max_depth is not None and self.depth >= max_depth:
            return [self]
        result = []
        for child in self.children:
            result.extend(child.get_leaf_nodes(max_depth))
        return result


class Model(object):
    def __init__(self, path):
        self.mode = MODES["MODE_RECTANGLE"]
        self.iterations = 1024
        self.leaf_size = 4
        self.padding = 1
        self.fill_color = (0, 0, 0)
        self.save_frames = False
        self.error_rate = 0.5
        self.area_power = 0.25
        self.output_scale = 1
        # entry_count (used in push) is necessary in python 3 since heapq can't handle duplicate values
        # it makes every tuple unique and preserves the insertion order
        self.entry_count = 0
        self.im = Image.open(path).convert('RGB')
        self.width, self.height = self.im.size
        self.heap = []
        self.root = Quad(self, (0, 0, self.width, self.height), 0)
        self.error_sum = self.root.error * self.root.area
        self.push(self.root)

    def reset(self):
        self.entry_count = 0
        self.heap = []
        self.root = Quad(self, (0, 0, self.width, self.height), 0)
        self.error_sum = self.root.error * self.root.area
        self.push(self.root)

    @property
    def quads(self):
        return [x[-1] for x in self.heap]

    def average_error(self):
        return self.error_sum / (self.width * self.height)

    def push(self, quad):
        score = -quad.error * (quad.area ** self.area_power)
        heapq.heappush(self.heap, (quad.leaf, score, self.entry_count, quad))
        self.entry_count += 1

    def pop(self):
        return heapq.heappop(self.heap)[-1]

    def split(self):
        quad = self.pop()
        self.error_sum -= quad.error * quad.area
        children = quad.split()
        for child in children:
            self.push(child)
            self.error_sum += child.error * child.area

    def render(self, path, max_depth=None):
        m = self.output_scale
        dx, dy = (self.padding, self.padding)
        im = Image.new('RGB', (self.width * m + dx, self.height * m + dy))
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 0, self.width * m, self.height * m), self.fill_color)
        for quad in self.root.get_leaf_nodes(max_depth):
            l, t, r, b = quad.box
            box = (l * m + dx, t * m + dy, r * m - 1, b * m - 1)
            if self.mode == MODES['MODE_ELLIPSE']:
                draw.ellipse(box, quad.color)
            elif self.mode == MODES['MODE_ROUNDED_RECTANGLE']:
                radius = m * min((r - l), (b - t)) / 4
                rounded_rectangle(draw, box, radius, quad.color)
            elif self.mode == MODES['MODE_RECTANGLE']:
                draw.rectangle(box, quad.color)
            else:
                raise Exception('Wrong mode %d' % self.mode)
        del draw
        im.save(path, 'PNG')

    def execute(self, path='output.png'):
        previous = None
        for i in range(self.iterations):
            error = self.average_error()
            if previous is None or previous - error > self.error_rate:
                print(i, error)
                if self.save_frames:
                    self.render('frames/%06d.png' % i)
                previous = error
            self.split()
        self.render(path)

        print('-' * 32)
        depth = Counter(x.depth for x in self.quads)
        for key in sorted(depth):
            value = depth[key]
            n = 4 ** key
            pct = 100.0 * value / n
            print('%3d %8d %8d %8.2f%%' % (key, n, value, pct))
        print('-' * 32)
        print('             %8d %8.2f%%' % (len(self.quads), 100))
        # for max_depth in range(max(depth.keys()) + 1):
        #     self.model.render('out%d.png' % max_depth, max_depth)

    def set_mode(self, mode):
        if isinstance(mode, int) and mode in MODES.values():
            self.mode = mode
        else:
            mode = MODES.get(mode)
            if mode is not None:
                self.mode = mode

    def get_mode(self):
        return self.mode

    def set_iterations(self, iterations):
        self.iterations = iterations

    def get_iterations(self):
        return self.iterations

    def set_leaf_size(self, leaf_size):
        self.leaf_size = leaf_size

    def get_leaf_size(self):
        return self.leaf_size

    def set_padding(self, padding):
        self.padding = padding

    def get_padding(self):
        return self.padding

    def set_fill_color(self, color):
        self.fill_color = color

    def get_fill_color(self):
        return self.fill_color

    def set_save_frames(self, save_frames):
        if isinstance(save_frames, bool):
            self.save_frames = save_frames

    def get_save_frames(self):
        return self.save_frames

    def set_error_rate(self, error_rate):
        if isinstance(error_rate, (int, float)):
            if error_rate <= 0.0:
                self.error_rate = 0.0
            elif error_rate >= 1.0:
                self.error_rate = 1.0
            else:
                self.error_rate = error_rate

    def get_error_rate(self):
        return self.error_rate

    def set_area_power(self, power):
        if isinstance(power, (int, float)):
            if power <= 0.0:
                self.area_power = 0.0
            elif power >= 1.0:
                self.area_power = 1.0
            else:
                self.area_power = power

    def get_area_power(self):
        return self.area_power

    def set_output_scale(self, scale):
        self.output_scale = scale

    def get_output_scale(self):
        return self.output_scale


def main():
    args = sys.argv[1:]
    if len(args) != 1:
        print('Usage: python main.py input_image')
        return
    model = Model(args[0])
    model.execute()


if __name__ == '__main__':
    main()
