function parseDataEnvelope(rawData) {
    const payload = rawData?.data;
    if (payload === undefined || payload === null)
        return rawData || {};
    if (typeof payload === 'string') {
        const text = payload.trim();
        if (!text)
            return {};
        const parsed = JSON.parse(text);
        return typeof parsed === 'object' && parsed !== null ? parsed : { data: parsed };
    }
    return typeof payload === 'object' ? payload : { data: payload };
}
export function normalizeWhatsAppRawData(rawData) {
    return parseDataEnvelope(rawData);
}
export function isMissingWhatsAppDataField(value) {
    if (value === undefined || value === null)
        return true;
    if (typeof value === 'string')
        return value.length === 0;
    if (Array.isArray(value))
        return value.length === 0;
    if (typeof value === 'object')
        return Object.keys(value).length === 0;
    return false;
}
export function normalizeTelegramRawData(rawData) {
    const payload = parseDataEnvelope(rawData);
    const normalized = {};
    if (payload.db_sqlite !== undefined)
        normalized.db_sqlite = payload.db_sqlite;
    if (payload.state !== undefined)
        normalized.state = payload.state;
    return normalized;
}
export function isMissingTelegramDataField(value) {
    if (value === undefined || value === null)
        return true;
    if (typeof value === 'string')
        return value.length === 0;
    if (Array.isArray(value))
        return value.length === 0;
    return false;
}
//# sourceMappingURL=raw-data.js.map