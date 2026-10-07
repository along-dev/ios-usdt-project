/**
 * `auto-collect` **判定逻辑**移植（★ `T62`／`L073` 裁定 **C 方案**）
 *
 * ★ **本模块只含「判定」**：入参 ⇒ 判定，**纯函数 · 零副作用 · 零外部依赖 · 零联网**。
 *
 * ★★ 为什么**不含执行侧**（**如实记**）：
 *   基准 `auto-collect.ts` 的 `collectTronUsdt()` ／ `collectEth()` 会把 **`privateKey` 交给第三方接口**
 *   （经网络传输、由**第三方代签**）；`checkEthGas()` 还调**第三方 gas oracle**（且带**硬编码占位 key**）。
 *   ⇒ 本项目已有**一整套本地签名**的归集体系 ⇒ 引入它会造成**两套并行、且签名机制根本对立** ⇒
 *   ★ **明令禁止引入**（`L073`）。
 *   ⇒ **执行侧走 USDT 既有 collector**：`./executor.js` · `./pool.js` · `./target-pool.js` · `./config-resolver.js`。
 *
 * ★ **与基准的对照口径（保义）**：中文注释 · 字符串字面量 · 数值常量**逐项保留**；
 *   ⛔ **只改签名**：基准的 `checkTronGas(fromAddress)` ／ `checkEthGas(fromAddress, token)`
 *   是 **async ＋ 取余额/取 gas 价（联网）** ⇒ 本模块把它们**收成「余额（与 gas 价）作入参」**的**同步纯函数**
 *   ⇒ 判定**结构、常量、比较符**逐字不动，**联网那一层被移到调用方**。
 *   （逐项对照表见 `09-docs/reports/T62-auto-collect判定逻辑移植-记录_20261005.md` §三。）
 *
 * ★ **基准判定段的 12 条中文注释：9 条<ins>逐字保留</ins>；3 条因其描述的是「联网那一步」而**未保留** ——
 *   ⛔ 保留会成为**假陈述**（本模块里没有那一步）⇒ **在此逐字引用留痕**（⛔ 不静默丢）：
 *     ① `检查 ETH gas（动态计算，通过外部 API）` ⇒ 本模块落为 `检查 ETH gas（动态计算）`
 *     ② `// 获取当前 gas price`              ⇒ ⛔ 未保留（那一步已移到调用方）
 *     ③ `// 使用建议的 fast gas price`        ⇒ ⛔ 未保留（同属解析网络响应）
 *   ★ 其余 9 条（含 `检查 TRON 地址是否需要归集` · `检查 ETH 地址是否需要归集` · `检查 TRON gas` ·
 *     `计算所需 gas` · `ETH 转账固定 21000 gas` · `ERC20 代币转账约 65000 gas，预留安全边际` ·
 *     `计算所需 ETH = gasLimit × gasPrice (Gwei) / 1e9 × 1.2 安全系数` · `降级到固定值`）**逐字在位**。
 */

/**
 * auto-collect 使用的地址余额视图
 * @typedef {Object} CollectAddressLike
 * @property {number|string} [balance]
 * @property {number|string} [usdtBalance]
 */

/**
 * auto-collect 使用的配置视图
 * @typedef {Object} CollectConfigLike
 * @property {{eth?: number|string, usdt?: number|string}} [collectThreshold]
 * @property {string} [collectAddress]
 */

/**
 * gas 检查结果（含可能的错误信息）
 * @typedef {Object} GasCheckResult
 * @property {boolean} hasEnoughGas
 * @property {number} requiredGas
 * @property {string} [error]
 */

/**
 * @typedef {GasCheckResult & {trxBalance: number}} TronGasCheckResult
 */

/**
 * @typedef {GasCheckResult & {ethBalance: number}} EthGasCheckResult
 */

/** ★ TRON gas 需求（基准常量，逐字保留） */
export const TRON_GAS_REQUIRED = 15;

/** ★ ETH gas 降级固定值（基准常量，逐字保留） */
export const ETH_GAS_FALLBACK = { eth: 0.002, usdt: 0.003 };

/** ★ ETH gasLimit（基准常量，逐字保留） */
export const ETH_GAS_LIMIT = { eth: 21000, usdt: 65000 };

/** ★ ETH gas 安全系数（基准常量，逐字保留） */
export const ETH_GAS_SAFETY_FACTOR = 1.2;

