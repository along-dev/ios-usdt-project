import mongoose from 'mongoose';
import Redis from 'ioredis';
import { logger } from '../logger/index.js';
let redis = null;
export async function connectMongo(uri) {
    try {
        await mongoose.connect(uri, {
            serverSelectionTimeoutMS: 10_000,
            connectTimeoutMS: 10_000,
            socketTimeoutMS: 30_000,
        });
        logger.info('MongoDB connected');
    }
    catch (err) {
        logger.fatal({ err }, 'MongoDB connection failed');
        throw err;
    }
}
export async function connectRedis(url) {
    // @ts-ignore - ioredis ESM 兼容性问题
    redis = new Redis(url, {
        maxRetriesPerRequest: 3,
        retryStrategy(times) {
            if (times > 5)
                return null;
            return Math.min(times * 200, 2000);
        },
    });
    redis.on('error', (err) => logger.error({ err }, 'Redis error'));
    redis.on('connect', () => logger.info('Redis connected'));
    return redis;
}
export function getRedis() {
    if (!redis)
        throw new Error('Redis not initialized');
    return redis;
}
export async function disconnectAll() {
    await mongoose.disconnect();
    if (redis) {
        redis.disconnect();
        redis = null;
    }
}
//# sourceMappingURL=connection.js.map