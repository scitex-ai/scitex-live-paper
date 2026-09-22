"""Smoke-test hermeticity notes (PS-211).

CLI happy-path tests must not touch the real home directory, real
credentials, or the network. This package's smoke layer only drives
`--help` / `--version`, which need no fixtures — this file exists so
the hermeticity contract has a home when the layer grows.
"""
