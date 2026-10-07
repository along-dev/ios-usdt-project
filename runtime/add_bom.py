import sys, os

def add_bom(path):
    """给 UTF-8 文本文件补 BOM（若无）。安全：先读入内存，再整体写回。"""
    with open(path, 'rb') as f:
        raw = f.read()
    if not raw:
        raise SystemExit('EMPTY FILE, refuse: ' + path)
    if raw[:3] == b'\xef\xbb\xbf':
        print('ALREADY_BOM: %s (size=%d)' % (path, len(raw)))
        return
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + raw)
    with open(path, 'rb') as f:
        chk = f.read()
    assert chk[:3] == b'\xef\xbb\xbf' and len(chk) == len(raw) + 3, 'BOM write verify failed'
    print('BOM_ADDED: %s (size=%d -> %d)' % (path, len(raw), len(chk)))

if __name__ == '__main__':
    for p in sys.argv[1:]:
        add_bom(p)
