package request

import (
	j2 "github.com/golang-jwt/jwt/v5"
)

type AppClaims struct {
	UserId     int
	CreateTime string
	LoginTime  string
	j2.RegisteredClaims
}

type AppRefreshClaims struct {
	AccessToken string
	j2.RegisteredClaims
}
