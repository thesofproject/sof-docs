#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(c) 2023 Intel Corporation. All rights reserved.

build_docs_only="FALSE"
if [ $# -eq 1 ] && [[ $1 = "docs" ]]; then
  build_docs_only="TRUE"
  echo "Re-build sof-docs only."
fi

# Build documentation using docker image
docker build -t ubuntu-sofdocs -f ./sof-docs/scripts/docker_build/Dockerfile ./

# Run image container to copy output.
# Add sleep infinity to keep container running.
docker run -d --rm --name sofdocs_container ubuntu-sofdocs sleep infinity

if [ $build_docs_only = "FALSE" ]; then
  echo "Copy SOF Doxygen generated documentation from container to host ./sof/doc/"
  docker cp sofdocs_container:/home/thesofproject/sof/doc ./sof/
fi

echo "Copy SOF-DOCS generated documentation from container to host ./sof-docs/_build .."
docker cp sofdocs_container:/home/thesofproject/sof-docs/_build ./sof-docs/

echo "Stop the sofdocs_container"
docker stop sofdocs_container

# It is required to prevent stacking of images for each build run
echo "Remove dangling docker images"
docker image prune --force

echo "Press key to exit..."
read -n 1 k <&1
