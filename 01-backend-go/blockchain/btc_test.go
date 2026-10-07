package blockchain

import "testing"

// BIP84 官方测试向量（https://github.com/bitcoin/bips/blob/master/bip-0084.mediawiki）
// 账户 0 首个接收地址 m/84'/0'/0'/0/0 的 P2WPKH 地址。
// 用途：确认本包 BTC 派生与 gasleak（core/crypto/derivation.js）及 BIP84 规范三方一致。
// 私钥 hex 由 wallet-sweeper 的纯 Python 实现独立算出（wsweep.derive.HDNode），
// 与地址一起构成对"助记词→私钥"和"私钥→地址"两段的双重钉死。
const (
	bip84Mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
	bip84PrivHex  = "4604b4b710fe91f584fff084e1a9159fe4f8408fff380596a604948474ce4fa3"
	bip84Address  = "bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu"
)

func TestBtcDeriveMatchesBIP84Vector(t *testing.T) {
	priv, err := BtcPrivateKeyByMnemonic(bip84Mnemonic)
	if err != nil {
		t.Fatalf("BtcPrivateKeyByMnemonic: %v", err)
	}
	if priv != bip84PrivHex {
		t.Fatalf("private key = %s, want %s", priv, bip84PrivHex)
	}
	addr, err := BtcAddressByPrivateKey(priv)
	if err != nil {
		t.Fatalf("BtcAddressByPrivateKey: %v", err)
	}
	if addr != bip84Address {
		t.Fatalf("address = %s, want %s", addr, bip84Address)
	}
}
