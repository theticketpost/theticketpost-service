from loguru import logger

# Print density (heat), 1 (light) to 4 (darkest). Dark prints draw more current:
# on a full black line the paper motor can skip steps and squash what follows.
DEFAULT_DENSITY = 3


def cmd_header(density=DEFAULT_DENSITY):
    # 0x1b 0x40      -> command ESC @: initialize printer
    # 0x1b 0x61      -> command ESC a: select justification
    # 0x01           range: 0 (left-justification), 1 centered,
    #                    2 (right justification)
    # 0x1f 0x11 0x02 -> density (Phomemo), 0x01 to 0x04
    density = min(4, max(1, int(density)))
    return  b'\x1b\x40'\
            b'\x1b\x61'\
            b'\x01'\
            b'\x1f\x11\x02' + density.to_bytes(1, 'little')


def cmd_footer():
    # 0x1b 0x64      -> command ESC d : print and feed n lines
    # 0x02           number of line to feed
    # 0x1b 0x64      -> command ESC d : print and feed n lines
    # 0x02           number of line to feed
    # 0x1f 0x11 0x08
    # 0x1f 0x11 0x0e
    # 0x1f 0x11 0x07
    # 0x1f 0x11 0x09
    return  b'\x1b\x64\x02'\
            b'\x1b\x64\x02'\
            b'\x1f\x11\x08'\
            b'\x1f\x11\x0e'\
            b'\x1f\x11\x07'\
            b'\x1f\x11\x09'


def cmd_marker(lines, width):
    # 0x1d 0x76 0x30 -> command GS v 0 : print raster bit image
    # 0x00              mode: 0 (normal), 1 (double width),
    #                   2 (double-height), 3 (quadruple)
    # 0x30 0x00         16bit, little-endian: number of bytes / line (48)
    # 0x00 0x01         16bit, little-endian: number of lines in the image (256)
    # Exactly the lines that follow: it used to say one less, and the printer
    # read the last line of every 256 as commands. Depending on the drawing,
    # those bytes fed paper or threw away what it hadn't printed yet.
    return b'\x1d\x76\x30\x00'+(int(width / 8)).to_bytes(2, 'little')+lines.to_bytes(2, 'little')


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


def cmds_print_img(image, density=DEFAULT_DENSITY):
    remaining = image.height
    line=0
    data = cmd_header(density)
    while remaining > 0:
        lines = remaining
        if lines > 256:
            lines = 256
        data += cmd_marker(lines, image.width)
        remaining -= lines
        while lines > 0:
            data += cmd_line(image, line)
            lines -= 1
            line += 1
    data += cmd_footer()

    return data
