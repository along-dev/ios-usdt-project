/**
 * Fat Binary (Universal Binary) 解析
 */
/**
 * 解析 Fat/Universal binary header
 * @returns 架构列表，如果不是 fat binary 返回 null
 */
export function parseFatHeader(buf) {
    const magic = buf.readUInt32BE(0);
    if (magic !== 0xCAFEBABE)
        return null;
    const narch = buf.readUInt32BE(4);
    const arches = [];
    for (let i = 0; i < narch; i++) {
        const off = 8 + i * 20;
        arches.push({
            cputype: buf.readUInt32BE(off),
            cpusubtype: buf.readUInt32BE(off + 4),
            offset: buf.readUInt32BE(off + 8),
            size: buf.readUInt32BE(off + 12),
            align: buf.readUInt32BE(off + 16),
        });
    }
    return arches;
}
/**
 * 在 buffer 中搜索 pattern 所有出现位置
 */
export function findAllOccurrences(buf, pattern) {
    const results = [];
    const patBuf = Buffer.from(pattern, 'ascii');
    let pos = 0;
    while (pos < buf.length) {
        const idx = buf.indexOf(patBuf, pos);
        if (idx === -1)
            break;
        results.push(idx);
        pos = idx + 1;
    }
    return results;
}
/**
 * 查找 Mach-O 64-bit section
 */
export function findSection(buf, segname, sectname) {
    const magic = buf.readUInt32LE(0);
    if (magic !== 0xFEEDFACF)
        return null;
    const ncmds = buf.readUInt32LE(16);
    let offset = 32; // sizeof(mach_header_64)
    for (let i = 0; i < ncmds; i++) {
        const cmd = buf.readUInt32LE(offset);
        const cmdsize = buf.readUInt32LE(offset + 4);
        if (cmd === 0x19) { // LC_SEGMENT_64
            const name = buf.toString('ascii', offset + 8, offset + 24).replace(/\0/g, '');
            if (name === segname) {
                const nsects = buf.readUInt32LE(offset + 64);
                let sectOff = offset + 72;
                for (let j = 0; j < nsects; j++) {
                    const sname = buf.toString('ascii', sectOff, sectOff + 16).replace(/\0/g, '');
                    if (sname === sectname) {
                        const size = Number(buf.readBigUInt64LE(sectOff + 40));
                        const fileOffset = buf.readUInt32LE(sectOff + 48);
                        return { size, offset: fileOffset };
                    }
                    sectOff += 80;
                }
            }
        }
        offset += cmdsize;
    }
    return null;
}
//# sourceMappingURL=fat-binary.js.map