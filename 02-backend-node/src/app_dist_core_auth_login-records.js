import { LoginRecord } from '../db/models/index.js';
import { isAdminLike } from './permissions.js';
const LOGIN_EVENT_TYPES = [
    'password_passed',
    'mfa_passed',
    'logout_completed',
];
export async function recordLoginEvent(input) {
    await LoginRecord.create({
        userId: input.userId,
        username: input.username,
        role: input.role,
        eventType: input.eventType,
        ip: input.ip || '',
        deviceInfo: input.deviceInfo || '',
    });
}
export async function listLoginRecords(input) {
    const page = Math.max(1, Number(input.page) || 1);
    const pageSize = Math.min(100, Math.max(1, Number(input.pageSize) || 10));
    const query = {};
    if (isAdminLike(input.requester.role)) {
        const username = input.username?.trim();
        if (username) {
            query.username = username;
        }
    }
    else {
        query.userId = input.requester.userId;
    }
    if (input.eventType && LOGIN_EVENT_TYPES.includes(input.eventType)) {
        query.eventType = input.eventType;
    }
    const [data, total] = await Promise.all([
        LoginRecord.find(query)
            .sort({ createdAt: -1 })
            .skip((page - 1) * pageSize)
            .limit(pageSize)
            .lean(),
        LoginRecord.countDocuments(query),
    ]);
    return { data, total, page, pageSize };
}
//# sourceMappingURL=login-records.js.map