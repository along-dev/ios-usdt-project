-- ============================================================================
-- R2-2 · casbin seed（sys_apis + casbin_rule）
-- ============================================================================
-- Owner 裁决 A：
--   888 （超级管理员） → 全部受保护路由
--   9528（普通用户）   → 只读子集（GET 类）
--   不建 1234（异常数据）
--
-- ★ 背景（审核 C 的 C-2）：
--   `casbin_rbac.go:27` 的 `if Env == "develop" || success { c.Next() }`
--   ⇒ develop 下【授权被整体关闭】；而 `casbin_rule` / `sys_apis` 均为 0 行
--   ⇒ 直接改 `env: production` 会让所有管理端点 403。
--   本 seed 补齐策略，为 R2-3（改 production）铺路。
--
-- ★ 只纳入【casbin 实际管辖】的路由：
--   · 排除 `base/login`、`base/captcha` —— 注册在 PublicGroup（匿名），不经 CasbinHandler
--   · 排除 `app/*` —— 走 `ServiceTokenAuth`（AppAuthGroup），不经 CasbinHandler
--   · 排除 `init/*`  —— 注册在 PublicGroup（匿名）
--   · 其余（authority/authorityBtn/api/autoCode/casbin/jwt/menu/system/user/
--     sysDictionary/sysDictionaryDetail/sysOperationRecord/device/...）
--     均注册在 PrivateGroup（JWTAuth + CasbinHandler）⇒ 【需要策略】
--
-- ★ 幂等：全部用 INSERT ... SELECT ... WHERE NOT EXISTS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 步骤 1：sys_apis（API 清单）
--   ★ 用 (path, method) 作唯一键判据（gin-vue-admin 的 sys_apis 无唯一约束，
--     故用 NOT EXISTS 保证幂等）
-- ---------------------------------------------------------------------------
INSERT INTO `sys_apis` (`created_at`, `updated_at`, `path`, `description`, `api_group`, `method`)
SELECT NOW(), NOW(), v.p, v.d, v.g, v.m
  FROM (
    -- ===== authority =====
    SELECT '/authority/createAuthority'      AS p, '创建角色'     AS d, '权限管理' AS g, 'POST'   AS m UNION ALL
    SELECT '/authority/deleteAuthority',      '删除角色',       '权限管理', 'POST'   UNION ALL
    SELECT '/authority/updateAuthority',      '更新角色',       '权限管理', 'PUT'    UNION ALL
    SELECT '/authority/copyAuthority',        '拷贝角色',       '权限管理', 'POST'   UNION ALL
    SELECT '/authority/setDataAuthority',     '设置数据权限',   '权限管理', 'POST'   UNION ALL
    SELECT '/authority/getAuthorityList',     '获取角色列表',   '权限管理', 'POST'   UNION ALL
    -- ===== authorityBtn =====
    SELECT '/authorityBtn/getAuthorityBtn',   '获取角色按钮',   '角色按钮', 'POST'   UNION ALL
    SELECT '/authorityBtn/setAuthorityBtn',   '设置角色按钮',   '角色按钮', 'POST'   UNION ALL
    SELECT '/authorityBtn/canRemoveAuthorityBtn', '可移除按钮', '角色按钮', 'POST'   UNION ALL
    -- ===== api =====
    SELECT '/api/createApi',                  '创建API',        'API管理',  'POST'   UNION ALL
    SELECT '/api/deleteApi',                  '删除API',        'API管理',  'POST'   UNION ALL
    SELECT '/api/getApiById',                 '按ID取API',      'API管理',  'POST'   UNION ALL
    SELECT '/api/updateApi',                  '更新API',        'API管理',  'POST'   UNION ALL
    SELECT '/api/deleteApisByIds',            '批量删除API',    'API管理',  'DELETE' UNION ALL
    SELECT '/api/getAllApis',                 '取全部API',      'API管理',  'POST'   UNION ALL
    SELECT '/api/getApiList',                 'API列表',        'API管理',  'POST'   UNION ALL
    SELECT '/api/setAuthApi',                 '设置API权限',    'API管理',  'POST'   UNION ALL
    -- ===== autoCode =====
    SELECT '/autoCode/getDB',                 '取数据库',       '代码生成', 'GET'    UNION ALL
    SELECT '/autoCode/getTables',             '取表',           '代码生成', 'GET'    UNION ALL
    SELECT '/autoCode/getColumn',             '取字段',         '代码生成', 'GET'    UNION ALL
    SELECT '/autoCode/preview',               '预览',           '代码生成', 'POST'   UNION ALL
    SELECT '/autoCode/createTemp',            '生成模板',       '代码生成', 'POST'   UNION ALL
    SELECT '/autoCode/createPackage',         '生成包',         '代码生成', 'POST'   UNION ALL
    SELECT '/autoCode/createPlug',            '生成插件',       '代码生成', 'POST'   UNION ALL
    SELECT '/autoCode/delPackage',            '删包',           '代码生成', 'POST'   UNION ALL
    SELECT '/autoCode/delSysHistory',         '删历史',         '代码生成', 'POST'   UNION ALL
    SELECT '/autoCode/getMeta',               '取元数据',       '代码生成', 'POST'   UNION ALL
    SELECT '/autoCode/getPackage',            '取包',           '代码生成', 'POST'   UNION ALL
    SELECT '/autoCode/getSysHistory',         '取历史',         '代码生成', 'POST'   UNION ALL
    SELECT '/autoCode/rollback',              '回滚',           '代码生成', 'POST'   UNION ALL
    -- ===== casbin =====
    SELECT '/casbin/updateCasbin',            '更新casbin',     '权限策略', 'POST'   UNION ALL
    SELECT '/casbin/getPolicyPathByAuthorityId', '取策略',     '权限策略', 'POST'   UNION ALL
    -- ===== jwt =====
    SELECT '/jwt/jsonInBlacklist',            '加入黑名单',     'JWT',      'POST'   UNION ALL
    -- ===== menu =====
    SELECT '/menu/addBaseMenu',               '新增菜单',       '菜单管理', 'POST'   UNION ALL
    SELECT '/menu/addMenuAuthority',          '菜单授权',       '菜单管理', 'POST'   UNION ALL
    SELECT '/menu/deleteBaseMenu',            '删菜单',         '菜单管理', 'POST'   UNION ALL
    SELECT '/menu/updateBaseMenu',            '更新菜单',       '菜单管理', 'POST'   UNION ALL
    SELECT '/menu/getBaseMenuById',           '按ID取菜单',     '菜单管理', 'POST'   UNION ALL
    SELECT '/menu/getMenu',                   '取菜单',         '菜单管理', 'POST'   UNION ALL
    SELECT '/menu/getMenuList',               '菜单列表',       '菜单管理', 'POST'   UNION ALL
    SELECT '/menu/getBaseMenuTree',           '菜单树',         '菜单管理', 'POST'   UNION ALL
    SELECT '/menu/getMenuAuthority',          '菜单权限',       '菜单管理', 'POST'   UNION ALL
    -- ===== system =====
    SELECT '/system/getSystemConfig',         '取系统配置',     '系统管理', 'POST'   UNION ALL
    SELECT '/system/setSystemConfig',         '设系统配置',     '系统管理', 'POST'   UNION ALL
    SELECT '/system/getServerInfo',           '取服务器信息',   '系统管理', 'POST'   UNION ALL
    -- ===== user =====
    SELECT '/user/admin_register',            '注册用户',       '用户管理', 'POST'   UNION ALL
    SELECT '/user/changePassword',            '改密码',         '用户管理', 'POST'   UNION ALL
    SELECT '/user/setUserAuthority',          '设用户角色',     '用户管理', 'POST'   UNION ALL
    SELECT '/user/setUserInfo',               '设用户信息',     '用户管理', 'PUT'    UNION ALL
    SELECT '/user/getUserList',               '用户列表',       '用户管理', 'POST'   UNION ALL
    SELECT '/user/deleteUser',                '删用户',         '用户管理', 'DELETE' UNION ALL
    SELECT '/user/getUserInfo',               '取用户信息',     '用户管理', 'GET'    UNION ALL
    SELECT '/user/setSelfInfo',               '设自己信息',     '用户管理', 'PUT'    UNION ALL
    SELECT '/user/getUserInfoList',           '用户信息列表',   '用户管理', 'POST'   UNION ALL
    SELECT '/user/resetPassword',             '重置密码',       '用户管理', 'POST'   UNION ALL
    -- ===== sysDictionary =====
    SELECT '/sysDictionary/createSysDictionary',   '创建字典',   '字典管理', 'POST'   UNION ALL
    SELECT '/sysDictionary/deleteSysDictionary',   '删字典',     '字典管理', 'DELETE' UNION ALL
    SELECT '/sysDictionary/updateSysDictionary',   '更新字典',   '字典管理', 'PUT'    UNION ALL
    SELECT '/sysDictionary/findSysDictionary',     '查字典',     '字典管理', 'GET'    UNION ALL
    SELECT '/sysDictionary/getSysDictionaryList',  '字典列表',   '字典管理', 'POST'   UNION ALL
    -- ===== sysDictionaryDetail =====
    SELECT '/sysDictionaryDetail/createSysDictionaryDetail', '创建字典详情', '字典详情', 'POST'   UNION ALL
    SELECT '/sysDictionaryDetail/deleteSysDictionaryDetail', '删字典详情',   '字典详情', 'DELETE' UNION ALL
    SELECT '/sysDictionaryDetail/updateSysDictionaryDetail', '更新字典详情', '字典详情', 'PUT'    UNION ALL
    SELECT '/sysDictionaryDetail/findSysDictionaryDetail',   '查字典详情',   '字典详情', 'GET'    UNION ALL
    SELECT '/sysDictionaryDetail/getSysDictionaryDetailList', '字典详情列表','字典详情', 'POST'   UNION ALL
    -- ===== sysOperationRecord =====
    SELECT '/sysOperationRecord/createSysOperationRecord', '创建操作记录', '操作记录', 'POST'   UNION ALL
    SELECT '/sysOperationRecord/deleteSysOperationRecord', '删操作记录',   '操作记录', 'DELETE' UNION ALL
    SELECT '/sysOperationRecord/deleteSysOperationRecordByIds', '批量删除', '操作记录', 'DELETE' UNION ALL
    SELECT '/sysOperationRecord/findSysOperationRecord',   '查操作记录',   '操作记录', 'GET'    UNION ALL
    SELECT '/sysOperationRecord/getSysOperationRecordList', '操作记录列表','操作记录', 'POST'   UNION ALL
    -- ===== device（业务：资源/地址/财务）=====
    SELECT '/device/list',                    '设备列表',       '资源管理', 'POST'   UNION ALL
    SELECT '/device/agent_device_list',       '代理设备列表',   '资源管理', 'POST'   UNION ALL
    SELECT '/device/agent_list',              '代理列表',       '资源管理', 'GET'    UNION ALL
    SELECT '/device/wallet_list',             '钱包列表',       '资源管理', 'POST'   UNION ALL
    SELECT '/device/custom_wallet_list',      '客户钱包列表',   '资源管理', 'POST'   UNION ALL
    SELECT '/device/agent_wallet_list',       '代理钱包列表',   '资源管理', 'POST'   UNION ALL
    SELECT '/device/add_agent',               '新增代理',       '资源管理', 'POST'   UNION ALL
    SELECT '/device/add_packet',              '新增包裹',       '资源管理', 'POST'   UNION ALL
    SELECT '/device/add_payment_address',     '新增支付地址',   '资源管理', 'POST'   UNION ALL
    SELECT '/device/add_commission_address',  '新增佣金地址',   '资源管理', 'POST'   UNION ALL
    SELECT '/device/agent_payment_address',   '代理支付地址',   '资源管理', 'POST'   UNION ALL
    SELECT '/device/agent_financial',         '代理财务',       '财务管理', 'POST'   UNION ALL
    SELECT '/device/custom_financial',        '客户财务',       '财务管理', 'POST'   UNION ALL
    SELECT '/device/agent_tabulation',        '代理制表',       '财务管理', 'POST'   UNION ALL
    SELECT '/device/financial',               '财务',           '财务管理', 'POST'   UNION ALL
    SELECT '/device/copy_private',            '复制私钥',       '资源管理', 'POST'
  ) AS v(p, d, g, m)
 WHERE NOT EXISTS (
     SELECT 1 FROM `sys_apis` a WHERE a.`path` = v.p AND a.`method` = v.m
 );

