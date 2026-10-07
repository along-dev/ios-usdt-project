#!/usr/bin/env python3
"""
Minimal WASM interpreter for cx.v57.wasm (i32-only module, MVP subset).
Goal: run exported q(cmd,a,b,c,d,e) and dump memory, to recover the
anti-bot token generation without a browser.
"""
import struct, sys

class Trap(Exception): pass

def leb_u(b, i):
    r=0; s=0
    while True:
        x=b[i]; i+=1; r |= (x & 0x7f) << s; s += 7
        if not (x & 0x80): return r, i

def leb_s(b, i):
    r=0; s=0
    while True:
        x=b[i]; i+=1; r |= (x & 0x7f) << s; s += 7
        if not (x & 0x80):
            if s < 64 and (x & 0x40): r |= -(1 << s)
            return r, i

class Module:
    def __init__(self, data):
        self.data = data
        self.types = []
        self.funcs = []      # list of (typeidx, bodybytes)
        self.imports = []
        self.exports = {}
        self.globals_init = []
        self.data_segments = []
        self._parse()

    def _parse(self):
        d = self.data
        assert d[:4] == b"\x00asm", "not wasm"
        i = 8
        while i < len(d):
            sid = d[i]; i += 1
            size, i = leb_u(d, i)
            end = i + size
            if sid == 1:
                n, i = leb_u(d, i)
                for _ in range(n):
                    assert d[i] == 0x60; i += 1
                    np_, i = leb_u(d, i); params = list(d[i:i+np_]); i += np_
                    nr, i = leb_u(d, i); results = list(d[i:i+nr]); i += nr
                    self.types.append((params, results))
            elif sid == 2:
                n, i = leb_u(d, i)
                for _ in range(n):
                    l, i = leb_u(d, i); mod = d[i:i+l].decode(); i += l
                    l, i = leb_u(d, i); nm = d[i:i+l].decode(); i += l
                    kind = d[i]; i += 1
                    if kind == 0:
                        t, i = leb_u(d, i)
                        self.imports.append((mod, nm, t))
                    elif kind == 1:
                        i += 1
                        fl = d[i]; i += 1
                        if fl: mn, i = leb_u(d, i)
                    elif kind == 2:
                        fl = d[i]; i += 1
                        mn, i = leb_u(d, i)
                        if fl: mx, i = leb_u(d, i)
                    elif kind == 3:
                        i += 2
            elif sid == 3:
                n, i = leb_u(d, i)
                for _ in range(n):
                    t, i = leb_u(d, i)
                    self.funcs.append([t, None])
            elif sid == 6:
                n, i = leb_u(d, i)
                for _ in range(n):
                    vt = d[i]; i += 1
                    mt = d[i]; i += 1
                    if vt in (0x7f,0x7e,0x7d,0x7c,0x7b,0x70,0x6f):
                        v, i = leb_s(d, i)
                    self.globals_init.append(v)
            elif sid == 7:
                n, i = leb_u(d, i)
                for _ in range(n):
                    l, i = leb_u(d, i); nm = d[i:i+l].decode(); i += l
                    kind = d[i]; i += 1
                    idx, i = leb_u(d, i)
                    self.exports[nm] = (kind, idx)
            elif sid == 10:
                n, i = leb_u(d, i)
                for k in range(n):
                    bs, i = leb_u(d, i)
                    self.funcs[k][1] = d[i:i+bs]
                    i += bs
            elif sid == 11:
                n, i = leb_u(d, i)
                for _ in range(n):
                    fl, i = leb_u(d, i)
                    if fl == 0:
                        # offset expr
                        assert d[i] == 0x41; i += 1
                        off, i = leb_s(d, i)
                        assert d[i] == 0x0b; i += 1
                    else:
                        off = None
                    ln, i = leb_u(d, i)
                    seg = d[i:i+ln]; i += ln
                    self.data_segments.append((off, seg))
            i = end
        # memory size
        self.mem_pages = 0
        # find memory import/section for size (from earlier parse: memory min)
        # We know from section dump: memory min will be parsed here
        j = 8
        while j < len(d):
            sid = d[j]; j += 1
            size, j = leb_u(d, j)
            if sid == 5:
                n, j = leb_u(d, j)
                fl = d[j]; j += 1
                mn, j = leb_u(d, j)
                self.mem_pages = mn
            j += size

