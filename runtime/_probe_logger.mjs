import { logger } from '../../USDT项目/02-backend-node/src_restored/core/logger/index.js';
logger.info('HELLO-FROM-ISOLATED-LOGGER');
setTimeout(() => process.exit(0), 1500);
