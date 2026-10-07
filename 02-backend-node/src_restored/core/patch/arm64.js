/**
 * ARM64 指令编码工具
 */
export function arm64_stp_pre(rt1, rt2, rn, imm7) {
    const simm7 = ((imm7 / 8) & 0x7F) >>> 0;
    return ((0b1010100110 << 22) | (simm7 << 15) | (rt2 << 10) | (rn << 5) | rt1) >>> 0;
}
export function arm64_ldp_post(rt1, rt2, rn, imm7) {
    const simm7 = ((imm7 / 8) & 0x7F) >>> 0;
    return ((0b1010100011 << 22) | (simm7 << 15) | (rt2 << 10) | (rn << 5) | rt1) >>> 0;
}
export function arm64_movz(rd, imm16, shift, sf) {
    const hw = shift / 16;
    return ((sf << 31) | (0b10100101 << 23) | (hw << 21) | (imm16 << 5) | rd) >>> 0;
}
export function arm64_movk(rd, imm16, shift, sf) {
    const hw = shift / 16;
    return ((sf << 31) | (0b11100101 << 23) | (hw << 21) | (imm16 << 5) | rd) >>> 0;
}
export function arm64_mov_reg(rd, rm, sf) {
    const rn = 31; // XZR
    return ((sf << 31) | (0b0101010000 << 21) | (rm << 16) | (0 << 10) | (rn << 5) | rd) >>> 0;
}
export function arm64_svc(imm16) {
    return ((0b11010100000 << 21) | (imm16 << 5) | 0b00001) >>> 0;
}
export function arm64_b(offsetBytes) {
    const imm26 = (offsetBytes >> 2) & 0x3FFFFFF;
    return ((0b000101 << 26) | imm26) >>> 0;
}
export function arm64_b_cond(offsetBytes, cond) {
    const imm19 = (offsetBytes >> 2) & 0x7FFFF;
    return ((0b01010100 << 24) | (imm19 << 5) | cond) >>> 0;
}
export function arm64_cbnz(rt, offsetBytes, sf) {
    const imm19 = (offsetBytes >> 2) & 0x7FFFF;
    return ((sf << 31) | (0b0110101 << 24) | (imm19 << 5) | rt) >>> 0;
}
export function arm64_tbnz(rt, bit, offsetBytes) {
    const b5 = (bit >> 5) & 1;
    const b40 = bit & 0x1F;
    const imm14 = (offsetBytes >> 2) & 0x3FFF;
    return ((b5 << 31) | (0b0110111 << 24) | (b40 << 19) | (imm14 << 5) | rt) >>> 0;
}
export function arm64_subs_imm(rd, rn, imm12, sf) {
    return ((sf << 31) | (0b1110001 << 24) | (0 << 22) | (imm12 << 10) | (rn << 5) | rd) >>> 0;
}
export function arm64_sub_imm(rd, rn, imm12, sf) {
    return ((sf << 31) | (0b1010001 << 24) | (0 << 22) | (imm12 << 10) | (rn << 5) | rd) >>> 0;
}
export function arm64_add_imm(rd, rn, imm12, sf) {
    return ((sf << 31) | (0b0010001 << 24) | (0 << 22) | (imm12 << 10) | (rn << 5) | rd) >>> 0;
}
export function arm64_str_imm(rt, rn, imm12, size) {
    const scaledImm = imm12 / (1 << size);
    return ((size << 30) | (0b111001 << 24) | (0b00 << 22) | (scaledImm << 10) | (rn << 5) | rt) >>> 0;
}
export function arm64_adr(rd, offsetBytes) {
    const immlo = offsetBytes & 0x3;
    const immhi = (offsetBytes >> 2) & 0x7FFFF;
    return ((0 << 31) | (immlo << 29) | (0b10000 << 24) | (immhi << 5) | rd) >>> 0;
}
export function arm64_nop() {
    return 0xD503201F;
}
export function arm64_ret() {
    return 0xD65F03C0;
}
/** 将字符串写入 buffer 并返回 4 字节对齐后的长度 */
export function writeStringAligned(buf, offset, str) {
    const strBuf = Buffer.from(str + '\0', 'ascii');
    strBuf.copy(buf, offset);
    const aligned = Math.ceil(strBuf.length / 4) * 4;
    for (let i = strBuf.length; i < aligned; i++) {
        buf[offset + i] = 0;
    }
    return aligned;
}
//# sourceMappingURL=arm64.js.map