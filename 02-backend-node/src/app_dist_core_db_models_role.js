import mongoose, { Schema } from 'mongoose';
const RoleSchema = new Schema({
    name: { type: String, required: true, unique: true },
    menuKeys: { type: [String], default: [] },
    visibleChains: { type: [String], default: [] },
    visibleSocialTypes: { type: [String], default: [] },
}, { timestamps: true });
export const Role = mongoose.model('Role', RoleSchema);
//# sourceMappingURL=role.js.map