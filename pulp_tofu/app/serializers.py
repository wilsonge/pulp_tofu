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


class TofuContentSerializer(platform.SingleArtifactContentSerializer):
    """
    A Serializer for TofuContent.

    Serializes OpenTofu module content, which consists of a module identified by
    namespace/name/system and a specific version. Each module has a single artifact
    (the module archive/source).
    """

    namespace = serializers.CharField(
        help_text=_("The organization or user that owns the module"),
        required=True,
    )
    name = serializers.CharField(
        help_text=_("The module name"),
        required=True,
    )
    system = serializers.CharField(
        help_text=_("The target system (e.g., aws, azurerm, gcp)"),
        required=True,
    )
    version = serializers.CharField(
        help_text=_("Semantic version number (semver 2.0)"),
        required=True,
    )
    download_url = serializers.CharField(
        help_text=_("The location from which the module version's source can be downloaded"),
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        fields = platform.SingleArtifactContentSerializer.Meta.fields + (
            "namespace",
            "name",
            "system",
            "version",
            "download_url",
        )
        model = models.TofuContent


class TofuRemoteSerializer(platform.RemoteSerializer):
    """
    A Serializer for TofuRemote.

    Serializes a remote source for OpenTofu modules, including support for
    selective syncing via include/exclude patterns.
    """

    includes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text=_(
            "List of module patterns to include during sync. "
            "Patterns support wildcards, e.g., 'hashicorp/consul/*', '*/vpc/aws'. "
            "If empty, all modules are included (unless excluded)."
        ),
    )
    excludes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text=_(
            "List of module patterns to exclude during sync. "
            "Exclusions are applied after inclusions."
        ),
    )

    # Support on-demand download policies for module artifacts
    policy = serializers.ChoiceField(
        help_text=_(
            "The policy to use when downloading content. The possible values include: "
            "'immediate', 'on_demand', and 'streamed'. 'immediate' is the default."
        ),
        choices=models.Remote.POLICY_CHOICES,
        default=models.Remote.IMMEDIATE,
    )

    class Meta:
        fields = platform.RemoteSerializer.Meta.fields + (
            "includes",
            "excludes",
        )
        model = models.TofuRemote


class TofuRepositorySerializer(platform.RepositorySerializer):
    """
    A Serializer for TofuRepository.

    Serializes repositories that contain OpenTofu module content.
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

    Serializes distributions that serve TofuPublications via the OpenTofu Module
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
