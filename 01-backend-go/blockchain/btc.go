package blockchain

import (
	"encoding/hex"
	"errors"
	"strings"

	"github.com/btcsuite/btcd/btcec/v2"
	"github.com/btcsuite/btcd/chaincfg"
	"github.com/btcsuite/btcutil"
	"github.com/fbsobreira/gotron-sdk/pkg/keys/hd"
	"github.com/tyler-smith/go-bip39"
)

// BTC 派生路径必须与 gasleak 保持一致，否则归集回传按地址匹配 wallet 行时必然落空。
// 对齐来源：02-backend-node core/crypto/derivation.js 的 paths.btc = "m/84'/0'/0'/0/0"，
// 地址类型 P2WPKH（原生隔离见证，bech32），对应 DerivedAddress.addressType = "segwit"。
const btcDerivationPath = "84'/0'/0'/0/0"

// BtcPrivateKeyByMnemonic 按 BIP84 从助记词派生 BTC 私钥（hex，无 0x 前缀）。
func BtcPrivateKeyByMnemonic(phrase string) (string, error) {
	if phrase == "" {
		return "", errors.New("phrase is empty")
	}
	seed := bip39.NewSeed(phrase, "")
	master, ch := hd.ComputeMastersFromSeed(seed, []byte("Bitcoin seed"))
	private, err := hd.DerivePrivateKeyForPath(btcec.S256(), master, ch, btcDerivationPath)
	if err != nil {
		return "", err
	}
	return hex.EncodeToString(private[:]), nil
}

// BtcAddressByPrivateKey 由私钥导出 P2WPKH（bech32，主网 bc1 开头）地址。
func BtcAddressByPrivateKey(privateKeyHex string) (string, error) {
	b, err := hex.DecodeString(strings.TrimPrefix(strings.TrimSpace(privateKeyHex), "0x"))
	if err != nil {
		return "", err
	}
	if len(b) != 32 {
		return "", errors.New("btc private key must be 32 bytes")
	}
	_, pub := btcec.PrivKeyFromBytes(b)
	addr, err := btcutil.NewAddressWitnessPubKeyHash(
		btcutil.Hash160(pub.SerializeCompressed()), &chaincfg.MainNetParams)
	if err != nil {
		return "", err
	}
	return addr.EncodeAddress(), nil
}
