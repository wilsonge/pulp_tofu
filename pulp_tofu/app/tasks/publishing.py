import logging
from gettext import gettext as _

from pulpcore.plugin.models import (
    ContentArtifact,
    RepositoryVersion,
    PublishedArtifact,
)

from pulp_tofu.app.models import TofuContent, TofuPublication


log = logging.getLogger(__name__)


def publish(repository_version_pk):
    """
    Create a Publication based on a RepositoryVersion.

    For OpenTofu modules, we publish all module artifacts that are part of
    the repository version. The artifacts are served directly by Pulp's
    content app via the distribution's content handlers.

    Args:
        repository_version_pk (str): Create a publication from this repository version.
    """
    repository_version = RepositoryVersion.objects.get(pk=repository_version_pk)

    log.info(
        _("Publishing: repository={repo}, version={ver}").format(
            repo=repository_version.repository.name,
            ver=repository_version.number,
        )
    )

    with TofuPublication.create(repository_version) as publication:
        # Get all TofuContent in this repository version
        content_qs = TofuContent.objects.filter(
            pk__in=repository_version.content.all()
        )

        log.info(
            _("Publishing {count} module(s)").format(count=content_qs.count())
        )

        # For each module, publish its artifact
        for content in content_qs:
            # Get the content artifact associated with this module
            content_artifact = ContentArtifact.objects.filter(content=content).first()

            if content_artifact:
                # Create a PublishedArtifact to make the artifact available
                # via the distribution
                PublishedArtifact.objects.create(
                    relative_path=content_artifact.relative_path,
                    publication=publication,
                    content_artifact=content_artifact,
                )

                log.debug(
                    _("Published {namespace}/{name}/{system}@{version}").format(
                        namespace=content.namespace,
                        name=content.name,
                        system=content.system,
                        version=content.version,
                    )
                )
            else:
                log.warning(
                    _("No artifact found for {namespace}/{name}/{system}@{version}").format(
                        namespace=content.namespace,
                        name=content.name,
                        system=content.system,
                        version=content.version,
                    )
                )

    log.info(_("Publication: {publication} created").format(publication=publication.pk))