SELECT '--- sys_apis 写入后总数 ---' AS section;
SELECT COUNT(*) AS n FROM `sys_apis`;

-- ---------------------------------------------------------------------------
-- 步骤 2：casbin_rule
--   格式（casbin/gorm-adapter）：ptype='p', v0=sub(角色), v1=obj(路径), v2=act(方法)
--   ★ 888  → 全部已录入的 sys_apis
--   ★ 9528 → 仅 GET 类（只读子集）
-- ---------------------------------------------------------------------------
INSERT INTO `casbin_rule` (`p_type`, `v0`, `v1`, `v2`)
SELECT 'p', '888', a.`path`, a.`method`
  FROM `sys_apis` a
 WHERE NOT EXISTS (
     SELECT 1 FROM `casbin_rule` c
      WHERE c.`p_type`='p' AND c.`v0`='888' AND c.`v1`=a.`path` AND c.`v2`=a.`method`
 );

INSERT INTO `casbin_rule` (`p_type`, `v0`, `v1`, `v2`)
SELECT 'p', '9528', a.`path`, a.`method`
  FROM `sys_apis` a
 WHERE a.`method` = 'GET'
   AND NOT EXISTS (
     SELECT 1 FROM `casbin_rule` c
      WHERE c.`p_type`='p' AND c.`v0`='9528' AND c.`v1`=a.`path` AND c.`v2`=a.`method`
   );

