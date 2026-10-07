export function getRealIP(request) {
    const headers = request.headers;
    return headers['cf-connecting-ip']
        || headers['x-real-ip']
        || headers['x-forwarded-for']?.split(',')[0].trim()
        || request.ip;
}
//# sourceMappingURL=ip.js.map