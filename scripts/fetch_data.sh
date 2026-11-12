#!/usr/bin/env bash
# Downloads the Cookie Cats A/B test data into seeds/ and checks it is the expected file.
set -euo pipefail
cd "$(dirname "$0")/.."
URL="https://raw.githubusercontent.com/ryanschaub/Mobile-Games-A-B-Testing-with-Cookie-Cats/master/cookie_cats.csv"
SHA="5ab54d761fbddcd50de7b88e4eaf7837cba4569474f50c043a4d17ee342c46bd"
curl -sSfL -o seeds/cookie_cats.csv "$URL"
echo "$SHA  seeds/cookie_cats.csv" | shasum -a 256 -c -
