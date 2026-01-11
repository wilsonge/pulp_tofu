"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/index.html
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
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

from . import models, serializers, tasks


class ProviderFilter(core.ContentFilter):
    """
    FilterSet for Provider.

    Allows filtering providers by namespace, type, version, os, and arch.
    """

    class Meta:
        model = models.Provider
        fields = [
            "namespace",
            "type",
            "version",
            "os",
            "arch",
        ]


class ProviderViewSet(core.ContentViewSet):
    """
    A ViewSet for Provider.

    Provides REST API endpoints for managing OpenTofu provider content units.

    Endpoint: /pulp/api/v3/providers/tofu/units/
    """

    endpoint_name = "providers"
    queryset = models.Provider.objects.all()
    serializer_class = serializers.ProviderSerializer
    filterset_class = ProviderFilter

    # @transaction.atomic
    # def create(self, request):
    #     """
    #     Create a Provider unit with its associated artifact.
    #
    #     Each OpenTofu provider has a single artifact (the provider zip archive).
    #     The artifact is associated with a relative path based on the provider's
    #     namespace, type, version, os, and arch.
    #
    #     The relative_path is automatically generated as:
    #     {namespace}/{type}/{version}/{os}_{arch}/{filename}
    #     """
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     serializer.save()
    #
    #     headers = self.get_success_headers(serializer.data)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        description="List all providers for a given namespace and type",
        summary="List providers by namespace/type",
        parameters=[
            OpenApiParameter(
                name="namespace",
                type=str,
                location=OpenApiParameter.PATH,
                description="Provider namespace (e.g., 'hashicorp')",
            ),
            OpenApiParameter(
                name="type",
                type=str,
                location=OpenApiParameter.PATH,
                description="Provider type (e.g., 'aws', 'random')",
            ),
        ],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"(?P<namespace>[^/]+)/(?P<type>[^/]+)",
        url_name="by-namespace-type",
    )
    def by_namespace_type(self, request, namespace=None, type=None):
        """
        List all providers matching the given namespace and type.

        URL: /pulp/api/v3/content/tofu/providers/:namespace/:type/

        This provides a more RESTful alternative to using query parameters.
        """
        queryset = self.get_queryset().filter(namespace=namespace, type=type)
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Get a specific provider by namespace, type, and version",
        summary="Get provider by namespace/type/version",
        parameters=[
            OpenApiParameter(
                name="namespace",
                type=str,
                location=OpenApiParameter.PATH,
                description="Provider namespace",
            ),
            OpenApiParameter(
                name="type",
                type=str,
                location=OpenApiParameter.PATH,
                description="Provider type",
            ),
            OpenApiParameter(
                name="version",
                type=str,
                location=OpenApiParameter.PATH,
                description="Provider version (e.g., '2.0.0')",
            ),
        ],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"(?P<namespace>[^/]+)/(?P<type>[^/]+)/(?P<version>[^/]+)",
        url_name="by-namespace-type-version",
    )
    def by_namespace_type_version(self, request, namespace=None, type=None, version=None):
        """
        List all providers (different platforms) for a specific namespace/type/version.

        URL: /pulp/api/v3/content/tofu/providers/:namespace/:type/:version/

        Returns all platform variants (os/arch combinations) for the given provider version.
        """
        queryset = self.get_queryset().filter(namespace=namespace, type=type, version=version)
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Get a specific provider package by namespace, type, version, os, and arch",
        summary="Get provider package",
        parameters=[
            OpenApiParameter(
                name="namespace",
                type=str,
                location=OpenApiParameter.PATH,
                description="Provider namespace",
            ),
            OpenApiParameter(
                name="type",
                type=str,
                location=OpenApiParameter.PATH,
                description="Provider type",
            ),
            OpenApiParameter(
                name="version",
                type=str,
                location=OpenApiParameter.PATH,
                description="Provider version",
            ),
            OpenApiParameter(
                name="os",
                type=str,
                location=OpenApiParameter.PATH,
                description="Operating system (e.g., 'linux', 'darwin')",
            ),
            OpenApiParameter(
                name="arch",
                type=str,
                location=OpenApiParameter.PATH,
                description="CPU architecture (e.g., 'amd64', 'arm64')",
            ),
        ],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=(
            r"(?P<namespace>[^/]+)/(?P<type>[^/]+)/(?P<version>[^/]+)/"
            r"(?P<os>[^/]+)/(?P<arch>[^/]+)"
        ),
        url_name="by-full-path",
    )
    def by_full_path(self, request, namespace=None, type=None, version=None, os=None, arch=None):
        """
        Get a specific provider package by its full identifier.

        URL: /pulp/api/v3/content/tofu/providers/:namespace/:type/:version/:os/:arch/

        This uniquely identifies a single provider package.
        """
        provider = get_object_or_404(
            self.get_queryset(), namespace=namespace, type=type, version=version, os=os, arch=arch
        )
        serializer = self.get_serializer(provider)
        return Response(serializer.data)


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

    Provides REST API endpoints for managing OpenTofu provider registry remotes.
    """

    endpoint_name = "tofu"
    queryset = models.TofuRemote.objects.all()
    serializer_class = serializers.TofuRemoteSerializer
    filterset_class = TofuRemoteFilter


class TofuRepositoryViewSet(core.RepositoryViewSet, ModifyRepositoryActionMixin):
    """
    A ViewSet for TofuRepository.

    Provides REST API endpoints for managing OpenTofu provider repositories,
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
    OpenTofu provider repositories.

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
    OpenTofu providers via the Provider Registry Protocol.

    Endpoint: /pulp/api/v3/distributions/tofu/
    """

    endpoint_name = "tofu"
    queryset = models.TofuDistribution.objects.all()
    serializer_class = serializers.TofuDistributionSerializer
