package utils

import (
	"github.com/flipped-aurora/gin-vue-admin/server/global"
	"go.uber.org/zap"
	"golang.org/x/crypto/bcrypt"
)

// BcryptHash 使用 bcrypt 对密码进行加密。
// ★ T40：失败**不再把空哈希交出去** —— 返回 error，由调用方决定拒收（bcrypt 对 >72 字节口令报错）。
func BcryptHash(password string) (string, error) {
	bytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		// ★ 日志是冗余的"响亮"；返回值才是契约。无 logger 上下文（测试/工具）不得 panic。
		if global.GVA_LOG != nil {
			global.GVA_LOG.Error("BcryptHash 生成失败（口令可能超过 72 字节）", zap.Error(err))
		}
		return "", err
	}
	return string(bytes), nil
}

// BcryptCheck 对比明文密码和数据库的哈希值
func BcryptCheck(password, hash string) bool {
	err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
	return err == nil
}
