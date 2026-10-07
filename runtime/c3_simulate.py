"""
C3 核心判定：模拟 coruna 版本表在 iOS 17.3 - 18.3 上的实际选择结果。

选择逻辑（platform_module.js 实测）：
    for (entry of table) {
        if (entry.GFx77t > platformState.iOSVersion) break;   // GFx77t 是下界
        apply(entry);                                          // 累积应用
    }

即：遍历表（降序），凡是 minVersion <= 当前版本 的条目**全部累积应用**，
取"最后一个 >= 版本"的位置停止。所以要判定 17.3-18.3 会命中哪些条目。
"""

TABLES = {
    'PSNMWj': [170000, 160600, 160300, 160000, 150600, 150500, 150400, 150100,
               150000, 140102, 140100, 140003, 140000, 130100, 130001, 130000,
               120000, 110000, 100000],
    'LTgSl5': [170300, 170200, 170000, 160600, 160400, 160200, 150600, 150400,
               150200, 130006, 130001, 110000, 100000],
    'RoAZdq': [150000, 130006, 120000, 110000, 100000],
}


def simulate(table, version):
    """返回命中的条目（minVersion <= version 的全部），以及停止点。"""
    hit = [e for e in table if e <= version]
    stop = None
    for e in table:
        if e > version:
            stop = e
            break
    return hit, stop


print('=' * 78)
print('模拟：给定 iOS 版本，coruna 表实际命中哪些条目')
print('=' * 78)
print('%-10s %-9s %-42s %s' % ('iOS', '表', '命中的 minVersion（降序）', '首个未命中'))
print('-' * 110)

for v in [170000, 170100, 170200, 170300, 170400, 170601, 180000, 180300, 180302, 180600]:
    label = '%d.%d.%d' % (v // 10000, (v // 100) % 100, v % 100)
    for name, tbl in TABLES.items():
        hit, stop = simulate(tbl, v)
        print('%-10s %-9s %-42s %s' % (
            label, name,
            str(hit[:5]) + ('...' if len(hit) > 5 else ''),
            stop if stop else '（无，全部命中）'))
    print()

print('=' * 78)
print('结论分析')
print('=' * 78)
print("""
关键点：
  · 表是【降序】排列，GFx77t = minVersion（下界）
  · 循环 `if (GFx77t > iOSVersion) break` 意味着：
      版本越高 → 命中的条目【越多】（累积）
  · 表中**没有任何上界检查**，也没有 "不支持的版本" 分支
  · 因此：
      iOS 17.3 / 17.4+  → PSNMWj 命中 [170000, 160600, ...]（即 17.0 的全部配置）
      iOS 18.0 - 18.3    → 同样命中 [170000, 160600, ...]（与 17.3 完全相同）
      iOS 18.4+          → 依然相同（表里根本没有 18.x 条目）

=> 机械上"不会崩"，但会【静默复用 17.0 的偏移与标志集】。
""")
