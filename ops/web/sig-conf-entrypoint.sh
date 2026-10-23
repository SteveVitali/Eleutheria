#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# 40-sig-conf.sh — renders the sig-web nginx config at container start
# (P35.54 / REL-03b / ADR-220 D1). The stock nginx:alpine entrypoint runs
# /docker-entrypoint.d/*.sh before nginx, and the image ships envsubst —
# the per-revision env (SIG_LATEST_PUB, SIG_LATEST_LABEL, SIG_CONF_GEN,
# SIG_STAGING) substitutes into the G3 §4.2 template so every instance of
# a revision serves the same immutable config (NEW-4).
#
#   SIG_CONF_GEN + SIG_LATEST_PUB both set  → render the release template.
#   neither set                            → the committed legacy config,
#                                             verbatim (the dark cutover
#                                             roll is a later row's leg).
#   exactly one set                        → refuse to start: a half-set
#                                             revision env is a
#                                             misconfiguration, never a
#                                             silently half-templated site.
#
# The paths default to the image layout and are env-overridable so the
# unit tests can exercise the same branches on a scratch root.

set -eu

TEMPLATE="${SIG_NGINX_TEMPLATE:-/etc/nginx/sig-release.conf.template}"
HEADERS_TEMPLATE="${SIG_NGINX_HEADERS_TEMPLATE:-/etc/nginx/sig-headers.conf.template}"
LEGACY="${SIG_NGINX_LEGACY:-/etc/nginx/sig-legacy.conf}"
OUT="${SIG_NGINX_OUT:-/etc/nginx/nginx.conf}"
HEADERS_OUT="${SIG_NGINX_HEADERS_OUT:-/etc/nginx/sig-headers.conf}"

# shellcheck disable=SC2016  # envsubst takes the literal variable-name list
ENV_VARS='$SIG_LATEST_PUB $SIG_LATEST_LABEL $SIG_CONF_GEN $SIG_STAGING $SIG_ROBOTS_TAG_LINE'

if [ -n "${SIG_CONF_GEN:-}" ] || [ -n "${SIG_LATEST_PUB:-}" ]; then
    if [ -z "${SIG_CONF_GEN:-}" ] || [ -z "${SIG_LATEST_PUB:-}" ]; then
        echo "sig-web: half-set release environment" \
            "(SIG_CONF_GEN='${SIG_CONF_GEN:-unset}'" \
            "SIG_LATEST_PUB='${SIG_LATEST_PUB:-unset}')" \
            "— refusing to render" >&2
        exit 1
    fi
    SIG_STAGING="${SIG_STAGING:-0}"
    if [ "$SIG_STAGING" != "0" ] && [ "$SIG_STAGING" != "1" ]; then
        echo "sig-web: SIG_STAGING='${SIG_STAGING}' — only 0|1 render" >&2
        exit 1
    fi
    SIG_LATEST_LABEL="${SIG_LATEST_LABEL:-unsigned}"
    if [ "$SIG_STAGING" = "1" ]; then
        SIG_ROBOTS_TAG_LINE='add_header X-Robots-Tag "noindex" always;'
    else
        SIG_ROBOTS_TAG_LINE=''
    fi
    export SIG_LATEST_PUB SIG_LATEST_LABEL SIG_CONF_GEN SIG_STAGING SIG_ROBOTS_TAG_LINE
    envsubst "$ENV_VARS" < "$TEMPLATE" > "$OUT"
    envsubst "$ENV_VARS" < "$HEADERS_TEMPLATE" > "$HEADERS_OUT"
    echo "sig-web: rendered the release template" \
        "(conf_gen=${SIG_CONF_GEN} latest=${SIG_LATEST_PUB}" \
        "label=${SIG_LATEST_LABEL} staging=${SIG_STAGING})" >&2
else
    cp "$LEGACY" "$OUT"
    : > "$HEADERS_OUT"
    echo "sig-web: no release environment — the committed legacy config" \
        "verbatim (the cutover roll retires this branch)" >&2
fi
