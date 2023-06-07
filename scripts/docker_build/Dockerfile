# SPDX-License-Identifier: BSD-3-Clause
# Copyright(c) 2023 Intel Corporation. All rights reserved.
#
# Defines a docker image that can build Sound Open Firmware documentation
#
# Usage:
# create parent directory for sof and sof-docs repository (e.g. thesofproject)
# clone sof repository to thesofproject\sof folder
# clone sof-docs repository to thesofproject\sof-docs folder
# build docker image from parent directory .\thesofproject:
# > docker build -t ubuntu-sofdocs -f ./sof-docs/scripts/docker_build/Dockerfile ./
# run the image container:
# > docker run -d --name sofdocs_container ubuntu-sofdocs sleep infinity
# copy build output from container to host:
# > docker cp sofdocs_container:/home/thesofproject/sof/doc ./sof/
# > docker cp sofdocs_container:/home/thesofproject/sof-docs/_build ./sof-docs/
# stop the container:
# docker stop sofdocs_container
#
# Note: The first build can take time to setup ubuntu and install tools,
# but each next one will repeat only copy and build steps.
#

FROM dokken/ubuntu-22.04

# Set image working directory
WORKDIR /home/thesofproject

RUN apt-get update

# Install sof-docs build tools
RUN apt-get install -y python3.6
RUN apt-get install -y doxygen python3-pip python3-wheel make \
   default-jre graphviz cmake ninja-build

# Copy sof-docs file with dependency tools list
COPY ./sof-docs/scripts/requirements.txt /home/thesofproject/sof-docs/scripts/requirements.txt

# Install sof-docs requirements tools
RUN pip3 install --user -r /home/thesofproject/sof-docs/scripts/requirements.txt

# Directly install sphinx to add 'sphinx-build' to the system
RUN apt-get install -y python3-sphinx

# Copy sof source code from host to image
COPY ./sof/ /home/thesofproject/sof/

# Build API documentation from SOF source (Doxygen)
RUN cmake -S sof/doc -B sof/doc -GNinja
RUN ninja -C sof/doc -v doc

# Copy sof-docs source code from host to image
COPY ./sof-docs/ /home/thesofproject/sof-docs/

# Build sof-docs, ignore eventual errors to complete image creation
RUN make -C sof-docs VERBOSE=1 html; exit 0
