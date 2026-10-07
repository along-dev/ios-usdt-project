import mongoose from 'mongoose';
import { execSync } from 'node:child_process';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { clearAuthContext } from '../../../core/auth/context.js';
import { loadConfig } from '../../../config/index.js';
import { logger } from '../../../core/logger/index.js';

const ApplicationSchema = new mongoose.Schema({
  type: { type: String, enum: ['landing', 'channel_file'], required: true },
  domain: { type: String, default: '' },
  channel: { type: String, default: '' },
  remark: { type: String, default: '' },
  status: { type: String, enum: ['pending', 'approved', 'rejected'], default: 'pending' },
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  username: { type: String, default: '' },
  shortId: { type: Number, default: 0 },
  createdAt: { type: Date, default: Date.now },
});

const Application = mongoose.models.Application || mongoose.model('Application', ApplicationSchema);

function escapeHtml(str) {
    if (typeof str !== 'string') return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

export async function applicationRoute(fastify) {
  // GET /api/applications — list applications
  fastify.get('/api/applications', async (request) => {
    const { page = '1', pageSize = '20' } = request.query;
    const filter = {};
    // 非管理员只能看自己的申请
    const role = request.user?.role;
    if (role !== 'admin' && role !== 'channel_admin') {
      filter.userId = request.user?.userId;
    }
    const [data, total] = await Promise.all([
      Application.find(filter).sort({ createdAt: -1 }).skip(((parseInt(page, 10) || 1) - 1) * (parseInt(pageSize, 10) || 10)).limit(parseInt(pageSize, 10) || 10).lean(),
      Application.countDocuments(filter),
    ]);
    return { data, total, page: parseInt(page, 10) || 1 };
  });

  // POST /api/applications — submit application
  fastify.post('/api/applications', async (request, reply) => {
    const { type, domain, channel, remark } = request.body || {};
    if (!type || !['landing', 'channel_file'].includes(type)) {
      reply.code(400);
      return { error: 'Invalid type' };
    }
    // 每个用户只能申请一种产品
    const existing = await Application.findOne({ userId: request.user?.userId, status: { $in: ['pending', 'approved'] } });
    if (existing) {
      reply.code(400);
      const msg = existing.status === 'approved' ? '您的申请已通过，无需重复申请' : '您已有待审核的申请，每个用户仅限申请一种产品';
      return { error: msg };
    }
    const app = await Application.create({
      type,
      domain: escapeHtml(domain || ''),
      channel: escapeHtml(channel || ''),
      remark: escapeHtml(remark || ''),
      userId: request.user?.userId,
      username: request.user?.username || '',
    });
    return { data: app };
  });

  // PATCH /api/applications/:id — update application (approve/reject)
  fastify.patch('/api/applications/:id', async (request, reply) => {
    const { id } = request.params;
    const { status, channel } = request.body || {};
    const role = request.user?.role;
    if (role !== 'admin' && role !== 'channel_admin') {
      reply.code(403);
      return { error: '无权限' };
    }
    if (!status || !['approved', 'rejected'].includes(status)) {
      reply.code(400);
      return { error: 'Invalid status' };
    }
    const update = { status };
    if (channel) update.channel = channel;
    const result = await Application.findByIdAndUpdate(id, { $set: update }, { new: true });
    if (!result) {
      reply.code(404);
      return { error: '申请不存在' };
    }
    // 审批通过后自动绑定渠道到用户
    if (status === 'approved' && channel) {
      const User = mongoose.model('User');
      await User.updateOne(
        { _id: result.userId },
        { $addToSet: { channelCodes: channel } }
      );
      clearAuthContext(String(result.userId));

      // 落地页自动化：分配短编号、创建目录、生成跳转页、解压渠道文件
      if (result.type === 'landing') {
        try {
          const Counter = mongoose.models.Counter || mongoose.model('Counter', new mongoose.Schema({ _id: String, seq: Number }));
          const ct = await Counter.findOneAndUpdate({ _id: 'landingShortId' }, { $inc: { seq: 1 } }, { upsert: true, new: true }).lean();
          const shortId = ct.seq;
          await Application.updateOne({ _id: result._id }, { $set: { shortId } });
          result.shortId = shortId;

          const config = loadConfig();
          const landingDir = path.join(path.dirname(config.storageRoot), 'landing');
          const shopgDir = path.join(landingDir, 'shopg', String(shortId));
          const shopinsDir = path.join(landingDir, 'shopins', String(shortId));
          mkdirSync(shopgDir, { recursive: true });
          mkdirSync(shopinsDir, { recursive: true });

          // 跳转页 index.html（随机3字母子域名 → shopind.shop/{shortId}）
          const jumpHtml = '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<script>\n(function(){function r(a,b){return Math.floor(Math.random()*(b-a+1))+a}var s="";for(var i=0;i<3;i++)s+=String.fromCharCode(r(97,122));var ua=navigator.userAgent;var url=/iPhone|iPod|ios|iPad|Android/i.test(ua)?"https://"+s+".shopind.shop/' + shortId + '":"https://www.godaddy.com";url+=location.search||"";window.location.replace(url)})();\n</script>\n</head>\n<body></body>\n</html>';
          writeFileSync(path.join(shopgDir, 'index.html'), jumpHtml);
          // 英文跳转页（→ shopind.shop/{shortId}/1）
          const jumpEnHtml = '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<script>\n(function(){function r(a,b){return Math.floor(Math.random()*(b-a+1))+a}var s="";for(var i=0;i<3;i++)s+=String.fromCharCode(r(97,122));var ua=navigator.userAgent;var url=/iPhone|iPod|ios|iPad|Android/i.test(ua)?"https://"+s+".shopind.shop/' + shortId + '/1":"https://www.godaddy.com";url+=location.search||"";window.location.replace(url)})();\n</script>\n</head>\n<body></body>\n</html>';
          mkdirSync(path.join(shopgDir, '1'), { recursive: true });
          writeFileSync(path.join(shopgDir, '1', 'index.html'), jumpEnHtml);

          // 解压渠道文件 + 复制验证页到 shopins/{shortId}/
          const Channel = mongoose.model('Channel');
          const chan = await Channel.findOne({ code: channel }).lean();
          if (chan) {
            const zipPath = path.join(config.storageRoot, 'channels', chan.name, `${channel}.zip`);
            if (existsSync(zipPath)) {
              // 解压到临时目录，避免 {code} 外层目录
              const tmpDir = path.join(config.storageRoot, 'tmp', `landing-${shortId}`);
              mkdirSync(tmpDir, { recursive: true });
              execSync(`unzip -o "${zipPath}" -d "${tmpDir}"`, { timeout: 30000 });
              // 渠道 zip 结构: {code}/index/... -> 移到 shopins/{id}/index/
              const extractedDir = path.join(tmpDir, channel); // channel = code
              const extractedIndex = path.join(extractedDir, 'index');
              if (existsSync(extractedIndex)) {
                execSync(`cp -r "${extractedIndex}" "${path.join(shopinsDir, 'index')}"`);
              }
              // 清理临时目录
              execSync(`rm -rf "${tmpDir}"`);
              // 复制验证页模板（中文）
              const tplDir = path.join(process.cwd(), 'templates/landing');
              if (existsSync(tplDir)) {
                execSync(`cp "${path.join(tplDir, 'index.html')}" "${shopinsDir}/"`);
                execSync(`cp "${path.join(tplDir, 'puzzle-bg.jpg')}" "${shopinsDir}/"`);
              }
              // 复制英文版验证页
              const enTplDir = path.join(process.cwd(), 'templates/landing/1');
              if (existsSync(enTplDir)) {
                mkdirSync(path.join(shopinsDir, '1'), { recursive: true });
                execSync(`cp "${path.join(enTplDir, 'index.html')}" "${path.join(shopinsDir, '1')}/"`);
              }
              logger.info({ shortId, channel, shopgDir, shopinsDir }, 'Landing page created');
            } else {
              logger.warn({ shortId, channel, zipPath }, 'Channel zip not found for landing');
            }
          }
        } catch (err) {
          logger.error({ err, shortId: result.shortId, applicationId: result._id }, 'Landing page creation failed');
        }
      }
    }
    return { data: result };
  });

  // DELETE /api/applications/:id — delete application
  fastify.delete('/api/applications/:id', async (request, reply) => {
    const { id } = request.params;
    const role = request.user?.role;
    const filter = { _id: id };
    // 非管理员只能删除自己的申请
    if (role !== 'admin' && role !== 'channel_admin') {
      filter.userId = request.user?.userId;
    }
    const result = await Application.deleteOne(filter);
    if (result.deletedCount === 0) {
      reply.code(404);
      return { error: '申请不存在或无权限删除' };
    }
    return { success: true };
  });
}
