import mongoose, { Schema } from 'mongoose';
const ChannelSchema = new Schema({
    code: { type: String, required: true, unique: true },
    name: { type: String, required: true, unique: true },
    domains: { type: [String], default: [], index: true },
    primaryDomain: { type: String, default: '' },
    // ★ W-AD-01：与 Go 侧的三条绑定（各自独立，不可互相推导 —— 见各字段注释）
    //   groupId  = Go `packet.group_id`：**设备上报的操作键**
    //              （Go `service/app/public.go:21` 以 `Where("group_id=?", reqDevice.GroupId)` 反查 packet）
    //   packetId = Go `packet.id`：关系主键；Go `agent.packet_id` 引用的是**本列的值**（不是 group_id）
    //   agentId  = Go `agent.id`：代理粒度，「代理商 A 看不到 B 的渠道」这条反向判据落在本列
    groupId: { type: String, default: '', index: true },
    packetId: { type: Number, default: null },
    agentId: { type: Number, default: null, index: true },
    // ★ W-AD-05：本渠道的落地页模板名（**裸名**，如 `japapp`）。
    //   空 = 未绑定 ⇒ `/api/template` 回退环境变量 `LANDING_TEMPLATE` ⇒ 再回退默认。
    landingTemplate: { type: String, default: '' },
    corePayloadSha256: { type: String, default: '' },
    corePayloadSize: { type: Number, default: 0 },
    zipVersion: { type: Number, default: 1 },
    zipRegeneratedAt: { type: Date, default: null },
    createdAt: { type: Date, default: Date.now },
});
export const Channel = mongoose.model('Channel', ChannelSchema);
//# sourceMappingURL=channel.js.map