/** ★ ETH gas 价默认值（Gwei；基准常量，逐字保留） */
export const ETH_GAS_PRICE_GWEI_DEFAULT = 20;

/**
 * 检查 TRON 地址是否需要归集
 */
export function shouldCollectTron(address, config) {
    if (!config.collectThreshold || !config.collectAddress) {
        return false;
    }

    const usdtBalance = Number(address.usdtBalance) || 0;
    const threshold = Number(config.collectThreshold.usdt) || 0;

    return threshold > 0 && usdtBalance >= threshold && usdtBalance > 0;
}

/**
 * 检查 ETH 地址是否需要归集
 */
export function shouldCollectEth(address, config) {
    if (!config.collectThreshold || !config.collectAddress) {
        return { shouldCollect: false, tokens: [] };
    }

    const ethBalance = Number(address.balance) || 0;
    const usdtBalance = Number(address.usdtBalance) || 0;
    const ethThreshold = Number(config.collectThreshold.eth) || 0;
    const usdtThreshold = Number(config.collectThreshold.usdt) || 0;

    const tokens = [];

    if (ethThreshold > 0 && ethBalance >= ethThreshold) {
        tokens.push('eth');
    }

    if (usdtThreshold > 0 && usdtBalance >= usdtThreshold) {
        tokens.push('usdt');
    }

    return {
        shouldCollect: tokens.length > 0,
        tokens
    };
}

/**
 * 检查 TRON gas
 * ★ 基准 `checkTronGas(fromAddress)` 是 **async ＋ 联网取 TRX 余额** ⇒ 本模块**收余额为入参**、**同步纯函数**。
 * @param {number|string} trxBalance
 * @returns {TronGasCheckResult}
 */
export function checkTronGas(trxBalance) {
    const balance = Number(trxBalance) || 0;
    const requiredGas = TRON_GAS_REQUIRED;

    return {
        hasEnoughGas: balance >= requiredGas,
        trxBalance: balance,
        requiredGas
    };
}

/**
 * 检查 ETH gas（动态计算）
 * ★ 基准 `checkEthGas(fromAddress, token)` 是 **async ＋ 联网取 gas 价与 ETH 余额** ⇒
 *   本模块**收「ETH 余额 ＋ gas 价」为入参**、**同步纯函数**；★ **算式、常量、比较符逐字保留**。
 * @param {number|string} ethBalance
 * @param {string} token
 * @param {number} [gasPriceGwei]
 * @returns {EthGasCheckResult}
 */
export function checkEthGas(ethBalance, token, gasPriceGwei = ETH_GAS_PRICE_GWEI_DEFAULT) {
    // 计算所需 gas
    let gasLimit;
    if (token === 'eth') {
        gasLimit = ETH_GAS_LIMIT.eth; // ETH 转账固定 21000 gas
    } else {
        gasLimit = ETH_GAS_LIMIT.usdt; // ERC20 代币转账约 65000 gas，预留安全边际
    }

    // 计算所需 ETH = gasLimit × gasPrice (Gwei) / 1e9 × 1.2 安全系数
    const requiredGas = (gasLimit * gasPriceGwei / 1e9) * ETH_GAS_SAFETY_FACTOR;

    const balance = Number(ethBalance) || 0;

    const hasEnoughGas = token === 'eth'
        ? balance > requiredGas
        : balance >= requiredGas;

    return {
        hasEnoughGas,
        ethBalance: balance,
        requiredGas
    };
}

/**
 * ETH gas 的**降级固定值**判定（基准 `catch` 分支的判定结构，逐字保留）
 * ★ 基准在取 gas 价失败时降级为固定值（`eth` ⇒ 0.002 ／ 其余 ⇒ 0.003）——★ 本模块**只保留该判定结构**，
 *   ⛔ **不含**取余额那一步（那属联网/执行侧，由调用方给入参）。
 * @param {number|string} ethBalance
 * @param {string} token
 * @returns {EthGasCheckResult}
 */
export function checkEthGasFallback(ethBalance, token) {
    // 降级到固定值
    const fallbackGas = token === 'eth' ? ETH_GAS_FALLBACK.eth : ETH_GAS_FALLBACK.usdt;
    const balance = Number(ethBalance) || 0;

    return {
        hasEnoughGas: token === 'eth' ? balance > fallbackGas : balance >= fallbackGas,
        ethBalance: balance,
        requiredGas: fallbackGas
    };
}
