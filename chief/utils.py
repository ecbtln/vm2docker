__author__ = 'elubin'
import os
import re
import shutil

def recursive_size(path, divisor=1024*1024):
    sizeof = os.path.getsize
    if os.path.isdir(path):
        # walk it
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                if not os.path.islink(full_path):
                    total_size += sizeof(full_path)
        return total_size / divisor
    else:
        return sizeof(path) / divisor


def generate_regexp(iterable):
    options = '|'.join(iterable)
    return re.compile('^(%s)$' % options)


def rm_rf(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def inheritors(klass):
    subclasses = set()
    work = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses


class ringbytearray(bytearray):
    """
    A ring buffer implementation of a bytearray of fixed size
    """

    def __init__(self, capacity):
        super(ringbytearray, self).__init__(capacity)

        # keep track of start and nbytes pointers
        self.start = 0
        self.nbytes = 0
        # NB: end == (self.start + self.nbytes - 1) % size (end is the last written_to byte)!

    @property
    def bytes_empty(self):
        return len(self) - self.nbytes

    @property
    def _contiguous_bytes_free(self):
        """
        The # of bytes we can write to before wrapping around, <= bytes_empty
        """
        if self.end < self.start:
            return len(self) - self.nbytes
        else:
            return len(self) - self.start - self.nbytes

    @property
    def end(self): # this value is kinda garbage when the ring buffer is empty, just keep in mind
        if self.nbytes == 0:
            return self.start # garbage value
        return (self.start + self.nbytes - 1) % len(self)

    # @property
    # def next(self):
    #     pass

    def __translate_idx(self, idx):
        if -self.nbytes <= idx < self.nbytes:
            if idx < 0:
                idx %= self.nbytes
            return (self.start + idx) % len(self)
        else:
            raise IndexError("Index out of range")

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            pass
        elif isinstance(key, int):
            try:
                self[self.__translate_idx(key)] = value
            except IndexError:
                super(ringbytearray, self).__setitem__(key, value)
        else:
            super(ringbytearray, self).__setitem__(key, value)

    def __getitem__(self, item):
        if isinstance(item, slice):
            pass
        elif isinstance(item, int):
            try:
                return self[self.__translate_idx(item)]
            except IndexError:
                super(ringbytearray, self).__getitem__(item)
        else:
            super(ringbytearray, self).__getitem__(item)

    def write_to(self, f, n_bytes):
        """
        Write at most n_bytes to the ring buffer
        f is a function that takes in as argument the buffer and the max bytes to write to it, and returns the actual #
        of bytes written

        returns the # of bytes written to the ringbytearray
        """
        assert n_bytes <= self.bytes_empty
        mem = memoryview(self)[self.end + 1:]
        n_actual_bytes = f(mem, min(n_bytes, self._contiguous_bytes_free))
        self.nbytes += n_actual_bytes
        return n_actual_bytes

    def read(self, n_bytes=None):
        """
        In this case we read and we want exactly n_bytes read (or all the bytes in the buffer) and returned as a new byte array
        The internal start pointer is then advanced and the nbytes counter is decremented
        """
        if n_bytes is None:
            n_bytes = self.nbytes
        else:
            n_bytes = min(self.nbytes, n_bytes)


        n_read = 0
        output = bytearray()
        while n_read != n_bytes:
            mem = memoryview(self)[self.start:min(len(self), self.start + n_bytes)]
            output.extend(mem)
            n = len(mem)
            n_read += n
            self.nbytes -= n
            self.start = (self.start + n) % len(self)


        if self.nbytes == 0:
            # if there are 0 bytes in the ring buffer, reset the pointer to the beginning
            self.start = 0
        return output

    def find(self, sub, start=None, end=None):
        # TODO: still need to implement
        if self.nbytes == 0:
            return -1

        if start is None:
            start = 0
        else:
            start = min(max(0, start), self.nbytes - 1)
        if end is None:
            end = self.nbytes - 1
        else:
            end = max(min(end, self.nbytes - 1), 0)


        # TODO: only search between start and end (obviously), aka ignore garbage bytes
        start = self.__translate_idx(start)
        end = self.__translate_idx(end)

        return super(ringbytearray, self).find(sub, start, end)


    def read_until(self, delimiter):
        """
        Read bytes out of the ring buffer until delimiter is found, which is an arbitrary byte sequence. If the
        delimiter cannot be found, the ring buffer is emptied completely.
        """
        idx = self.find(delimiter)
        if idx == -1:
            return self.read()
        else:
            out = self.read((idx - self.start) % len(self))

            delim = self.read(len(delimiter))
            assert delim == delimiter
            return out





