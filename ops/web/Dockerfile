# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# The sig-web image (P31.15 / SURFACE.2, ADR-R9-TILES). It serves the public
# static site from /mnt/sig-web — the gcsfuse mount of the <project>-sig-web
# bucket the deploy script attaches (P30.3: "the bucket sync IS the deploy";
# the hand-made live service was stock nginx:1.27-alpine + that volume).
#
# Brotli is COMPILED, not packaged: Alpine's nginx-mod-http-brotli modules target
# a different nginx ABI than the runtime image ships, so load_module would fail.
# This build downloads the sha256-verified nginx source matching the runtime
# base EXACTLY, builds the brotli C library + the two ngx_brotli dynamic modules,
# and runs the same nginx base with them loaded (ops/web/nginx.conf).
#
# To bump: update the *_REF/VERSION + the matching tarball sha256
# (`curl -fsSL <url> | sha256sum`). BROTLI_REF must stay the commit
# ngx_brotli@NGX_BROTLI_REF pins as its deps/brotli git submodule
# (the GitHub tarball has no submodule contents — we lay it in ourselves).

# --- module build stage ------------------------------------------------------
FROM alpine:3.21 AS brotli-build

ARG NGINX_VERSION=1.27.5
ARG NGINX_SHA256=e96acebb9c2a6db8a000c3dd1b32ecba1b810f0cd586232d4d921e376674dd0e
# google/ngx_brotli @ a71f9312 — its deps/brotli submodule pins BROTLI_REF.
ARG NGX_BROTLI_REF=a71f9312c2deb28875acc7bacfdd5695a111aa53
ARG NGX_BROTLI_SHA256=1d21be34f3b7b6d05a8142945e59b3a47665edcdfe0f3ee3d3dbef121f90c08c
# google/brotli @ ed738e8 — the exact commit ngx_brotli's gitlink names.
ARG BROTLI_REF=ed738e842d2fbdf2d6459e39267a633c4a9b2f5d
ARG BROTLI_SHA256=aaa739962a45b508b2e783b915e6b2b57ed3b12bd4b0feac73acfb144dffa54f

RUN apk add --no-cache build-base ca-certificates cmake curl pcre2-dev zlib-dev

WORKDIR /build
RUN curl -fsSL "https://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz" \
      -o nginx.tar.gz \
 && echo "${NGINX_SHA256}  nginx.tar.gz" | sha256sum -c - \
 && tar xzf nginx.tar.gz \
 && curl -fsSL \
      "https://github.com/google/ngx_brotli/archive/${NGX_BROTLI_REF}.tar.gz" \
      -o ngx_brotli.tar.gz \
 && echo "${NGX_BROTLI_SHA256}  ngx_brotli.tar.gz" | sha256sum -c - \
 && tar xzf ngx_brotli.tar.gz \
 && mv "ngx_brotli-${NGX_BROTLI_REF}" ngx_brotli \
 && mkdir -p ngx_brotli/deps/brotli \
 && curl -fsSL \
      "https://github.com/google/brotli/archive/${BROTLI_REF}.tar.gz" \
      -o brotli.tar.gz \
 && echo "${BROTLI_SHA256}  brotli.tar.gz" | sha256sum -c - \
 && tar xzf brotli.tar.gz -C ngx_brotli/deps/brotli --strip-components=1 \
 && rm -f nginx.tar.gz ngx_brotli.tar.gz brotli.tar.gz

# The brotli C library where ngx_brotli's config script looks for it:
# static archives at deps/brotli/out (-lbrotlienc -lbrotlicommon).
RUN cmake -S ngx_brotli/deps/brotli -B ngx_brotli/deps/brotli/out \
      -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
      -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
 && cmake --build ngx_brotli/deps/brotli/out --parallel "$(nproc)" \
      --target brotlienc brotlicommon

# --with-compat dynamic modules: loadable in the official same-version binary.
RUN cd "nginx-${NGINX_VERSION}" \
 && ./configure --with-compat --add-dynamic-module=../ngx_brotli \
 && make -j"$(nproc)" modules

# --- runtime stage: the same nginx the live service already runs -------------
FROM nginx:1.27.5-alpine

COPY --from=brotli-build \
     /build/nginx-1.27.5/objs/ngx_http_brotli_filter_module.so \
     /build/nginx-1.27.5/objs/ngx_http_brotli_static_module.so \
     /usr/lib/nginx/modules/
COPY ops/web/nginx.conf /etc/nginx/nginx.conf

# Cloud Run provides $PORT; the config listens on 8080. The site root is the
# gcsfuse-mounted bucket at /mnt/sig-web (ops/gcp/web.sh).
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
