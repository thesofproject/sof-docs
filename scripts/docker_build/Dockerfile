# SPDX-License-Identifier: BSD-3-Clause
# Copyright(c) 2023 Intel Corporation. All rights reserved.
#
# Defines a docker image that can build Sound Open Firmware documentation
#
# Usage:
# create parent directory for sof and sof-docs repository (e.g. thesofproject)
# clone sof repository to thesofproject/sof folder
# clone sof-docs repository to thesofproject/sof-docs folder
# build docker image from parent directory ./thesofproject:
# > docker build -t ubuntu-sofdocs -f ./sof-docs/scripts/docker_build/Dockerfile ./
# run the image container:
# > docker run -d --name sofdocs_container ubuntu-sofdocs sleep infinity
# copy build output from container to host:
# > docker cp sofdocs_container:/home/thesofproject/sof/build_doxygen ./sof/
# > docker cp sofdocs_container:/home/thesofproject/sof-docs/_build ./sof-docs/
# stop the container:
# docker stop sofdocs_container
#
# Note: The first build can take time to setup ubuntu and install tools,
# but each next one will repeat only copy and build steps.
#

FROM ubuntu:24.04

# Set image working directory
WORKDIR /home/thesofproject

# Install sof-docs build tools. Ubuntu 24.04 ships Python 3.12, which
# satisfies the supported lockfile (Sphinx 9 requires Python >= 3.12).
RUN apt-get update && apt-get install -y --no-install-recommends \
   python3 python3-venv python3-pip \
   doxygen make default-jre graphviz cmake ninja-build \
   && rm -rf /var/lib/apt/lists/*

# Install the Python tools into a venv (avoids Ubuntu's PEP 668
# "externally managed environment" restriction) and put it first on PATH.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install the pinned documentation toolchain from the lockfile. Copying
# only these two files first lets Docker cache the install layer across
# source changes.
COPY ./sof-docs/scripts/requirements.txt ./sof-docs/scripts/constraints.txt \
   /home/thesofproject/sof-docs/scripts/
RUN pip install --no-cache-dir \
   -r sof-docs/scripts/requirements.txt -c sof-docs/scripts/constraints.txt

# Copy sof source code from host to image
COPY ./sof/ /home/thesofproject/sof/

# Build API documentation from SOF source (Doxygen). Build out of source
# into sof/build_doxygen, which is where the sof-docs Makefile expects it
# (its SOF_DOC_BUILD default is ../sof/build_doxygen).
RUN cmake -GNinja -S sof/doc -B sof/build_doxygen
RUN ninja -C sof/build_doxygen -v doc

# Copy sof-docs source code from host to image
COPY ./sof-docs/ /home/thesofproject/sof-docs/

# Build sof-docs, ignore eventual errors to complete image creation
RUN make -C sof-docs VERBOSE=1 html; exit 0
