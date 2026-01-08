"""Constants for Pulp Tofu plugin tests."""

from urllib.parse import urljoin

from pulp_smash.constants import PULP_FIXTURES_BASE_URL
from pulp_smash.pulp3.constants import (
    BASE_DISTRIBUTION_PATH,
    BASE_PUBLICATION_PATH,
    BASE_REMOTE_PATH,
    BASE_REPO_PATH,
    BASE_CONTENT_PATH,
)

# FIXME: list any download policies supported by your plugin type here.
# If your plugin supports all download policies, you can import this
# from pulp_smash.pulp3.constants instead.
# DOWNLOAD_POLICIES = ["immediate", "streamed", "on_demand"]
DOWNLOAD_POLICIES = ["immediate"]

TOFU_CONTENT_NAME = "tofu.provider"

TOFU_CONTENT_PATH = urljoin(BASE_CONTENT_PATH, "tofu/providers/")

TOFU_REMOTE_PATH = urljoin(BASE_REMOTE_PATH, "tofu/tofu/")

TOFU_REPO_PATH = urljoin(BASE_REPO_PATH, "tofu/tofu/")

TOFU_PUBLICATION_PATH = urljoin(BASE_PUBLICATION_PATH, "tofu/tofu/")

TOFU_DISTRIBUTION_PATH = urljoin(BASE_DISTRIBUTION_PATH, "tofu/tofu/")

# FIXME: replace this with your own fixture repository URL and metadata
TOFU_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "tofu/")
"""The URL to a tofu repository."""

# FIXME: replace this with the actual number of content units in your test fixture
TOFU_FIXTURE_COUNT = 3
"""The number of content units available at :data:`TOFU_FIXTURE_URL`."""

TOFU_FIXTURE_SUMMARY = {TOFU_CONTENT_NAME: TOFU_FIXTURE_COUNT}
"""The desired content summary after syncing :data:`TOFU_FIXTURE_URL`."""

# FIXME: replace this with the location of one specific content unit of your choosing
TOFU_URL = urljoin(TOFU_FIXTURE_URL, "")
"""The URL to an tofu file at :data:`TOFU_FIXTURE_URL`."""

# FIXME: replace this with your own fixture repository URL and metadata
TOFU_INVALID_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "tofu-invalid/")
"""The URL to an invalid tofu repository."""

# FIXME: replace this with your own fixture repository URL and metadata
TOFU_LARGE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "tofu_large/")
"""The URL to a tofu repository containing a large number of content units."""

# FIXME: replace this with the actual number of content units in your test fixture
TOFU_LARGE_FIXTURE_COUNT = 25
"""The number of content units available at :data:`TOFU_LARGE_FIXTURE_URL`."""

# OpenTofu Registry constants
REGISTRY_URL = "https://registry.opentofu.org"
"""The OpenTofu registry URL."""
