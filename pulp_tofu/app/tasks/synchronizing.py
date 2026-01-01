from gettext import gettext as _
import json
import logging
from fnmatch import fnmatch
from urllib.parse import urljoin

from pulpcore.plugin.models import Artifact, ProgressReport, Remote, Repository
from pulpcore.plugin.stages import (
    DeclarativeArtifact,
    DeclarativeContent,
    DeclarativeVersion,
    Stage,
)

from pulp_tofu.app.models import TofuContent, TofuRemote


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
        2. Queries for modules based on includes patterns
        3. Fetches version information for each module
        4. Creates DeclarativeContent for each module version
        """
        # Discover the registry API base URL
        registry_base_url = await self._discover_registry_endpoint()

        # Get the list of modules to sync based on includes patterns
        modules_to_sync = self._parse_includes()

        if not modules_to_sync:
            log.warning(_("No modules specified in 'includes'. Nothing to sync."))
            return

        # Track progress
        with ProgressReport(
            message="Syncing OpenTofu modules",
            code="sync.opentofu.modules",
            total=len(modules_to_sync)
        ) as progress_bar:
            for module_spec in modules_to_sync:
                try:
                    namespace, name, system = module_spec.split("/")

                    # Check if this module matches any exclude patterns
                    if self._is_excluded(module_spec):
                        log.info(_("Skipping excluded module: {module}").format(module=module_spec))
                        progress_bar.increment()
                        continue

                    # Fetch module versions from the registry
                    await self._sync_module(registry_base_url, namespace, name, system)
                    progress_bar.increment()

                except ValueError:
                    log.error(
                        _("Invalid module specification: {spec}. Expected format: namespace/name/system").format(
                            spec=module_spec
                        )
                    )
                    progress_bar.increment()
                    continue
                except Exception as e:
                    log.error(
                        _("Failed to sync module {module}: {error}").format(
                            module=module_spec, error=str(e)
                        )
                    )
                    progress_bar.increment()
                    continue

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
        if url.endswith("/.well-known/terraform.json") or url.endswith(".well-known/terraform.json"):
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
                from urllib.parse import urlparse
                parsed = urlparse(url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                return urljoin(base, modules_endpoint)
            else:
                return modules_endpoint
        else:
            # Assume the URL is already the registry API base URL
            return url

    def _parse_includes(self):
        """
        Parse the includes patterns to get a list of modules to sync.

        For now, this expects explicit module specifications in the format:
        namespace/name/system

        Wildcard support (e.g., hashicorp/*/aws) could be added in the future
        by querying a module listing API if available.

        Returns:
            list: List of module specifications (namespace/name/system)
        """
        includes = self.remote.includes or []

        # For now, return the includes as-is
        # TODO: Implement wildcard expansion if the registry provides a search/list API
        return includes

    def _is_excluded(self, module_spec):
        """
        Check if a module specification matches any exclude pattern.

        Args:
            module_spec (str): Module specification (namespace/name/system)

        Returns:
            bool: True if the module should be excluded
        """
        excludes = self.remote.excludes or []

        for pattern in excludes:
            if fnmatch(module_spec, pattern):
                return True

        return False

    async def _sync_module(self, registry_base_url, namespace, name, system):
        """
        Sync a specific module from the registry.

        Args:
            registry_base_url (str): Base URL of the registry API
            namespace (str): Module namespace
            name (str): Module name
            system (str): Target system
        """
        # Build the versions endpoint URL
        versions_url = urljoin(
            registry_base_url.rstrip("/") + "/",
            f"{namespace}/{name}/{system}/versions"
        )

        log.info(
            _("Fetching versions for module: {namespace}/{name}/{system}").format(
                namespace=namespace, name=name, system=system
            )
        )

        # Download the versions list
        downloader = self.remote.get_downloader(url=versions_url)
        result = await downloader.run()

        # Parse the versions response
        with open(result.path, "r") as f:
            versions_data = json.load(f)

        # Extract versions from the response
        modules = versions_data.get("modules", [])
        if not modules:
            log.warning(
                _("No versions found for module: {namespace}/{name}/{system}").format(
                    namespace=namespace, name=name, system=system
                )
            )
            return

        versions = modules[0].get("versions", [])

        log.info(
            _("Found {count} versions for {namespace}/{name}/{system}").format(
                count=len(versions),
                namespace=namespace,
                name=name,
                system=system
            )
        )

        # Fetch download info for each version
        for version_info in versions:
            version = version_info.get("version")
            if not version:
                continue

            try:
                await self._sync_module_version(
                    registry_base_url, namespace, name, system, version
                )
            except Exception as e:
                log.error(
                    _("Failed to sync {namespace}/{name}/{system} version {version}: {error}").format(
                        namespace=namespace,
                        name=name,
                        system=system,
                        version=version,
                        error=str(e)
                    )
                )

    async def _sync_module_version(self, registry_base_url, namespace, name, system, version):
        """
        Sync a specific version of a module.

        Args:
            registry_base_url (str): Base URL of the registry API
            namespace (str): Module namespace
            name (str): Module name
            system (str): Target system
            version (str): Module version
        """
        # Build the download endpoint URL
        download_url = urljoin(
            registry_base_url.rstrip("/") + "/",
            f"{namespace}/{name}/{system}/{version}/download"
        )

        log.debug(
            _("Fetching download info for {namespace}/{name}/{system}@{version}").format(
                namespace=namespace, name=name, system=system, version=version
            )
        )

        # Download the download info
        downloader = self.remote.get_downloader(url=download_url)
        result = await downloader.run()

        # Parse the download response
        with open(result.path, "r") as f:
            download_data = json.load(f)

        # Get the download location
        module_download_url = download_data.get("location")
        if not module_download_url:
            log.warning(
                _("No download location for {namespace}/{name}/{system}@{version}").format(
                    namespace=namespace, name=name, system=system, version=version
                )
            )
            return

        # Create the TofuContent unit (in-memory only)
        content = TofuContent(
            namespace=namespace,
            name=name,
            system=system,
            version=version,
            download_url=module_download_url,
        )

        # Build the relative path for the artifact
        relative_path = f"{namespace}/{name}/{system}/{version}/module.tar.gz"

        # Create DeclarativeArtifact
        da = DeclarativeArtifact(
            artifact=Artifact(),
            url=module_download_url,
            relative_path=relative_path,
            remote=self.remote,
            deferred_download=self.deferred_download,
        )

        # Create and emit DeclarativeContent
        dc = DeclarativeContent(content=content, d_artifacts=[da])
        await self.put(dc)

        log.debug(
            _("Synced {namespace}/{name}/{system}@{version}").format(
                namespace=namespace, name=name, system=system, version=version
            )
        )
