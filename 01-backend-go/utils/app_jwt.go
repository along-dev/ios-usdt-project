package utils

import (
	"context"
	"crypto"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"errors"
	"github.com/flipped-aurora/gin-vue-admin/server/api/v1/request"
	"github.com/golang-jwt/jwt/v5"
	"sort"
	"time"

	"github.com/flipped-aurora/gin-vue-admin/server/global"
)

type AppJwt struct {
	SigningKey []byte
}

func NewAppJWT() *AppJwt {
	return &AppJwt{
		[]byte(global.GVA_CONFIG.AppJwt.SigningKey),
	}
}

func (j *AppJwt) CreateToken(_createTime, _loginTime string, _userId, _expiresAt int) (string, error) {
	claims := request.AppClaims{
		CreateTime: _createTime,
		LoginTime:  _loginTime,
		UserId:     _userId,
		RegisteredClaims: jwt.RegisteredClaims{
			NotBefore: jwt.NewNumericDate(time.Now()),                                              // 签名生效时间
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Second * time.Duration(_expiresAt))), // 过期时间 秒  配置文件
			Issuer:    global.GVA_CONFIG.AppJwt.Issuer,                                             // 签名的发行者
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	newAccessToken, err := token.SignedString(j.SigningKey)
	if err != nil {
		return "", err
	}
	err = global.GVA_REDIS.Set(context.Background(), newAccessToken, _userId, time.Duration(_expiresAt)*time.Second).Err()
	if err != nil {
		return "", errors.New("redis save jwt fail")
	}
	return newAccessToken, nil
}

func (j *AppJwt) CreateRefreshToken(_token string, _userId, _expiresAt int) (string, error) {
	claims := request.AppRefreshClaims{
		AccessToken: _token,
		RegisteredClaims: jwt.RegisteredClaims{
			NotBefore: jwt.NewNumericDate(time.Now()),                                              // 签名生效时间
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Second * time.Duration(_expiresAt))), // 过期时间 秒  配置文件
			Issuer:    global.GVA_CONFIG.AppJwt.Issuer,                                             // 签名的发行者
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	newRefreshToken, err := token.SignedString(j.SigningKey)
	if err != nil {
		return "", err
	}
	err = global.GVA_REDIS.Set(context.Background(), newRefreshToken, _userId, time.Duration(_expiresAt)*time.Second).Err()
	if err != nil {
		return "", errors.New("redis save jwt fail")
	}
	return newRefreshToken, nil
}

// 解析 token
func (j *AppJwt) ParseToken(accessToken string) (*request.AppClaims, error) {
	token, err := jwt.ParseWithClaims(accessToken, &request.AppClaims{}, func(token *jwt.Token) (i interface{}, e error) {
		return j.SigningKey, nil
	})
	if claims, ok := token.Claims.(*request.AppClaims); ok && token.Valid {
		return claims, nil
	} else if err != nil {
		if errors.Is(err, jwt.ErrTokenExpired) {
			return claims, TokenExpired
		}
	}
	return nil, TokenInvalid
}

func (j *AppJwt) ParseRefreshToken(refreshToken string) (*request.AppRefreshClaims, error) {
	token, err := jwt.ParseWithClaims(refreshToken, &request.AppRefreshClaims{}, func(token *jwt.Token) (i interface{}, e error) {
		return j.SigningKey, nil
	})
	if claims, ok := token.Claims.(*request.AppRefreshClaims); ok && token.Valid {
		return claims, nil
	}
	return nil, err
}

// 登录验签
func VerifyLoginSign(params map[string]string, sign string) (err error) {
	//验签
	publicBlock, _ := pem.Decode(global.PUBLIC_KEY_STR)
	if publicBlock == nil || publicBlock.Type != "RSA PUBLIC KEY" {
		return errors.New("failed to decode PEM block containing public key")
	}
	publicKey, err := x509.ParsePKCS1PublicKey(publicBlock.Bytes)
	if err != nil {
		return err
	}

	// 和签名步骤相同，对收到的请求参数按照字母顺序进行排序
	keys := make([]string, 0, len(params))
	for k := range params {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	var signature = ""
	i := 0
	for _, k := range keys {
		v := params[k]
		if i != 0 {
			signature += "&"
		}
		signature += k
		signature += "="
		signature += v
		i++
	}
	// 和签名步骤相同，将排序后的signature进行hash操作
	h := sha256.New()
	h.Write([]byte(signature))
	Sha256Code := h.Sum(nil)
	// 对签名进行base64解码
	decodeSignature, err := base64.StdEncoding.DecodeString(sign)
	// 使用rsa验签函数
	// 第一个参数是公钥
	// 第二个参数是hash函数
	// 第三个参数是被hash函数处理过的原始输入
	// 第四个参数是被处理过的签名
	err = rsa.VerifyPKCS1v15(publicKey, crypto.SHA256, Sha256Code, decodeSignature)
	if err != nil { // 验证失败
		return err
	}
	return nil // 验证成功
}
