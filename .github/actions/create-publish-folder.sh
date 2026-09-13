#!/bin/bash
# create publish folder for github.io

mkdir _build/latest
mv -v _build/html/* _build/latest
mv _build/latest _build/html/
touch _build/html/.nojekyll
cp scripts/publish-README.md _build/html/README.md
cp scripts/publish-index.html _build/html/index.html
