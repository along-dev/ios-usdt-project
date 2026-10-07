"""
解析 entry3_type0x07.bin 的内部结构，判断 44 还是 49 才是正确的 size。

观察到的字节：
    0f d0 ad de                      magic (LE 0x0FD0ADDE)
    00 00 00 00
    80 51 01 00                      ? 0x00015180 = 86400
    d0 07 00 00                      0x000007d0 = 2000
    01 00 00 00
    01 00 00 00
    02 00 00 00
    24 00 00 00                      0x24 = 36
    0c 00 00 00                      0x0c = 12   ← 字符串长度前缀
    53 70 72 69 6e 67 42 6f 61 72 64  "SpringBoard" (11 bytes)
    00                                NUL 终止 → 共 12 字节
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, struct

P = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\payloads'
f = os.path.join(P, '1334417664270db20af705f422878c53c8378203', 'entry3_type0x07.bin')
raw = open(f, 'rb').read()

print('文件大小:', len(raw))
print()
print('=== 按 uint32 LE 解字段 ===')
for i in range(0, 44, 4):
    v = struct.unpack_from('<I', raw, i)[0]
    print('  offset %2d (0x%02x): 0x%08x  = %d' % (i, i, v, v))

print()
print('=== 字符串段 ===')
slen = struct.unpack_from('<I', raw, 0x20)[0]   # 0x24 之前那个 0x0c
print('  offset 0x20 = %d (字符串长度前缀)' % slen)
name = raw[0x24:0x24 + slen]
print('  offset 0x24 起 %d 字节: %r' % (slen, name))
print()
print('  0x24 + %d = 0x%02x = %d' % (slen, 0x24 + slen, 0x24 + slen))
print('  文件实际大小 = %d' % len(raw))
print()
if len(raw) == 0x24 + slen:
    print('  → 结构自洽：头部 36 字节 + 字符串 %d 字节 = %d，与磁盘 %d 一致'
          % (slen, 0x24 + slen, len(raw)))
    print('  → 但 manifest 写 44。差 %d 字节。' % (44 - len(raw)))
elif len(raw) == 0x24 + slen + 1:
    print('  → 结构 = 头部36 + 字符串%d + 1 个 NUL 终止符 = %d，与磁盘一致' % (slen, len(raw)))
print()
print('=== 44 是什么位置 ===')
print('  0x24 = 36 (头部长度)')
print('  36 + 12 = 48')
print('  44 = 36 + 8 → 只额外算 8 字节，字符串 "SpringBoard" 是 11 字节')
print('  → 44 无法由任何自然字段组合得到，判定为【错误值】')
