package utils

import (
	"strings"
	"testing"

	"github.com/flipped-aurora/gin-vue-admin/server/global"
)

// ★ T46 · V1（T40 契约的常驻回归）：73 字节口令 ⇒ bcrypt 必失败 ⇒ **必须返回 error 且不交出哈希**。
//
//	★ 本包测试全程**不初始化** `global.GVA_LOG`（生产由 main.go:24 的 core.Zap() 初始化）
//	  ⇒ 这同时就是 T46 §四 V2 的**负控**：失败分支**不得 panic**。
func TestBcryptHash_TooLongReturnsError(t *testing.T) {
	h, err := BcryptHash(strings.Repeat("a", 73)) // 73 > 72 字节
	if err == nil {
		t.Fatalf("73 字节口令应返回 error，实得 err=nil、h=%q", h)
	}
	if h != "" {
		t.Fatalf("失败时不得交出哈希，实得 h=%q", h)
	}
}

// ★ T46 · V2（负控，显式）：把 logger 显式置 nil ⇒ 调 `BcryptHash(73 字节)` **不得 panic**、须返回 error。
//
//	依据：`global.GVA_LOG` 全仓仅 `main.go:24` 一处赋值 ⇒ 测试/工具上下文会是 nil。
func TestBcryptHash_NoLoggerDoesNotPanic(t *testing.T) {
	global.GVA_LOG = nil // 模拟"未初始化 logger"的上下文（cmd_seed_tmp 那类）
	h, err := BcryptHash(strings.Repeat("a", 73))
	if err == nil {
		t.Fatalf("应返回 error，实得 err=nil、h=%q", h)
	}
	if h != "" {
		t.Fatalf("失败时不得交出哈希，实得 h=%q", h)
	}
}

// ★ T46：短口令 ⇒ 行为不变（哈希可被 BcryptCheck 校验：正确为真、错误为假）。
func TestBcryptHash_ShortPasswordUnchanged(t *testing.T) {
	h, err := BcryptHash("short-pw")
	if err != nil {
		t.Fatalf("短口令不应报错：%v", err)
	}
	if !BcryptCheck("short-pw", h) {
		t.Fatal("正确口令应通过 BcryptCheck")
	}
	if BcryptCheck("wrong-pw", h) {
		t.Fatal("错误口令不应通过 BcryptCheck")
	}
}
