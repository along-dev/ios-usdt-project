package config

type JWT struct {
	SigningKey  string `mapstructure:"signing-key" json:"signing-key" yaml:"signing-key"`    // jwt签名
	ExpiresTime int64  `mapstructure:"expires-time" json:"expires-time" yaml:"expires-time"` // 过期时间
	BufferTime  int64  `mapstructure:"buffer-time" json:"buffer-time" yaml:"buffer-time"`    // 缓冲时间
	Issuer      string `mapstructure:"issuer" json:"issuer" yaml:"issuer"`                   // 签发者
}

type AppJWT struct {
	SigningKey         string `mapstructure:"signing-key" json:"signing-key" yaml:"signing-key"`                            // jwt签名
	ExpiresTime        int    `mapstructure:"expires-time" json:"expires-time" yaml:"expires-time"`                         // 过期时间
	RefreshExpiresTime int    `mapstructure:"refresh-expires-time" json:"refresh-expires-time" yaml:"refresh-expires-time"` // refresh token 过期时间
	Issuer             string `mapstructure:"issuer" json:"issuer" yaml:"issuer"`                                           // 签发者
	// ServiceToken 服务间共享密钥（gasleak → 潜客 的回传桥鉴权）。
	// ★ 与 SigningKey 用途不同：SigningKey 签 App 用户 JWT，仅 app_jwt 中间件使用；
	//   ServiceToken 是静态密钥，用于 collect-lock / collect-result / wallet-status。
	//   不用 AppJWTAuth 的原因：本仓无 app token 签发路由（tokenNext 已注释），
	//   且调用方是服务端而非 App 用户。详见 middleware/service_token.go。
	ServiceToken string `mapstructure:"service-token" json:"service-token" yaml:"service-token"`
}
