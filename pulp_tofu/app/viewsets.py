"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/index.html
"""

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from pulpcore.plugin.viewsets import RemoteFilter
from pulpcore.plugin import viewsets as core
from pulpcore.plugin.actions import ModifyRepositoryActionMixin
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositorySyncURLSerializer,
)
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.models import ContentArtifact

from . import models, serializers, tasks


class TofuContentFilter(core.ContentFilter):
    """
    FilterSet for TofuContent.

    Allows filtering modules by namespace, name, system, and version.
    """

    class Meta:
        model = models.TofuContent
        fields = [
            "namespace",
            "name",
            "system",
            "version",
        ]


class TofuContentViewSet(core.ContentViewSet):
    """
    A ViewSet for TofuContent.

    Provides REST API endpoints for managing OpenTofu module content units.

    Endpoint: /pulp/api/v3/content/tofu/units/
    """

    endpoint_name = "tofu"
    queryset = models.TofuContent.objects.all()
    serializer_class = serializers.TofuContentSerializer
    filterset_class = TofuContentFilter

    @transaction.atomic
    def create(self, request):
        """
        Create a TofuContent unit with its associated artifact.

        Each OpenTofu module has a single artifact (the module archive/source).
        The artifact is associated with a relative path based on the module's
        namespace, name, system, and version.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract the artifact from validated data
        _artifact = serializer.validated_data.pop("_artifact", None)

        # Save the content unit
        content = serializer.save()

        # If the content was created and has an artifact, create the ContentArtifact
        if content.pk and _artifact:
            # Build the relative path for the artifact
            # Format: namespace/name/system/version/module.tar.gz
            relative_path = f"{content.namespace}/{content.name}/{content.system}/{content.version}/module.tar.gz"

            ContentArtifact.objects.create(
                artifact=_artifact,
                content=content,
                relative_path=relative_path,
            )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class TofuRemoteFilter(RemoteFilter):
    """
    A FilterSet for TofuRemote.

    Allows filtering remotes by name and URL.
    """

    class Meta:
        model = models.TofuRemote
        fields = RemoteFilter.Meta.fields


class TofuRemoteViewSet(core.RemoteViewSet):
    """
    A ViewSet for TofuRemote.

    Provides REST API endpoints for managing OpenTofu module registry remotes.
    """

    endpoint_name = "tofu"
    queryset = models.TofuRemote.objects.all()
    serializer_class = serializers.TofuRemoteSerializer
    filterset_class = TofuRemoteFilter


class TofuRepositoryViewSet(core.RepositoryViewSet, ModifyRepositoryActionMixin):
    """
    A ViewSet for TofuRepository.

    Provides REST API endpoints for managing OpenTofu module repositories,
    including sync operations.

    Endpoint: /pulp/api/v3/repositories/tofu/
    """

    endpoint_name = "tofu"
    queryset = models.TofuRepository.objects.all()
    serializer_class = serializers.TofuRepositorySerializer

    # This decorator is necessary since a sync operation is asyncrounous and returns
    # the id and href of the sync task.
    @extend_schema(
        description="Trigger an asynchronous task to sync content.",
        summary="Sync from remote",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=RepositorySyncURLSerializer)
    def sync(self, request, pk):
        """
        Dispatches a sync task.
        """
        repository = self.get_object()
        serializer = RepositorySyncURLSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        remote = serializer.validated_data.get("remote")
        mirror = serializer.validated_data.get("mirror")

        result = dispatch(
            tasks.synchronize,
            [repository, remote],
            kwargs={
                "remote_pk": str(remote.pk),
                "repository_pk": str(repository.pk),
                "mirror": mirror,
            },
        )
        return core.OperationPostponedResponse(result, request)


class TofuRepositoryVersionViewSet(core.RepositoryVersionViewSet):
    """
    A ViewSet for TofuRepositoryVersion.

    Provides REST API endpoints for viewing OpenTofu repository versions.
    Each version is an immutable snapshot of repository content.
    """

    parent_viewset = TofuRepositoryViewSet


class TofuPublicationViewSet(core.PublicationViewSet):
    """
    A ViewSet for TofuPublication.

    Provides REST API endpoints for creating and managing publications of
    OpenTofu module repositories.

    Endpoint: /pulp/api/v3/publications/tofu/
    """

    endpoint_name = "tofu"
    queryset = models.TofuPublication.objects.exclude(complete=False)
    serializer_class = serializers.TofuPublicationSerializer

    # This decorator is necessary since a publish operation is asyncrounous and returns
    # the id and href of the publish task.
    @extend_schema(
        description="Trigger an asynchronous task to publish content",
        responses={202: AsyncOperationResponseSerializer},
    )
    def create(self, request):
        """
        Publishes a repository.

        Either the ``repository`` or the ``repository_version`` fields can
        be provided but not both at the same time.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repository_version = serializer.validated_data.get("repository_version")

        result = dispatch(
            tasks.publish,
            [repository_version.repository],
            kwargs={"repository_version_pk": str(repository_version.pk)},
        )
        return core.OperationPostponedResponse(result, request)


class TofuDistributionViewSet(core.DistributionViewSet):
    """
    A ViewSet for TofuDistribution.

    Provides REST API endpoints for managing distributions that serve
    OpenTofu modules via the Module Registry Protocol.

    Endpoint: /pulp/api/v3/distributions/tofu/
    """

    endpoint_name = "tofu"
    queryset = models.TofuDistribution.objects.all()
    serializer_class = serializers.TofuDistributionSerializer
