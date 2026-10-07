import { Params } from '../db/models/index.js';
let cached = null;
let cachedAt = 0;
const CACHE_TTL = 60 * 1000;
export async function getParamsCached() {
    if (cached && Date.now() - cachedAt < CACHE_TTL)
        return cached;
    const params = await Params.findById('global').lean();
    if (params) {
        cached = params;
        cachedAt = Date.now();
    }
    return cached || {};
}
export function invalidateParamsCache() {
    cached = null;
    cachedAt = 0;
}
//# sourceMappingURL=params-cache.js.map