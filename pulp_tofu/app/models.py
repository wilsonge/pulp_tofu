"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/index.html
"""

from logging import getLogger

from django.db import models

from pulpcore.plugin.models import (
    Content,
    Remote,
    Repository,
    Publication,
    Distribution,
)
from pulpcore.plugin.util import get_domain_pk

logger = getLogger(__name__)


class Provider(Content):
    """
    The "tofu" content type representing an OpenTofu provider package.

    Based on the OpenTofu Provider Registry Protocol, each provider package is uniquely
    identified by the combination of namespace, type, version, os, and arch.

    Provider addresses follow the format: hostname/namespace/type
    where:
    - namespace: The organization or user that publishes the provider (e.g., "hashicorp")
    - type: The provider type (e.g., "aws", "azurerm", "google", "random")

    Each provider version can have multiple packages for different platforms (os/arch combinations).
    """

    TYPE = "tofu"

    # Core provider identification fields
    namespace = models.TextField(help_text="The organization or user that publishes the provider")
    type = models.TextField(
        help_text="The provider type (e.g., 'aws', 'azurerm', 'google', 'random')"
    )
    version = models.TextField(help_text="Semantic version number (semver 2.0)")

    # Platform-specific fields
    os = models.TextField(help_text="Operating system (e.g., 'linux', 'darwin', 'windows')")
    arch = models.TextField(help_text="CPU architecture (e.g., 'amd64', 'arm', 'arm64')")

    # Provider package metadata
    filename = models.TextField(help_text="The filename for this provider's zip archive")
    shasum = models.TextField(help_text="SHA256 checksum for the provider package")
    protocols = models.JSONField(
        default=list, help_text="Supported OpenTofu provider API versions (e.g., ['4.0', '5.1'])"
    )
    download_url = models.TextField(
        null=True, blank=True, help_text="The URL from which the provider package can be downloaded"
    )
    _pulp_domain = models.ForeignKey("core.Domain", default=get_domain_pk, on_delete=models.PROTECT)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = ("namespace", "type", "version", "os", "arch", "_pulp_domain")


class TofuPublication(Publication):
    """
    A Publication for Provider.

    Define any additional fields for your new publication if needed.
    """

    TYPE = "tofu"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class TofuRemote(Remote):
    """
    A Remote for Provider.

    Connects to an OpenTofu provider registry to sync provider packages.
    The URL should point to the base URL of the provider registry API
    (typically discovered via the service discovery protocol at /.well-known/terraform.json).
    """

    TYPE = "tofu"
    DEFAULT_DOWNLOAD_CONCURRENCY = 10

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class TofuRepository(Repository):
    """
    A Repository for Provider.

    Define any additional fields for your new repository if needed.
    """

    TYPE = "tofu"

    CONTENT_TYPES = [Provider]

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class TofuDistribution(Distribution):
    """
    A Distribution for Provider.

    Serves OpenTofu providers using the Provider Registry Protocol.
    The content handler routes requests to the appropriate endpoints:
    - /.well-known/terraform.json (service discovery)
    - /:namespace/:type/versions (list versions)
    - /:namespace/:type/:version/download/:os/:arch (download package)
    """

    TYPE = "tofu"

    def content_handler(self, path):
        """
        Route content requests to the OpenTofu provider registry protocol handler.

        Args:
            path: The path portion of the URL

        Returns:
            The content handler function
        """
        from pulp_tofu.app.content import tofu_content_handler

        return tofu_content_handler

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
