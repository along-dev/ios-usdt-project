-- 管理台业务菜单 seed（ios-usdt-project 本地运行）
-- ---------------------------------------------------------------------------
-- 背景：整合产物的 03-web-admin 有 20+ 业务页面（资源/地址/代理/财务/系统配置），
--   但 Go 侧的 menu.go 只 seed 了 gin-vue-admin 的 13 条脚手架菜单
--   ⇒ sys_base_menus 无任何业务菜单 ⇒ 管理台侧边栏空白、无功能入口。
--   依据：09-docs/reports/审核D-前端可用性.md（34 菜单↔页面↔API 映射）。
-- component 必须精确等于 import.meta.glob('../view/**/*.vue') 的键（去 '../' 前缀），
--   否则 asyncRouter.js 匹配不到 ⇒ 点出空白页（见 R-08 记载的同类坑）。
--
-- 幂等：每条 INSERT 均带 NOT EXISTS 守卫；重复执行不产生重复菜单。
-- ---------------------------------------------------------------------------
USE qianke;

SET @ts := NOW(3);

-- ===== ★ 前置：把 admin 归一到角色 888 =====
-- 背景：GVA seed 会把 admin 放到杂散子角色 8881（"普通用户子角色"），而 casbin 里
--   8881 **没有** `/device/*` 等业务策略（只有脚手架 /api,/authority… 共 39 条）；
--   888 有 198 条（含全部业务策略）。
--   ★ 同步更新后（T28 删除 casbin develop 后门 + 权限收紧），8881 访问业务 API 会
--     被拦成 `code:7 权限不足`。⇒ admin 必须归位到 888。
UPDATE sys_users SET authority_id = '888' WHERE username = 'admin';

-- ===== 目录层 =====
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,'0','resource','resource',0,NULL,10,'资源管理','coin',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id='0' AND path='resource');
SET @res := (SELECT id FROM sys_base_menus WHERE parent_id='0' AND path='resource' LIMIT 1);

INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,'0','address','address',0,NULL,11,'地址管理','location',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id='0' AND path='address');
SET @addr := (SELECT id FROM sys_base_menus WHERE parent_id='0' AND path='address' LIMIT 1);

INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,'0','agent','agent',0,NULL,12,'代理管理','user',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id='0' AND path='agent');
SET @ag := (SELECT id FROM sys_base_menus WHERE parent_id='0' AND path='agent' LIMIT 1);

INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,'0','finance','finance',0,NULL,13,'财务管理','money',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id='0' AND path='finance');
SET @fin := (SELECT id FROM sys_base_menus WHERE parent_id='0' AND path='finance' LIMIT 1);

INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,'0','syscfg','syscfg',0,NULL,14,'系统配置','setting',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id='0' AND path='syscfg');
SET @sc := (SELECT id FROM sys_base_menus WHERE parent_id='0' AND path='syscfg' LIMIT 1);

-- ===== 资源管理 =====
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@res,'installation','installation',0,'view/resourceManagement/InstallationList/InstallationList.vue',1,'设备列表','monitor',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@res AND path='installation');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@res,'infoList','infoList',0,'view/resourceManagement/infoList/index.vue',2,'用户信息','document',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@res AND path='infoList');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@res,'walletinfo','walletinfo',0,'view/resourceManagement/CustomerWalletinfo/index.vue',3,'客户钱包','wallet',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@res AND path='walletinfo');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@res,'proxywallet','proxywallet',0,'view/resourceManagement/ProxyWalletInfo/index.vue',4,'代理钱包','wallet',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@res AND path='proxywallet');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@res,'privatewallet','privatewallet',0,'view/resourceManagement/Privatewallet/Privatewallet.vue',5,'私有钱包','lock',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@res AND path='privatewallet');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@res,'walletinformation','walletinformation',0,'view/resourceManagement/walletinformation/walletinformation.vue',6,'钱包信息','wallet',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@res AND path='walletinformation');

-- ===== 地址管理 =====
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@addr,'addr-system','addr-system',0,'view/addressmanagement/index.vue',1,'系统收款地址','location',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@addr AND path='addr-system');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@addr,'addr-agent','addr-agent',0,'view/addressmanagement/agent.vue',2,'代理收款地址','location',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@addr AND path='addr-agent');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@addr,'addr-manage','addr-manage',0,'view/addressmanagement/manage.vue',3,'收款地址管理','location',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@addr AND path='addr-manage');

-- ===== 代理管理 =====
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@ag,'agent-list','agent-list',0,'view/agentList/index.vue',1,'代理列表','user',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@ag AND path='agent-list');

-- ===== 财务管理 =====
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@fin,'privatedomain','privatedomain',0,'view/financialManagement/Privatedomainaccounts.vue',1,'私域账户','coin',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@fin AND path='privatedomain');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@fin,'agencyincome','agencyincome',0,'view/financialManagement/agencyincome.vue',2,'代理收入','money',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@fin AND path='agencyincome');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@fin,'customerfinance','customerfinance',0,'view/financialManagement/customerfinance.vue',3,'客户财务','money',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@fin AND path='customerfinance');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@fin,'platformrevenue','platformrevenue',0,'view/financialManagement/platformrevenue.vue',4,'平台收入','money',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@fin AND path='platformrevenue');

-- ===== 系统配置 =====
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@sc,'commissionsettings','commissionsettings',0,'view/systemconfiguration/commissionsettings.vue',1,'佣金设置','setting',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@sc AND path='commissionsettings');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@sc,'currencysettings','currencysettings',0,'view/systemconfiguration/currencysettings.vue',2,'币种设置','coin',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@sc AND path='currencysettings');
INSERT INTO sys_base_menus (menu_level,parent_id,path,name,hidden,component,sort,title,icon,created_at,updated_at)
SELECT 0,@sc,'projectmanagement','projectmanagement',0,'view/systemconfiguration/projectmanagement.vue',3,'项目管理','folder',@ts,@ts FROM DUAL
 WHERE NOT EXISTS (SELECT 1 FROM sys_base_menus WHERE parent_id=@sc AND path='projectmanagement');

-- ===== 角色-菜单关联 =====
-- ★ admin(用户 id=8) 实际角色是 **8881**（不是 888）；888 是父角色。
--   两个都关联，保证 admin 与 888 角色都能看到业务菜单。
INSERT IGNORE INTO sys_authority_menus (sys_base_menu_id, sys_authority_authority_id)
SELECT id, '888' FROM sys_base_menus
 WHERE (parent_id='0' AND path IN ('resource','address','agent','finance','syscfg'))
    OR parent_id IN (@res,@addr,@ag,@fin,@sc)
 UNION ALL
SELECT id, '8881' FROM sys_base_menus
 WHERE (parent_id='0' AND path IN ('resource','address','agent','finance','syscfg'))
    OR parent_id IN (@res,@addr,@ag,@fin,@sc);

-- ===== 自检 =====
SELECT 'resources' AS sec, COUNT(*) AS n FROM sys_base_menus WHERE parent_id=@res
UNION ALL SELECT 'address', COUNT(*) FROM sys_base_menus WHERE parent_id=@addr
UNION ALL SELECT 'agent',   COUNT(*) FROM sys_base_menus WHERE parent_id=@ag
UNION ALL SELECT 'finance', COUNT(*) FROM sys_base_menus WHERE parent_id=@fin
UNION ALL SELECT 'syscfg',  COUNT(*) FROM sys_base_menus WHERE parent_id=@sc
UNION ALL SELECT 'linked_888', COUNT(*) FROM sys_authority_menus WHERE sys_authority_authority_id='888';
