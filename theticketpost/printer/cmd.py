from loguru import logger

PRINT_WIDTH = 384

#bytearray

def cmd_header():
    #ESC @: initialize printer
    #ESC a: select justification
    # 1: centered
    return  b'\x1b\x40'\
            b'\x1b\x61'\
            b'\x01'\
            b'\x1f\x11\x02\x04'


def cmd_footer():
    return  b'\x1b\x64\x02'\
            b'\x1b\x64\x02'\
            b'\x1f\x11\x08'\
            b'\x1f\x11\x0e'\
            b'\x1f\x11\x07'\
            b'\x1f\x11\x09'


def cmd_marker(lines=0x100):
    return b'\x1d\x76\x30\x00\x30\x00'+(lines - 1).to_bytes(2, 'little')


def cmd_line(image, line):

    data = bytearray()

    for x in range(int(image.width / 8)):
        byte = 0
        for bit in range(8):
            if image.getpixel((x*8 + bit, line)) == 0:
                byte |= 1 << (7 - bit)

        # 0x0a breaks the rendering
        # 0x0a alone is processed like LineFeed by the printe
        if byte == 0x0a:
            byte = 0x14
        data += byte.to_bytes(1, 'little')

    return data


def cmds_print_img(image):
    remaining = image.height
    line=0
    data = cmd_header()
    while remaining > 0:
        lines = remaining
        if lines > 256:
            lines = 256
        data += cmd_marker(lines)
        remaining -= lines
        while lines > 0:
            data += cmd_line(image, line)
            lines -= 1
            line += 1
    data += cmd_footer()

    return data
