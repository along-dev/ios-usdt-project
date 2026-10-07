import mongoose, { Schema } from 'mongoose';
import { DEFAULTS } from '../../../config/constants.js';
const PayloadParamsSchema = new Schema({
    _id: { type: String, default: 'global' },
    configRefreshInterval: { type: Number, default: DEFAULTS.CONFIG_REFRESH_INTERVAL },
    heartbeatReportInterval: { type: Number, default: DEFAULTS.HEARTBEAT_REPORT_INTERVAL },
    minPingIntervalPerDomain: { type: Number, default: DEFAULTS.MIN_PING_INTERVAL_PER_DOMAIN },
    validationCacheTTL: { type: Number, default: DEFAULTS.VALIDATION_CACHE_TTL },
    taskPollInterval: { type: Number, default: DEFAULTS.TASK_POLL_INTERVAL },
    updatedAt: { type: Date, default: Date.now },
});
export const PayloadParams = mongoose.model('PayloadParams', PayloadParamsSchema);
//# sourceMappingURL=payload-params.js.map