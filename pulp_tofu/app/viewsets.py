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
    """

    class Meta:
        model = models.TofuContent
        fields = [
            # ...
        ]


class TofuContentViewSet(core.ContentViewSet):
    """
    A ViewSet for TofuContent.

    Define endpoint name which will appear in the API endpoint for this content type.
    For example::
        https://pulp.example.com/pulp/api/v3/content/tofu/units/

    Also specify queryset and serializer for TofuContent.
    """

    endpoint_name = "tofu"
    queryset = models.TofuContent.objects.all()
    serializer_class = serializers.TofuContentSerializer
    filterset_class = TofuContentFilter

    @transaction.atomic
    def create(self, request):
        """
        Perform bookkeeping when saving Content.

        "Artifacts" need to be popped off and saved indpendently, as they are not actually part
        of the Content model.
        """
        return Response({}, status=status.HTTP_501_NOT_IMPLEMENTED)
        # This requires some choice. Depending on the properties of your content type - whether it
        # can have zero, one, or many artifacts associated with it, and whether any properties of
        # the artifact bleed into the content type (such as the digest), you may want to make
        # those changes here.

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # A single artifact per content, serializer subclasses SingleArtifactContentSerializer
        # ======================================
        # _artifact = serializer.validated_data.pop("_artifact")
        # # you can save model fields directly, e.g. .save(digest=_artifact.sha256)
        # content = serializer.save()
        #
        # if content.pk:
        #     ContentArtifact.objects.create(
        #         artifact=artifact,
        #         content=content,
        #         relative_path= ??
        #     )
        # =======================================

        # Many artifacts per content, serializer subclasses MultipleArtifactContentSerializer
        # =======================================
        # _artifacts = serializer.validated_data.pop("_artifacts")
        # content = serializer.save()
        #
        # if content.pk:
        #   # _artifacts is a dictionary of {"relative_path": "artifact"}
        #   for relative_path, artifact in _artifacts.items():
        #       ContentArtifact.objects.create(
        #           artifact=artifact,
        #           content=content,
        #           relative_path=relative_path
        #       )
        # ========================================

        # No artifacts, serializer subclasses NoArtifactContentSerialier
        # ========================================
        # content = serializer.save()
        # ========================================

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class TofuRemoteFilter(RemoteFilter):
    """
    A FilterSet for TofuRemote.
    """

    class Meta:
        model = models.TofuRemote
        fields = [
            # ...
        ]


class TofuRemoteViewSet(core.RemoteViewSet):
    """
    A ViewSet for TofuRemote.

    Similar to the TofuContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
    """

    endpoint_name = "tofu"
    queryset = models.TofuRemote.objects.all()
    serializer_class = serializers.TofuRemoteSerializer


class TofuRepositoryViewSet(core.RepositoryViewSet, ModifyRepositoryActionMixin):
    """
    A ViewSet for TofuRepository.

    Similar to the TofuContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
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
    A ViewSet for a TofuRepositoryVersion represents a single
    Tofu repository version.
    """

    parent_viewset = TofuRepositoryViewSet


class TofuPublicationViewSet(core.PublicationViewSet):
    """
    A ViewSet for TofuPublication.

    Similar to the TofuContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
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

    Similar to the TofuContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
    """

    endpoint_name = "tofu"
    queryset = models.TofuDistribution.objects.all()
    serializer_class = serializers.TofuDistributionSerializer
