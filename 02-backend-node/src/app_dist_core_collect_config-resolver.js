import { CollectConfig } from '../db/models/collect-config.js';

/**
 * 根据链和渠道编码解析归集配置（仅渠道专属，无全局兜底）。
 * @param {string} chain
 * @param {string|null|undefined} channelCode
 * @returns {Promise<Array>} 配置列表
 */
export async function resolveConfigsForAddress(chain, channelCode) {
    if (!channelCode) return [];
    return CollectConfig.find({ chain, enabled: true, channelCode }).lean();
}
