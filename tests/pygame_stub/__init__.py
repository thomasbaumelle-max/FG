class Surface:
    def __init__(self, size, flags=0):  # flags ignored
        self._width, self._height = size

    def convert_alpha(self):
        return self

    def get_size(self):
        return (self._width, self._height)

    def get_width(self):
        return self._width

    def get_height(self):
        return self._height

    def blit(self, *args, **kwargs):
        pass

    def fill(self, *args, **kwargs):  # noqa: D401 - dummy method
        """Dummy fill method for tests."""
        pass

    def copy(self):
        return Surface((self._width, self._height))
    def get_rect(self, **kwargs):  # noqa: D401 - dummy method
        """Return a simple rect covering the surface."""
        return Rect(0, 0, self._width, self._height)


class Rect:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.width = w
        self.height = h

    @property
    def left(self):
        return self.x

    @left.setter
    def left(self, value):
        self.x = value

    @property
    def top(self):
        return self.y

    @top.setter
    def top(self, value):
        self.y = value

    @property
    def right(self):
        return self.x + self.width

    @right.setter
    def right(self, value):
        self.x = value - self.width

    @property
    def bottom(self):
        return self.y + self.height

    @bottom.setter
    def bottom(self, value):
        self.y = value - self.height

    @property
    def centerx(self):
        return self.x + self.width // 2

    @centerx.setter
    def centerx(self, value):
        self.x = value - self.width // 2

    @property
    def centery(self):
        return self.y + self.height // 2

    @centery.setter
    def centery(self, value):
        self.y = value - self.height // 2

    @property
    def topleft(self):
        return (self.left, self.top)

    @property
    def center(self):
        return (self.centerx, self.centery)

    @property
    def size(self):
        return (self.width, self.height)

    @size.setter
    def size(self, value):
        self.width, self.height = value

    @property
    def midtop(self):
        return (self.centerx, self.top)

    @midtop.setter
    def midtop(self, pos):
        cx, cy = pos
        self.centerx = cx
        self.top = cy

    @property
    def midbottom(self):
        return (self.centerx, self.bottom)

    @midbottom.setter
    def midbottom(self, pos):
        cx, cy = pos
        self.centerx = cx
        self.bottom = cy

    def collidepoint(self, pos):
        x, y = pos
        return self.left <= x < self.right and self.top <= y < self.bottom

    def move(self, dx, dy):
        return Rect(self.x + dx, self.y + dy, self.width, self.height)

    def inflate(self, dw, dh):
        return Rect(
            self.x - dw // 2,
            self.y - dh // 2,
            self.width + dw,
            self.height + dh,
        )


def init():
    pass

SRCALPHA = 1


class font:
    _init = True

    @staticmethod
    def init():
        font._init = True

    @staticmethod
    def get_init():
        return font._init

    @staticmethod
    def SysFont(name, size, *args, **kwargs):
        class DummyFont:
            def render(self, text, aa, colour):
                return Surface((10, 10))

        return DummyFont()


class time:
    @staticmethod
    def wait(ms):
        pass

    class Clock:
        def tick(self, fps=0):
            pass


class draw:
    @staticmethod
    def rect(surface, colour, rect, width=0):
        pass

    @staticmethod
    def circle(surface, colour, center, radius):
        pass

    @staticmethod
    def ellipse(surface, colour, rect, width=0):
        pass


class transform:
    @staticmethod
    def scale(img, size):
        return img

    @staticmethod
    def smoothscale(img, size):
        return img

    @staticmethod
    def flip(img, xbool, ybool):
        return img

    @staticmethod
    def rotate(img, angle):
        return img


class display:
    _surface = Surface((800, 600))
    _init = True

    @staticmethod
    def set_mode(size, flags=0):
        display._surface = Surface(size)
        display._init = True
        return display._surface

    @staticmethod
    def get_surface():
        return display._surface

    @staticmethod
    def get_init():
        return display._init

    @staticmethod
    def Info():
        class InfoObj:
            current_w = 800
            current_h = 600

        return InfoObj()

    @staticmethod
    def set_caption(title):
        pass

    @staticmethod
    def flip():
        pass

    @staticmethod
    def toggle_fullscreen():
        return True


class event:
    @staticmethod
    def get():
        return []

