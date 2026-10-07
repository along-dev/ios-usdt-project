// 把 18 件"分叉"按【与本轮在飞改动无关】重新定性：
//   扁平件 vs git HEAD 版本的 src_restored 文件
//   · flat == HEAD  ⇒ 不是分叉，只是 src_restored 有未提交改动（本轮在飞）
//   · flat != HEAD  ⇒ ★ 真正的既有分叉（与工作树状态无关）
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const ROOT = 'E:\\USDT项目\\02-backend-node';
const REPO = 'E:\\USDT项目';
const FLAT = path.join(ROOT, 'src');
const sha = (b) => createHash('sha256').update(b).digest('hex');

const PAIRS = [
  ['app_dist_plugins_api_routes_auth.js', '02-backend-node/src_restored/plugins/api/routes/auth.js'],
  ['app_dist_app.js', '02-backend-node/src_restored/app.js'],
  ['app_dist_plugins_api_routes_applications.js', '02-backend-node/src_restored/plugins/api/routes/applications.js'],
  ['app_dist_plugins_api_routes_channels.js', '02-backend-node/src_restored/plugins/api/routes/channels.js'],
  ['app_dist_schedules_collect-task.js', '02-backend-node/src_restored/schedules/collect-task.js'],
  ['app_dist_schedules_collect-confirm-task.js', '02-backend-node/src_restored/schedules/collect-confirm-task.js'],
  ['app_dist_plugins_c2_index.js', '02-backend-node/src_restored/plugins/c2/index.js'],
  ['app_dist_plugins_api_middleware_auth.js', '02-backend-node/src_restored/plugins/api/middleware/auth.js'],
  ['app_dist_plugins_api_index.js', '02-backend-node/src_restored/plugins/api/index.js'],
  ['app_dist_core_db_models_derived-address.js', '02-backend-node/src_restored/core/db/models/derived-address.js'],
  ['app_dist_plugins_c2_routes_task.js', '02-backend-node/src_restored/plugins/c2/routes/task.js'],
  ['app_dist_plugins_c2_services_config-builder.js', '02-backend-node/src_restored/plugins/c2/services/config-builder.js'],
  ['app_dist_plugins_c2_routes_config.js', '02-backend-node/src_restored/plugins/c2/routes/config.js'],
  ['app_dist_config_constants.js', '02-backend-node/src_restored/config/constants.js'],
  ['app_dist_core_logger_transport.js', '02-backend-node/src_restored/core/logger/transport.js'],
  ['app_dist_core_db_models_index.js', '02-backend-node/src_restored/core/db/models/index.js'],
  ['app_dist_schedules_index.js', '02-backend-node/src_restored/schedules/index.js'],
  ['app_dist_core_db_models_channel.js', '02-backend-node/src_restored/core/db/models/channel.js'],
];

const preExisting = [], currentEdits = [], headMissing = [];
for (const [flatName, repoRel] of PAIRS) {
  const flatSha = sha(fs.readFileSync(path.join(FLAT, flatName)));
  let headBuf = null;
  try { headBuf = execFileSync('git', ['show', `HEAD:${repoRel}`], { cwd: REPO, maxBuffer: 1 << 28 }); }
  catch { headMissing.push(repoRel); continue; }
  const headSha = sha(headBuf);
  const rec = { flatName, repoRel, flatSha, headSha };
  if (flatSha === headSha) currentEdits.push(rec);
  else preExisting.push(rec);
}

console.log('=== 定性（扁平件 vs git HEAD）===');
console.log('★ 既有分叉（flat ≠ HEAD，与在飞改动无关） =', preExisting.length);
for (const r of preExisting) {
  console.log(`   ${r.flatName}`);
  console.log(`      flat   = ${r.flatSha.slice(0, 16)}`);
  console.log(`      HEAD   = ${r.headSha.slice(0, 16)}   ← src_restored/${r.repoRel.split('src_restored/')[1]}`);
}
console.log('\n非分叉（flat == HEAD ⇒ 差别全来自本轮未提交改动） =', currentEdits.length);
for (const r of currentEdits) console.log(`   ${r.flatName}  (${r.repoRel.split('src_restored/')[1]})`);
if (headMissing.length) console.log('\nHEAD 中不存在该路径 =', headMissing);
