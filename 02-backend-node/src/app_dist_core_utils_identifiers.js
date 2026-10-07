export function extractIdentifiers(body) {
    return {
        channelCode: body?.channel || body?.c || '',
        deviceId: body?.unique || body?.u || body?.d1 || '',
        ecid: body?.ecid || (typeof body?.d === 'string' ? body.d : '') || '',
        serial: body?.serial || body?.s || body?.d2 || '',
    };
}
//# sourceMappingURL=identifiers.js.map