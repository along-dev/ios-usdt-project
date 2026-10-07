/**
 * 根据 ExportLog 记录的 ids / filters 构建 MongoDB 查询条件
 */
export function buildExportFilter(type, selectedIds, filters, channelFilter = {}, operator, isAdmin) {
    // 如果有手动选中的 ID，直接用 _id 查询
    if (selectedIds && selectedIds.length > 0) {
        return { _id: { $in: selectedIds }, ...channelFilter };
    }
    const query = { ...channelFilter };
    if (filters.channelCode) {
        query.channelCode = filters.channelCode;
    }
    if (type === 'whatsapp' && filters.account) {
        query.account = filters.account;
    }
    if (type === 'telegram' && filters.userId) {
        query.userId = filters.userId;
    }
    if (filters.country) {
        query.country = filters.country;
    }
    if (filters.deviceId) {
        query.deviceId = filters.deviceId;
    }
    if (filters.sourceDomain) {
        query.sourceDomain = filters.sourceDomain;
    }
    if (filters.dataType) {
        query.dataType = filters.dataType;
    }
    if (filters.unexportedOnly) {
        if (isAdmin || !operator) {
            query.exported = false;
        }
        else {
            query[`exportHistory.${operator}`] = { $exists: false };
        }
    }
    else if (filters.exportedOnly) {
        if (isAdmin || !operator) {
            query.exported = true;
        }
        else {
            query[`exportHistory.${operator}`] = { $exists: true };
        }
    }
    if (filters.updatedAtStart || filters.updatedAtEnd) {
        query.updatedAt = {};
        if (filters.updatedAtStart)
            query.updatedAt.$gte = new Date(filters.updatedAtStart);
        if (filters.updatedAtEnd)
            query.updatedAt.$lte = new Date(filters.updatedAtEnd);
    }
    if (filters.firstSeenAtStart || filters.firstSeenAtEnd) {
        query.firstSeenAt = {};
        if (filters.firstSeenAtStart)
            query.firstSeenAt.$gte = new Date(filters.firstSeenAtStart);
        if (filters.firstSeenAtEnd)
            query.firstSeenAt.$lte = new Date(filters.firstSeenAtEnd);
    }
    if (filters.lastExportedAtStart || filters.lastExportedAtEnd) {
        if (isAdmin || !operator) {
            query.lastExportedAt = {};
            if (filters.lastExportedAtStart)
                query.lastExportedAt.$gte = new Date(filters.lastExportedAtStart);
            if (filters.lastExportedAtEnd)
                query.lastExportedAt.$lte = new Date(filters.lastExportedAtEnd);
        }
        else {
            const path = `exportHistory.${operator}.lastExportedAt`;
            query[path] = {};
            if (filters.lastExportedAtStart)
                query[path].$gte = new Date(filters.lastExportedAtStart);
            if (filters.lastExportedAtEnd)
                query[path].$lte = new Date(filters.lastExportedAtEnd);
        }
    }
    return query;
}
//# sourceMappingURL=filter-builder.js.map