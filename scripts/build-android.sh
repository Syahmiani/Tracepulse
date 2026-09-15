#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -d /usr/lib/jvm/java-21-openjdk-amd64 ]]; then
    export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
elif [[ -d /usr/lib/jvm/java-21-openjdk ]]; then
    export JAVA_HOME=/usr/lib/jvm/java-21-openjdk
elif [[ -d /usr/lib/jvm/java-17-openjdk-amd64 ]]; then
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
elif [[ -d /usr/lib/jvm/java-17-openjdk ]]; then
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk
else
    echo "Java 17 or 21 is required to build the Android app." >&2
    echo "Install it with: sudo apt update && sudo apt install -y openjdk-21-jdk" >&2
    exit 2
fi
cd "$repo_root/frontend"
npm run build
npx cap sync android
cd android
exec ./gradlew assembleDebug --no-daemon
