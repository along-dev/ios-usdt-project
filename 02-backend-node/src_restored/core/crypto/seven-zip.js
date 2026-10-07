import Seven from 'node-7z';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { mkdir, writeFile, readFile, unlink, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { C2_CONSTANTS } from '../../config/constants.js';
import { logger } from '../logger/index.js';
// 优先用系统 7z/7za（Docker Alpine 的包名是 7z），fallback 到 7zip-bin（macOS 开发环境）
let sevenBin;
try {
    execFileSync('7z', ['--help'], { stdio: 'ignore' });
    sevenBin = '7z';
}
catch {
    try {
        execFileSync('7za', ['--help'], { stdio: 'ignore' });
        sevenBin = '7za';
    }
    catch {
        const sevenBinModule = await import('7zip-bin');
        sevenBin = sevenBinModule.default?.path7za ?? sevenBinModule.path7za;
    }
}
export class PayloadCrypto {
    static async encrypt(inputPath, outputPath) {
        const outputDir = path.dirname(outputPath);
        await mkdir(outputDir, { recursive: true });
        logger.info({ input: path.basename(inputPath), output: path.basename(outputPath) }, '7z encrypt start');
        return new Promise((resolve, reject) => {
            const stream = Seven.add(outputPath, inputPath, {
                $bin: sevenBin,
                password: C2_CONSTANTS.SEVEN_ZIP_PASSWORD,
                method: ['x=9', 'he=on'],
            });
            stream.on('end', () => {
                logger.info({ output: path.basename(outputPath) }, '7z encrypt done');
                resolve();
            });
            stream.on('error', (err) => {
                logger.error({ err, inputPath, outputPath }, '7z encrypt failed');
                reject(err);
            });
        });
    }
    static async encryptBuffer(data, outputPath) {
        const outputDir = path.dirname(outputPath);
        await mkdir(outputDir, { recursive: true });
        const tmpDir = await mkdtemp(path.join(tmpdir(), 'payload-enc-'));
        const tmpPath = path.join(tmpDir, path.basename(outputPath, '.js') + '.dylib');
        try {
            await writeFile(tmpPath, data);
            await PayloadCrypto.encrypt(tmpPath, outputPath);
        }
        finally {
            await unlink(tmpPath).catch(() => { });
            await rm(tmpDir, { recursive: true }).catch(() => { });
        }
    }
    /**
     * 对内存 Buffer 做 7zip 加密，返回加密后的 Buffer
     * 用于 config endpoint 等需要返回加密响应体的场景
     */
    static async packBuffer(data) {
        const tmpDir = await mkdtemp(path.join(tmpdir(), 'pack-'));
        const inputPath = path.join(tmpDir, 'data.bin');
        const outputPath = path.join(tmpDir, 'data.7z');
        try {
            await writeFile(inputPath, data);
            await PayloadCrypto.encrypt(inputPath, outputPath);
            return await readFile(outputPath);
        }
        finally {
            await rm(tmpDir, { recursive: true }).catch(() => { });
        }
    }
    static async decrypt(archivePath, outputDir) {
        await mkdir(outputDir, { recursive: true });
        logger.info({ archive: path.basename(archivePath) }, '7z decrypt start');
        return new Promise((resolve, reject) => {
            const stream = Seven.extractFull(archivePath, outputDir, {
                $bin: sevenBin,
                password: C2_CONSTANTS.SEVEN_ZIP_PASSWORD,
            });
            stream.on('end', () => {
                logger.info({ archive: path.basename(archivePath) }, '7z decrypt done');
                resolve();
            });
            stream.on('error', (err) => {
                logger.error({ err, archivePath, outputDir }, '7z decrypt failed');
                reject(err);
            });
        });
    }
}
//# sourceMappingURL=seven-zip.js.map