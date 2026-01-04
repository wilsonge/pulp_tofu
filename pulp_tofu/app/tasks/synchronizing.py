from gettext import gettext as _
import json
import logging
from urllib.parse import urljoin, urlparse

from pulpcore.plugin.models import Artifact, ContentArtifact, ProgressReport, Remote, Repository
from pulpcore.plugin.stages import (
    DeclarativeArtifact,
    DeclarativeContent,
    DeclarativeVersion,
    Stage,
)

from pulp_tofu.app.models import Provider, TofuRemote


log = logging.getLogger(__name__)


def synchronize(remote_pk, repository_pk, mirror):
    """
    Sync content from the remote repository.

    Create a new version of the repository that is synchronized with the remote.

    Args:
        remote_pk (str): The remote PK.
        repository_pk (str): The repository PK.
        mirror (bool): True for mirror mode, False for additive.

    Raises:
        ValueError: If the remote does not specify a URL to sync

    """
    remote = TofuRemote.objects.get(pk=remote_pk)
    repository = Repository.objects.get(pk=repository_pk)

    if not remote.url:
        raise ValueError(_("A remote must have a url specified to synchronize."))

    # Interpret policy to download Artifacts or not
    deferred_download = remote.policy != Remote.IMMEDIATE
    first_stage = TofuFirstStage(remote, deferred_download)
    DeclarativeVersion(first_stage, repository, mirror=mirror).create()


class TofuFirstStage(Stage):
    """
    The first stage of a pulp_tofu sync pipeline.
    """

    def __init__(self, remote, deferred_download):
        """
        The first stage of a pulp_tofu sync pipeline.

        Args:
            remote (FileRemote): The remote data to be used when syncing
            deferred_download (bool): if True the downloading will not happen now. If False, it will
                happen immediately.

        """
        super().__init__()
        self.remote = remote
        self.deferred_download = deferred_download

    async def run(self):
        """
        Build and emit `DeclarativeContent` from the OpenTofu registry.

        This method:
        1. Discovers the registry API endpoint (if needed)
        2. Queries for available modules
        3. Fetches version information for each module
        4. Creates DeclarativeContent for each module version

        Note: The OpenTofu registry doesn't provide a "list all modules" endpoint.
        The sync will need to discover modules through some mechanism - either
        by parsing the registry's website, using a search API, or syncing
        specific modules requested by users.
        """
        # Discover the registry API base URL
        registry_base_url = await self._discover_registry_endpoint()

        # TODO: Implement module discovery mechanism
        # The OpenTofu registry doesn't have a standard API to list all modules.
        # Possible approaches:
        # 1. Implement a search/scraping mechanism for the registry website
        # 2. Only sync modules that have been explicitly added to the repository
        # 3. Use a separate module list file or configuration

        log.warning(
            _(
                "Module discovery not yet implemented. "
                "Please add modules manually using the content API."
            )
        )

        # For now, sync will complete successfully but won't add any content
        # This allows the plugin infrastructure to work while module discovery
        # is being implemented

    async def _discover_registry_endpoint(self):
        """
        Discover the OpenTofu registry API endpoint.

        If the remote URL points to a service discovery endpoint, parse it.
        Otherwise, assume the URL is the registry API base URL.

        Returns:
            str: The base URL for the registry API
        """
        url = self.remote.url

        # If the URL ends with .well-known/terraform.json, fetch service discovery
        if url.endswith("/.well-known/terraform.json") or url.endswith(
            ".well-known/terraform.json"
        ):
            downloader = self.remote.get_downloader(url=url)
            result = await downloader.run()

            with open(result.path, "r") as f:
                discovery = json.load(f)

            # Get the modules.v1 endpoint
            modules_endpoint = discovery.get("modules.v1")
            if not modules_endpoint:
                raise ValueError(_("Service discovery did not return a 'modules.v1' endpoint"))

            # If relative, make it absolute
            if modules_endpoint.startswith("/"):
                parsed = urlparse(url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                return urljoin(base, modules_endpoint)
            else:
                return modules_endpoint
        else:
            # Assume the URL is already the registry API base URL
            return url
