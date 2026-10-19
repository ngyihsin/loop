---
type: repo
title: <git path>
tags: [cpp, python]
sources: [<Jenkinsfile path>, <build files>]
updated: YYYY-MM-DD
reviewed_by: unreviewed
---
# <git path>

## What it is / who consumes it

## Module map
| Directory | Responsibility | Language |
|---|---|---|

## Build
| Target (linux-x64 / linux-arm64 / windows-x64 / windows-arm64 / hexagon) | Build host | Env setup (toolchain file, vcvarsall, SDK) | Command | Time | Verified? |
|---|---|---|---|---|---|

## Test
| Kind (C++ unit / Python / on-device) | Runs on (x64 host / qemu / device) | Command | Time | Verified? |
|---|---|---|---|---|

## Gates (what `implement` must pass, cheapest first)
1. format / lint (changed files):
2. build:
3. unit tests:
4. on-device tests (via device skill):

## CI (Jenkins stages)
| Stage | Command | Platform | Hardware? |
|---|---|---|---|

## Pitfalls
