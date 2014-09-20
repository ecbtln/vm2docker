class ringbuffer(bytearray):
    """
    A ring buffer implementation of a bytearray of fixed size
    """

    def __init__(self, capacity):
        super(ringbuffer, self).__init__(capacity)

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
        if self.end < self.start or self.end == len(self) - 1:
            return len(self) - self.nbytes
        else:
            return len(self) - self.start - self.nbytes

    @property
    def end(self): # this value is kinda garbage when the ring buffer is empty, just keep in mind
        if self.nbytes == 0:
            return -1 # garbage value
        return (self.start + self.nbytes - 1) % len(self)

    # @property
    # def next(self):
    #     pass

    def __translate_idx(self, idx):
        # translate from 0 to n - 1 to the actual index in the ringbuffer

        if -self.nbytes <= idx < self.nbytes:
            if idx < 0:
                idx %= self.nbytes
            return (self.start + idx) % len(self)
        else:
            raise IndexError("Index out of range")

    def __translate_back_idx(self, idx):
        # translate from the idx in the bytearray to the index in the ringbuffer
        return (idx - self.start) % len(self)

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            pass
        elif isinstance(key, int):
            try:
                self[self.__translate_idx(key)] = value
            except IndexError:
                super(ringbuffer, self).__setitem__(key, value)
        else:
            super(ringbuffer, self).__setitem__(key, value)

    def __getitem__(self, item):
        if isinstance(item, slice):
            pass
        elif isinstance(item, int):
            try:
                return self[self.__translate_idx(item)]
            except IndexError:
                super(ringbuffer, self).__getitem__(item)
        else:
            super(ringbuffer, self).__getitem__(item)

    def write_to(self, f, n_bytes=None):
        """
        Write at most n_bytes to the ring buffer
        f is a function that takes in as argument the buffer and the max bytes to write to it, and returns the actual #
        of bytes written

        returns the # of bytes written to the ringbytearray
        """
        if n_bytes is None:
            n_bytes = self.bytes_empty
        else:
            n_bytes = min(self.bytes_empty, n_bytes)
        end = self.end
        start = (end + 1) % len(self)
        mem = memoryview(self)[start:]
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
        if len(sub) == 0:
            return -1

        # TODO: still need to implement
        if self.nbytes == 0:
            return -1

        if start is None:
            start = 0
        else:
            start = min(max(0, start), self.nbytes - 1)
        if end is None:
            end = self.nbytes
        else:
            end = max(min(end, self.nbytes), 0)

        new_start = self.__translate_idx(start)
        new_end = self.__translate_idx(end - 1) + 1


        # first try the first half
        res = super(ringbuffer, self).find(sub, new_start, min(new_start + end, len(self)))
        if res != -1:
            return self.__translate_back_idx(res)
        else:
            # no luck
            # check if we should be wrapping around
            if new_end <= new_start:
                # try the boarder, then the other half

                if len(sub) > 1:
                    n = len(sub)
                    # need to do some special stuff
                    # take the last n - 1 bytes and the first n - 1 bytes, where n is the length of the delimeter
                    search_target = bytearray()
                    tail = memoryview(self)[max(new_start, len(self) - n + 1):]
                    cap = memoryview(self)[:min(new_end, n - 1)]
                    search_target.extend(tail)
                    search_target.extend(cap)
                    res = search_target.find(sub)
                    if res != -1:
                        # translate this idx back
                        if new_start > len(self) - n + 1:
                            return self.__translate_back_idx(new_start + res)
                        else:
                            return self.__translate_back_idx(len(self) - n + 1 + res)

                # now try the other half
                res = super(ringbuffer, self).find(sub, 0, new_end)
                if res != -1:
                    return self.__translate_back_idx(res)
                else:
                    return -1
            else:
                return -1

    def read_until(self, delimiter):
        """
        Read bytes out of the ring buffer until delimiter is found, which is an arbitrary byte sequence. If the
        delimiter cannot be found, the ring buffer is emptied completely.
        """
        idx = self.find(delimiter)
        if idx == -1:
            return self.read(), False
        else:
            out = self.read(idx)

            delim = self.read(len(delimiter))
            assert delim == delimiter
            return out, True





