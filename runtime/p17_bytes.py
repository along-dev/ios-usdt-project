import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os

P = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\payloads'
f = os.path.join(P, '1334417664270db20af705f422878c53c8378203', 'entry3_type0x07.bin')
raw = open(f, 'rb').read()
print('文件:', os.path.basename(f))
print('实际大小:', len(raw))
print('hex:')
for i in range(0, len(raw), 16):
    chunk = raw[i:i+16]
    hexs = ' '.join('%02x' % b for b in chunk)
    asci = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print('  %04x  %-47s  %s' % (i, hexs, asci))

print()
print('前 44 字节 hex:', raw[:44].hex())
print('第 45-49 字节 :', raw[44:].hex())
print()
# 对比一个 size 一致的 entry4_type0x07.bin
f2 = os.path.join(P, '1334417664270db20af705f422878c53c8378203', 'entry4_type0x05.bin')
raw2 = open(f2, 'rb').read()
print('对照 entry4_type0x05.bin 大小:', len(raw2))
print('其前 64 字节:')
for i in range(0, min(64, len(raw2)), 16):
    chunk = raw2[i:i+16]
    hexs = ' '.join('%02x' % b for b in chunk)
    asci = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print('  %04x  %-47s  %s' % (i, hexs, asci))
