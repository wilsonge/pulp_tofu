"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/index.html
"""

from logging import getLogger

from django.db import models

from pulpcore.plugin.models import (
    Content,
    ContentArtifact,
    Remote,
    Repository,
    Publication,
    Distribution,
)

logger = getLogger(__name__)


class TofuContent(Content):
    """
    The "tofu" content type representing an OpenTofu module.

    Based on the OpenTofu Module Registry Protocol, each module is uniquely
    identified by the combination of namespace, name, system, and version.

    Module addresses follow the format: hostname/namespace/name/system
    where:
    - namespace: The organization or user that owns the module
    - name: The module name (the abstraction being created)
    - system: The target system (e.g., aws, azurerm, gcp)
    - version: Semantic version number (semver 2.0)
    """

    TYPE = "tofu"

    # Core module identification fields
    namespace = models.TextField(
        help_text="The organization or user that owns the module"
    )
    name = models.TextField(
        help_text="The module name"
    )
    system = models.TextField(
        help_text="The target system (e.g., aws, azurerm, gcp)"
    )
    version = models.TextField(
        help_text="Semantic version number (semver 2.0)"
    )

    # Download location for the module source
    download_url = models.TextField(
        null=True,
        blank=True,
        help_text="The location from which the module version's source can be downloaded"
    )

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = ("namespace", "name", "system", "version")


class TofuPublication(Publication):
    """
    A Publication for TofuContent.

    Define any additional fields for your new publication if needed.
    """

    TYPE = "tofu"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class TofuRemote(Remote):
    """
    A Remote for TofuContent.

    Connects to an OpenTofu module registry to sync modules.
    The URL should point to the base URL of the module registry API
    (typically discovered via the service discovery protocol at /.well-known/terraform.json).
    """

    TYPE = "tofu"
    DEFAULT_DOWNLOAD_CONCURRENCY = 10

    # Include/exclude patterns for selective syncing
    includes = models.JSONField(
        default=list,
        help_text="List of module patterns to include (e.g., ['hashicorp/consul/*', '*/vpc/aws'])"
    )
    excludes = models.JSONField(
        default=list,
        help_text="List of module patterns to exclude"
    )

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class TofuRepository(Repository):
    """
    A Repository for TofuContent.

    Define any additional fields for your new repository if needed.
    """

    TYPE = "tofu"

    CONTENT_TYPES = [TofuContent]

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class TofuDistribution(Distribution):
    """
    A Distribution for TofuContent.

    Define any additional fields for your new distribution if needed.
    """

    TYPE = "tofu"

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
