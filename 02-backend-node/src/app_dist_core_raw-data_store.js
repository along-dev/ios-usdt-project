import { createHash } from 'node:crypto';
import { mkdir, readFile, rename, unlink, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { gzip as gzipCb, gunzip as gunzipCb } from 'node:zlib';
import { promisify } from 'node:util';
const gzip = promisify(gzipCb);
const gunzip = promisify(gunzipCb);
export function buildRawDataRef(type, docId) {
    const digest = createHash('sha256').update(docId).digest('hex');
    return path.posix.join('raw-data', type, digest.slice(0, 2), digest.slice(2, 4), `${docId}.json.gz`);
}
function resolveStoragePath(storageRoot, rawDataRef) {
    const root = path.resolve(storageRoot);
    const absolutePath = path.resolve(root, rawDataRef);
    if (absolutePath !== root && !absolutePath.startsWith(root + path.sep)) {
        throw new Error('Invalid rawDataRef');
    }
    return absolutePath;
}
export async function writeRawData(storageRoot, type, docId, rawData) {
    const text = JSON.stringify(rawData || {});
    const rawDataHash = createHash('sha256').update(text).digest('hex');
    const gzipped = await gzip(text);
    const rawDataRef = buildRawDataRef(type, docId);
    const absolutePath = resolveStoragePath(storageRoot, rawDataRef);
    const tmpPath = `${absolutePath}.tmp-${process.pid}-${Date.now()}`;
    await mkdir(path.dirname(absolutePath), { recursive: true });
    await writeFile(tmpPath, gzipped);
    await rename(tmpPath, absolutePath);
    return {
        rawDataRef,
        rawDataSize: Buffer.byteLength(text),
        rawDataGzipSize: gzipped.length,
        rawDataHash,
        rawDataEncoding: 'json.gz',
    };
}
export async function readRawDataText(storageRoot, rawDataRef) {
    const gzipped = await readFile(resolveStoragePath(storageRoot, rawDataRef));
    return (await gunzip(gzipped)).toString('utf8');
}
export async function readRawDataJson(storageRoot, rawDataRef) {
    return JSON.parse(await readRawDataText(storageRoot, rawDataRef));
}
export async function deleteRawData(storageRoot, rawDataRef) {
    if (!rawDataRef)
        return;
    try {
        await unlink(resolveStoragePath(storageRoot, rawDataRef));
    }
    catch (err) {
        if (err?.code !== 'ENOENT')
            throw err;
    }
}
//# sourceMappingURL=store.js.map