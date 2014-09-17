__author__ = 'elubin'


import unittest
from chief.utils.ringbuffer import ringbuffer


def g(start):
    def f(b, n):
        for x in range(n):
            b[x] = chr(x+start)
        return n
    return f

class RingBufferTest(unittest.TestCase):
    def test_read(self):
        buffer = ringbuffer(10)
        buffer.write_to(g(0))
        self.assertEqual(buffer.find('\x00'), 0)
        self.assertEqual(buffer.find('\x09'), 9)
        self.assertEqual(buffer.find('\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09'), 0)
        self.assertEqual(buffer.find('\x10'), -1)
        self.assertEqual(buffer.find('\x00', 1), -1)
        self.assertEqual(buffer.find('\x09', 0, 9), -1)
        bytes = buffer.read(4)
        self.assertEqual(str(bytes), '\x00\x01\x02\x03')
        buffer.write_to(g(16))
        self.assertEqual(str(buffer), '\x10\x11\x12\x13\x04\x05\x06\x07\x08\x09')
        self.assertEqual(buffer.find('\x04\x05'), 0)
        self.assertEqual(buffer.find('\x10'), 6)
        self.assertEqual(buffer.find('\x09\x10'), 5)
        self.assertEqual(buffer.find('\x08\x09\x10\x11'), 4)
        self.assertEqual(buffer.find('\x08\x09\x10\x11', 4), 4)
        self.assertEqual(buffer.find('\x08\x09\x10\x11', 5), -1)
        self.assertEqual(buffer.find('\x08\x09\x10\x11', 4, 7), -1)
        bytes, res = buffer.read_until('\x10')
        self.assertEqual(res, True)
        self.assertEqual(bytes, '\x04\x05\x06\x07\x08\x09')



        bytes, res = buffer.read_until('\x00')
        self.assertEqual(res, False)
        self.assertEqual(bytes, '\x11\x12\x13')
        self.assertEqual(buffer.start, 0)
        self.assertEqual(buffer.nbytes, 0)


if __name__ == '__main__':
    unittest.main()