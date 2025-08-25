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
        self.bottom = y + h

    @property
    def topleft(self):
        return (self.x, self.y)

    @property
    def center(self):
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def size(self):
        return (self.width, self.height)

    @size.setter
    def size(self, value):
        self.width, self.height = value
        self.bottom = self.y + self.height

    @property
    def midtop(self):
        return (self.x + self.width // 2, self.y)

    @midtop.setter
    def midtop(self, pos):
        cx, cy = pos
        self.x = cx - self.width // 2
        self.y = cy
        self.bottom = self.y + self.height

    @property
    def midbottom(self):
        return (self.x + self.width // 2, self.y + self.height)

    @midbottom.setter
    def midbottom(self, pos):
        cx, cy = pos
        self.x = cx - self.width // 2
        self.y = cy - self.height
        self.bottom = self.y + self.height

    def collidepoint(self, pos):
        return False

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