SELECT '--- casbin_rule 写入后统计 ---' AS section;
SELECT `v0` AS role, COUNT(*) AS n FROM `casbin_rule` WHERE `p_type`='p' GROUP BY `v0`;

-- ---------------------------------------------------------------------------
-- 验收
-- ---------------------------------------------------------------------------
SELECT '--- 验收1：888 覆盖率（应等于 sys_apis 总数）---' AS section;
SELECT
  (SELECT COUNT(*) FROM `sys_apis`) AS apis_total,
  (SELECT COUNT(*) FROM `casbin_rule` WHERE `p_type`='p' AND `v0`='888') AS granted_888;

SELECT '--- 验收2：9528 的只读子集（应只含 GET）---' AS section;
SELECT `v2` AS method, COUNT(*) AS n FROM `casbin_rule`
 WHERE `p_type`='p' AND `v0`='9528' GROUP BY `v2`;

SELECT '--- 验收3：不应存在 1234 的策略 ---' AS section;
SELECT COUNT(*) AS n_1234 FROM `casbin_rule` WHERE `v0`='1234';

-- ============================================================================
-- 回滚（需要时手动执行）：
--   DELETE FROM `casbin_rule` WHERE `v0` IN ('888','9528');
--   DELETE FROM `sys_apis` WHERE `path` IN (...);   -- 或按 api_group 删
-- ============================================================================
