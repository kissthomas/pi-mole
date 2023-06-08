class Pager(object):
    def __init__(self, width=16, height=2, pages=2):
        self.width: int = width
        self.height: int = height
        self.pages: int = pages
        self._active_page: int = 0
        self._buffer = [[" ".ljust(width) for i in range(height)] for j in range(pages)]

    def get_line(self, page: int, line: int):
        if page < self.pages and line < self.height:
            return self._buffer[page][line]

    def get_page(self, page: int):
        if page < self.pages:
            return self._buffer[page]

    def get_active_page(self):
        return self._buffer[self._active_page]

    def set_line(self, page: int, line: int, string: str):
        if page < self.pages and line < self.height:
            self._buffer[page][line] = string.ljust(self.width)

    def set_page(self, page: int, data):
        if page < self.pages:
            self._buffer[page] = data

    def set_active_page(self, page: int):
        if page < self.pages:
            self._active_page = page

    def next_page(self):
        if self._active_page < self.pages - 1:
            self._active_page += 1
        else:
            self._active_page = 0