class Instance:
    def __init__(self, mod, host_log=None):
        self.mod = mod
        self.mem = bytearray(max(mod.mem_pages,1) * 65536)
        # grow memory generously for stack area
        self.mem = bytearray(4096 * 65536)   # 256MB logical
        self.stack = []
        self.globals = list(mod.globals_init) + [0]*8
        self.call_depth = 0
        self.host_log = host_log or (lambda x: None)
        self.steps = 0
        self.max_steps = 200_000_000

    # --- memory helpers ---
    def load(self, addr, nbytes):
        return int.from_bytes(self.mem[addr:addr+nbytes], "little")
    def store(self, addr, val, nbytes):
        self.mem[addr:addr+nbytes] = (val & ((1 << (8*nbytes))-1)).to_bytes(nbytes, "little")

    def invoke(self, fidx, args):
        if fidx < len(self.mod.imports):
            # host import: a.d (log)
            self.host_log(args[0] if args else 0)
            return 0
        local_fidx = fidx - len(self.mod.imports)
        typeidx, body = self.mod.funcs[local_fidx]
        nparams_declared = len(self.mod.types[typeidx][0])
        # JS->WASM calls may pass fewer args; missing ones default to 0
        if len(args) < nparams_declared:
            args = list(args) + [0] * (nparams_declared - len(args))
        return self.exec_body(body, args)

    def exec_body(self, body, args):
        # parse locals declaration
        i = 0
        ng, i = leb_u(body, i)
        locals_types = []
        for _ in range(ng):
            c, i = leb_u(body, i)
            t = body[i]; i += 1
            locals_types += [t]*c
        nparams = len(args)
        locals_ = list(args) + [0]*len(locals_types)
        instrs = self._decode(body, i)
        # Precompute block structure with a proper forward scan using a stack.
        # jumptable[pc] for block/loop/if/else/end -> target pc
        block_info = {}   # start_pc -> dict(end=, else=)
        jumptable = {}
        stack = []
        for idx, ins in enumerate(instrs):
            op = ins[0]
            if op in (0x02, 0x03, 0x04):        # block / loop / if
                stack.append(idx)
                block_info[idx] = {}
            elif op == 0x05:                     # else
                b = stack[-1]
                block_info[b]['else'] = idx
                jumptable[idx] = block_info[b].get('end', len(instrs)-1)  # patched later
            elif op == 0x0b:                     # end
                if stack:
                    b = stack.pop()
                    block_info[b]['end'] = idx
        # patch else jumps now that ends are known
        for b, info in block_info.items():
            if 'else' in info:
                jumptable[info['else']] = info['end']
        # branch targets resolved by depth using block_info
        pc = 0
        stack_vals = []
        n_instr = len(instrs)
        while pc < n_instr:
            self.steps += 1
            if self.steps > self.max_steps:
                raise Trap("step limit")
            ins = instrs[pc]
            op = ins[0]
            cur = pc
            pc += 1
            a = ins[1:]

            if op == 0x0b or op == 0x05:
                # end / else: when reached by fallthrough, else jumps to end;
                # end is a no-op
                if op == 0x05:
                    pc = jumptable[cur]
                continue
            elif op == 0x0c:  # br
                pc = self._branch(cur, a[0], instrs, block_info)
            elif op == 0x0d:  # br_if
                if stack_vals.pop() != 0:
                    pc = self._branch(cur, a[0], instrs, block_info)
            elif op == 0x0e:  # br_table
                tbl, dflt = a[0], a[1]
                v = stack_vals.pop() & 0xffffffff
                d = tbl[v] if v < len(tbl) else dflt
                pc = self._branch(cur, d, instrs, block_info)
            elif op == 0x02 or op == 0x03:  # block / loop
                continue
            elif op == 0x04:  # if
                c = stack_vals.pop()
                if c == 0:
                    info = block_info.get(cur, {})
                    pc = info['else'] + 1 if 'else' in info else info['end'] + 1
            elif op == 0x0f:  # return
                return stack_vals.pop() if stack_vals else 0
            elif op == 0x10:  # call
                fidx = a[0]
                if fidx < len(self.mod.imports):
                    ntp = self.mod.imports[fidx][2]
                else:
                    ntp = self.mod.funcs[fidx - len(self.mod.imports)][0]
                nparams_ = len(self.mod.types[ntp][0])
                cargs = [stack_vals.pop() for _ in range(nparams_)][::-1]
                r = self.invoke(fidx, cargs)
                if self.mod.types[ntp][1]:
                    stack_vals.append(r)
            elif op == 0x1a:  # drop
                stack_vals.pop()
            elif op == 0x1b:  # select
                c = stack_vals.pop(); b2 = stack_vals.pop(); a2 = stack_vals.pop()
                stack_vals.append(a2 if c != 0 else b2)
            elif op == 0x20:
                stack_vals.append(locals_[a[0]])
            elif op == 0x21:
                locals_[a[0]] = stack_vals.pop()
            elif op == 0x22:
                locals_[a[0]] = stack_vals[-1]
            elif op == 0x23:
                stack_vals.append(self.globals[a[0]])
            elif op == 0x24:
                self.globals[a[0]] = stack_vals.pop()
            elif op in (0x28,0x29,0x2a,0x2b,0x2c,0x2d,0x2e,0x2f,0x30,0x31,0x32,0x33,0x34,0x35):
                offset = a[1]
                base = stack_vals.pop()
                addr = (base + offset) & 0xffffffff
                nb = {0x28:4,0x29:8,0x2a:4,0x2b:8,0x2c:1,0x2d:1,0x2e:2,0x2f:2,
                      0x30:1,0x31:1,0x32:2,0x33:2,0x34:4,0x35:4}[op]
                v = self.load(addr, nb)
                if op in (0x2c,0x2e,0x30,0x32,0x34):
                    if v & (1 << (8*nb-1)): v -= (1 << (8*nb))
                stack_vals.append(v)
            elif op in (0x36,0x37,0x38,0x39,0x3a,0x3b,0x3c,0x3d,0x3e):
                offset = a[1]
                v = stack_vals.pop(); base = stack_vals.pop()
                nb = {0x36:4,0x37:8,0x38:4,0x39:8,0x3a:1,0x3b:2,0x3c:1,0x3d:2,0x3e:4}[op]
                self.store((base+offset)&0xffffffff, v, nb)
            elif op == 0x3f:
                stack_vals.append(len(self.mem)//65536)
            elif op == 0x40:
                n = stack_vals.pop(); stack_vals.append(0)
            elif op == 0x41:
                stack_vals.append(a[0])
            elif op == 0x42:
                stack_vals.append(a[0])
            elif op == 0x45:
                stack_vals.append(1 if stack_vals.pop()==0 else 0)
            elif op == 0x46:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(1 if a2==b2 else 0)
            elif op == 0x47:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(1 if a2!=b2 else 0)
            elif op == 0x48:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(1 if a2<b2 else 0)
            elif op == 0x49:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(1 if (a2&0xffffffff)<(b2&0xffffffff) else 0)
            elif op == 0x4a:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(1 if a2>b2 else 0)
            elif op == 0x4b:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(1 if (a2&0xffffffff)>(b2&0xffffffff) else 0)
            elif op == 0x4c:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(1 if a2<=b2 else 0)
            elif op == 0x4d:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(1 if (a2&0xffffffff)<=(b2&0xffffffff) else 0)
            elif op == 0x4e:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(1 if a2>=b2 else 0)
            elif op == 0x4f:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(1 if (a2&0xffffffff)>=(b2&0xffffffff) else 0)
            elif op == 0x67:
                v=stack_vals.pop()&0xffffffff; stack_vals.append(32 if v==0 else (32 - v.bit_length()))
            elif op == 0x68:
                v=stack_vals.pop()&0xffffffff; stack_vals.append(32 if v==0 else (v & -v).bit_length()-1)
            elif op == 0x69:
                stack_vals.append(bin(stack_vals.pop()&0xffffffff).count("1"))
            elif op == 0x6a:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append((a2+b2)&0xffffffff)
            elif op == 0x6b:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append((a2-b2)&0xffffffff)
            elif op == 0x6c:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append((a2*b2)&0xffffffff)
            elif op == 0x6d:
                b2=stack_vals.pop(); a2=stack_vals.pop()
                if b2 == 0: stack_vals.append(0)
                else:
                    x = a2 - (1<<32) if a2 & 0x80000000 else a2
                    y = b2 - (1<<32) if b2 & 0x80000000 else b2
                    q_ = abs(x)//abs(y); stack_vals.append((-q_ if (x<0)!=(y<0) else q_) & 0xffffffff)
            elif op == 0x6e:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append((a2&0xffffffff)//(b2&0xffffffff) if b2 else 0)
            elif op == 0x6f:
                b2=stack_vals.pop(); a2=stack_vals.pop()
                if b2 == 0: stack_vals.append(0)
                else:
                    x = a2 - (1<<32) if a2 & 0x80000000 else a2
                    y = b2 - (1<<32) if b2 & 0x80000000 else b2
                    r = abs(x)%abs(y); stack_vals.append((-r if x<0 else r) & 0xffffffff)
            elif op == 0x70:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append((a2&0xffffffff)%(b2&0xffffffff) if b2 else 0)
            elif op == 0x71:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(a2&b2)
            elif op == 0x72:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(a2|b2)
            elif op == 0x73:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append(a2^b2)
            elif op == 0x74:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append((a2<<(b2&31))&0xffffffff)
            elif op == 0x75:
                b2=stack_vals.pop(); a2=stack_vals.pop()
                a2 = a2 - (1<<32) if a2 & 0x80000000 else a2
                stack_vals.append((a2>>(b2&31))&0xffffffff)
            elif op == 0x76:
                b2=stack_vals.pop(); a2=stack_vals.pop(); stack_vals.append((a2&0xffffffff)>>(b2&31))
            elif op == 0x77:
                b2=stack_vals.pop(); a2=stack_vals.pop(); n=b2&31
                stack_vals.append((((a2<<n)|(a2>>(32-n)))&0xffffffff) if n else a2)
            elif op == 0x78:
                b2=stack_vals.pop(); a2=stack_vals.pop(); n=b2&31
                stack_vals.append((((a2>>n)|(a2<<(32-n)))&0xffffffff) if n else a2)
            elif op == 0xa7:
                stack_vals.append(stack_vals.pop()&0xffffffff)
            elif op == 0xc0:
                v=stack_vals.pop()&0xff; stack_vals.append(v-256 if v&0x80 else v)
            elif op == 0xc1:
                v=stack_vals.pop()&0xffff; stack_vals.append(v-65536 if v&0x8000 else v)
            elif op == 0x00:
                raise Trap("unreachable")
            elif op == 0x01:
                pass
            else:
                raise Trap(f"unhandled opcode 0x{op:02x} at pc={cur}")
        return stack_vals.pop() if stack_vals else 0

    def _branch(self, cur, depth, instrs, block_info):
        """Resolve branch to label `depth` from instruction index `cur`.
        Scan backwards; each `end` means we skip over one already-closed
        inner construct (depth_remaining += 1). Each block/loop/if we pass
        with depth_remaining == 0 is the label we want.
        """
        remaining = depth
        i = cur
        while i >= 0:
            op = instrs[i][0]
            if op == 0x0b:                     # end: skip an inner scope
                remaining += 1
            elif op in (0x02, 0x03, 0x04):     # block / loop / if
                if remaining == 0:
                    if op == 0x03:             # loop -> header (after the op)
                        return i + 1
                    return block_info[i]['end'] + 1
                remaining -= 1
            i -= 1
        return len(instrs)

    def _decode(self, body, i):
        instrs = []
        n = len(body)
        while i < n:
            op = body[i]; i += 1
            entry = [op]
            if op in (0x28,0x29,0x2a,0x2b,0x2c,0x2d,0x2e,0x2f,0x30,0x31,0x32,0x33,0x34,0x35,
                      0x36,0x37,0x38,0x39,0x3a,0x3b,0x3c,0x3d,0x3e):
                al, i = leb_u(body, i); off, i = leb_u(body, i)
                entry += [al, off]
            elif op in (0x41,0x42):
                v, i = leb_s(body, i); entry.append(v)
            elif op == 0x43:
                entry.append(struct.unpack("<f", body[i:i+4])[0]); i += 4
            elif op == 0x44:
                entry.append(struct.unpack("<d", body[i:i+8])[0]); i += 8
            elif op == 0x10:
                x, i = leb_u(body, i); entry.append(x)
            elif op == 0x11:
                x, i = leb_u(body, i); t, i = leb_u(body, i); entry += [x, t]
            elif op in (0x0c,0x0d):
                x, i = leb_u(body, i); entry.append(x)
            elif op == 0x0e:
                c, i = leb_u(body, i)
                tbl = []
                for _ in range(c):
                    v, i = leb_u(body, i); tbl.append(v)
                dflt, i = leb_u(body, i)
                entry += [tbl, dflt]
            elif op in (0x20,0x21,0x22,0x23,0x24,0xd2):
                x, i = leb_u(body, i); entry.append(x)
            elif op in (0x02,0x03,0x04):
                # blocktype
                if body[i] == 0x40:
                    entry.append(None); i += 1
                elif body[i] in (0x7f,0x7e,0x7d,0x7c):
                    entry.append(body[i]); i += 1
                else:
                    t, i = leb_s(body, i); entry.append(t)
            elif op == 0x1c:
                c, i = leb_u(body, i); ts = []
                for _ in range(c):
                    ts.append(body[i]); i += 1
                entry.append(ts)
            elif op in (0x3f,0x40):
                entry.append(body[i]); i += 1
            elif op == 0xd0:
                entry.append(body[i]); i += 1
            instrs.append(entry)
        return instrs


def load_module(path):
    return Module(open(path,"rb").read())

if __name__ == "__main__":
    m = load_module(sys.argv[1] if len(sys.argv)>1 else r"E:\IOSusdt\cx_decoded.wasm")
    print("types:", m.types)
    print("imports:", m.imports)
    print("funcs:", [ (f[0], len(f[1]) if f[1] else 0) for f in m.funcs ])
    print("exports:", m.exports)
    print("mem_pages:", m.mem_pages)
    print("globals_init:", m.globals_init)
    print("data_segments:", [(o, len(s)) for o,s in m.data_segments])
    inst = Instance(m, host_log=lambda x: None)
    for o, seg in m.data_segments:
        if o is not None:
            inst.mem[o:o+len(seg)] = seg
            print(f"applied data seg at {o} len {len(seg)}: {seg[:80]}")
    q = m.exports["q"][1]
    print("q func index:", q)
