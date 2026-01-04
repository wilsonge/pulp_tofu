"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/index.html
"""

from gettext import gettext as _

from rest_framework import serializers

from pulpcore.plugin import serializers as platform
from pulpcore.plugin.serializers import RepositoryVersionRelatedField

from . import models


class ProviderSerializer(platform.SingleArtifactContentSerializer):
    """
    A Serializer for Provider.

    Serializes OpenTofu provider content, which consists of a provider identified by
    namespace/type and a specific version for a platform (os/arch). Each provider
    has a single artifact (the provider zip archive).
    """

    namespace = serializers.CharField(
        help_text=_("The organization or user that publishes the provider"),
        required=True,
    )
    type = serializers.CharField(
        help_text=_("The provider type (e.g., 'aws', 'azurerm', 'google', 'random')"),
        required=True,
    )
    version = serializers.CharField(
        help_text=_("Semantic version number (semver 2.0)"),
        required=True,
    )
    os = serializers.CharField(
        help_text=_("Operating system (e.g., 'linux', 'darwin', 'windows')"),
        required=True,
    )
    arch = serializers.CharField(
        help_text=_("CPU architecture (e.g., 'amd64', 'arm', 'arm64')"),
        required=True,
    )
    filename = serializers.CharField(
        help_text=_("The filename for this provider's zip archive"),
        required=True,
    )
    shasum = serializers.CharField(
        help_text=_("SHA256 checksum for the provider package"),
        required=True,
    )
    protocols = serializers.JSONField(
        help_text=_("Supported OpenTofu provider API versions (e.g., ['4.0', '5.1'])"),
        required=True,
    )
    download_url = serializers.CharField(
        help_text=_("The URL from which the provider package can be downloaded"),
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def deferred_validate(self, data):
        """
        Validate and set the relative_path for the provider content.

        The relative_path is constructed from the provider's identifying fields
        to create a unique storage path: {namespace}/{type}/{version}/{os}_{arch}/{filename}
        """
        data = super().deferred_validate(data)

        # Construct the relative_path from the provider's identifying fields
        namespace = data.get("namespace")
        provider_type = data.get("type")
        version = data.get("version")
        os = data.get("os")
        arch = data.get("arch")
        filename = data.get("filename")

        # Set the relative_path for the artifact
        data["relative_path"] = f"{namespace}/{provider_type}/{version}/{os}_{arch}/{filename}"

        return data

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + (
            "namespace",
            "type",
            "version",
            "os",
            "arch",
            "filename",
            "shasum",
            "protocols",
            "download_url",
        )
        model = models.Provider


class TofuRemoteSerializer(platform.RemoteSerializer):
    """
    A Serializer for TofuRemote.

    Serializes a remote source for OpenTofu providers.
    """

    # Support on-demand download policies for provider artifacts
    policy = serializers.ChoiceField(
        help_text=_(
            "The policy to use when downloading content. The possible values include: "
            "'immediate', 'on_demand', and 'streamed'. 'immediate' is the default."
        ),
        choices=models.Remote.POLICY_CHOICES,
        default=models.Remote.IMMEDIATE,
    )

    class Meta:
        fields = platform.RemoteSerializer.Meta.fields
        model = models.TofuRemote


class TofuRepositorySerializer(platform.RepositorySerializer):
    """
    A Serializer for TofuRepository.

    Serializes repositories that contain OpenTofu provider content.
    """

    class Meta:
        fields = platform.RepositorySerializer.Meta.fields
        model = models.TofuRepository


class TofuPublicationSerializer(platform.PublicationSerializer):
    """
    A Serializer for TofuPublication.

    Serializes immutable snapshots of a TofuRepository that can be distributed.
    """

    class Meta:
        fields = platform.PublicationSerializer.Meta.fields
        model = models.TofuPublication


class TofuDistributionSerializer(platform.DistributionSerializer):
    """
    A Serializer for TofuDistribution.

    Serializes distributions that serve TofuPublications via the OpenTofu Provider
    Registry Protocol.
    """

    publication = platform.DetailRelatedField(
        required=False,
        help_text=_("Publication to be served"),
        view_name_pattern=r"publications(-.*/.*)?-detail",
        queryset=models.Publication.objects.exclude(complete=False),
        allow_null=True,
    )

    repository_version = RepositoryVersionRelatedField(
        required=False,
        help_text=_("RepositoryVersion to be served"),
        allow_null=True,
    )

    class Meta:
        fields = platform.DistributionSerializer.Meta.fields + (
            "publication",
            "repository_version",
        )
        model = models.TofuDistribution
