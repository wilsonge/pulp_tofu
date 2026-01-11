"""Constants for Pulp Tofu plugin tests."""

# import os
# from urllib.parse import urljoin

# PULP_FIXTURES_BASE_URL = os.environ.get(
#     "REMOTE_FIXTURES_ORIGIN", "https://fixtures.pulpproject.org/"
# )
#
# TOFU_FIXTURES_URL = urljoin(PULP_FIXTURES_BASE_URL, "tofu/")

# PULP_TOFU_BASE_URL = "/tofu/"

# Intended to be used with the XS specifier
TOFU_PROVIDER_VERSION = "3.7.2"
TOFU_PROVIDER_FILENAME = f"terraform-provider-random_{TOFU_PROVIDER_VERSION}_linux_arm.zip"
BASE_GITHUB_URL = "https://github.com/opentofu/terraform-provider-random"
TOFU_PROVIDER_URL = (
    f"{BASE_GITHUB_URL}/releases/download/v{TOFU_PROVIDER_VERSION}/" f"{TOFU_PROVIDER_FILENAME}"
)
TOFU_PROVIDER_SHA256 = "7371c2cc28c94deb9dba62fbac2685f7dde47f93019273a758dd5a2794f72919"

TOFU_PROVIDER_CREATE_DATA = {
    "namespace": "opentofu",
    "type": "random",
    "version": TOFU_PROVIDER_VERSION,
    "os": "linux",
    "arch": "arm",
    "filename": TOFU_PROVIDER_FILENAME,
    "shasum": TOFU_PROVIDER_SHA256,
    "protocols": ["5.0"],
    "relative_path": f"opentofu/random/{TOFU_PROVIDER_VERSION}/linux_arm/{TOFU_PROVIDER_FILENAME}",
}

TOFU_PROVIDER_DATA = {
    "namespace": "opentofu",
    "type": "random",
    "version": TOFU_PROVIDER_VERSION,
    "os": "linux",
    "arch": "arm",
    "filename": TOFU_PROVIDER_FILENAME,
    "shasum": TOFU_PROVIDER_SHA256,
    "protocols": ["5.0"],
}

# OpenTofu Registry constants
OPEN_TOFU_REGISTRY_URL = "https://registry.opentofu.org"
"""The OpenTofu registry URL."""
