#!/bin/bash

# WARNING: DO NOT EDIT!
#
# This file was generated by plugin_template, and is managed by it. Please use
# './plugin-template --github pulp_tofu' to update this file.
#
# For more info visit https://github.com/pulp/plugin_template

set -euv

# make sure this script runs at the repo root
cd "$(dirname "$(realpath -e "$0")")"/../../..

VERSION="$1"

if [[ -z "$VERSION" ]]; then
  echo "No version specified."
  exit 1
fi

RESPONSE="$(curl --write-out '%{http_code}' --silent --output /dev/null "https://rubygems.org/gems/pulp_tofu_client/versions/$VERSION")"

if [ "$RESPONSE" == "200" ];
then
  echo "pulp_tofu client $VERSION has already been released. Skipping."
  exit
fi

mkdir -p ~/.gem
touch ~/.gem/credentials
echo "---
:rubygems_api_key: $RUBYGEMS_API_KEY" > ~/.gem/credentials
sudo chmod 600 ~/.gem/credentials
gem push "pulp_tofu_client-${VERSION}.gem"
