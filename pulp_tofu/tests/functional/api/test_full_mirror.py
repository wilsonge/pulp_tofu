# coding=utf-8
"""Tests that tofu plugin can mirror OpenTofu Registry providers."""
import unittest

from pulp_smash import config
from pulp_smash.pulp3.bindings import monitor_task
from pulp_smash.pulp3.utils import gen_repo, get_content_summary

from pulp_tofu.tests.functional.constants import (
    TOFU_CONTENT_NAME,
    REGISTRY_URL,
)
from pulp_tofu.tests.functional.utils import (
    gen_tofu_client,
    gen_tofu_remote,
)
from pulp_tofu.tests.functional.utils import set_up_module as setUpModule  # noqa:F401

from pulpcore.client.pulpcore import TasksApi, ApiClient as CoreApiClient, Configuration
from pulpcore.client.pulp_tofu import (
    RepositoriesTofuApi,
    RepositorySyncURL,
    RemotesTofuApi,
    DistributionsTofuApi,
    PublicationsTofuApi,
)
import requests
import socket
from urllib.parse import urljoin


@unittest.skip("FIXME: Implement sync functionality first")
class RegistryMirrorTestCase(unittest.TestCase):
    """
    Testing Pulp's ability to sync OpenTofu providers from the registry.

    This test verifies that the plugin can mirror providers from the
    OpenTofu registry and make them available for OpenTofu clients.
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = gen_tofu_client()
        configuration = Configuration()
        configuration.username = "admin"
        configuration.password = "password"
        configuration.host = "http://{}:24817".format(socket.gethostname())
        configuration.safe_chars_for_path_param = "/"
        cls.core_client = CoreApiClient(configuration)

    def test_sync_specific_providers(self):
        """Test syncing specific providers from OpenTofu registry."""
        repo_api = RepositoriesTofuApi(self.client)
        remote_api = RemotesTofuApi(self.client)
        tasks_api = TasksApi(self.core_client)

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        # Sync only a few specific providers to keep test fast
        # FIXME: Update gen_tofu_remote to accept includes parameter
        body = gen_tofu_remote(
            REGISTRY_URL,
            # includes should be a list of providers like:
            # ["hashicorp/random", "hashicorp/null", "hashicorp/local"]
            policy="immediate",
        )
        remote = remote_api.create(body)
        self.addCleanup(remote_api.delete, remote.pulp_href)

        # Sync the repository
        self.assertEqual(repo.latest_version_href, f"{repo.pulp_href}versions/0/")
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = repo_api.read(repo.pulp_href)

        sync_task = tasks_api.read(sync_response.task)
        time_diff = sync_task.finished_at - sync_task.started_at
        print(f"Sync time: {time_diff.seconds} seconds")

        self.assertIsNotNone(repo.latest_version_href)
        # Should have synced provider content
        content_summary = get_content_summary(repo.to_dict())
        self.assertIn(TOFU_CONTENT_NAME, content_summary)
        self.assertGreater(content_summary[TOFU_CONTENT_NAME], 0)

    def test_on_demand_sync(self):
        """Test on-demand syncing of providers."""
        repo_api = RepositoriesTofuApi(self.client)
        remote_api = RemotesTofuApi(self.client)

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        # FIXME: Update gen_tofu_remote to accept includes parameter
        body = gen_tofu_remote(REGISTRY_URL, policy="on_demand")
        remote = remote_api.create(body)
        self.addCleanup(remote_api.delete, remote.pulp_href)

        # Sync the repository
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = repo_api.read(repo.pulp_href)

        self.assertIsNotNone(repo.latest_version_href)
        # On-demand should create content units but not download artifacts
        content_summary = get_content_summary(repo.to_dict())
        self.assertIn(TOFU_CONTENT_NAME, content_summary)


@unittest.skip("FIXME: Implement content serving first")
class ProviderRegistryProtocolTestCase(unittest.TestCase):
    """
    Test that the plugin correctly implements the OpenTofu Provider Registry Protocol.

    These tests verify that a distributed repository can serve providers
    to OpenTofu clients using the correct protocol endpoints.
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = gen_tofu_client()
        cls.repo_api = RepositoriesTofuApi(cls.client)
        cls.remote_api = RemotesTofuApi(cls.client)
        cls.publication_api = PublicationsTofuApi(cls.client)
        cls.distribution_api = DistributionsTofuApi(cls.client)

        # Create a repository with some synced providers
        cls.repo = cls.repo_api.create(gen_repo())

        # FIXME: Sync some test providers here
        # For now, we'll skip the sync and just test the protocol endpoints

    @classmethod
    def tearDownClass(cls):
        """Clean up test resources."""
        if hasattr(cls, "repo"):
            cls.repo_api.delete(cls.repo.pulp_href)

    def test_service_discovery(self):
        """Test the service discovery endpoint."""
        # Create a publication and distribution
        publication = self.publication_api.create({"repository": self.repo.pulp_href})
        monitor_task(publication.task)

        distro_data = {
            "name": "test-distro",
            "base_path": "test-providers",
            "publication": publication.pulp_href,
        }
        distro = self.distribution_api.create(distro_data)
        self.addCleanup(self.distribution_api.delete, distro.pulp_href)

        # Test service discovery endpoint
        base_url = self.cfg.get_content_host_base_url()
        discovery_url = urljoin(base_url, f"{distro.base_path}/.well-known/terraform.json")

        response = requests.get(discovery_url)
        self.assertEqual(response.status_code, 200)

        discovery_data = response.json()
        self.assertIn("providers.v1", discovery_data)
        self.assertIsNotNone(discovery_data["providers.v1"])

    def test_list_provider_versions(self):
        """Test listing available versions of a provider."""
        # FIXME: This test requires synced provider content
        # Create a publication and distribution
        publication = self.publication_api.create({"repository": self.repo.pulp_href})
        monitor_task(publication.task)

        distro_data = {
            "name": "test-versions",
            "base_path": "test-versions",
            "publication": publication.pulp_href,
        }
        distro = self.distribution_api.create(distro_data)
        self.addCleanup(self.distribution_api.delete, distro.pulp_href)

        # Test list versions endpoint for a known provider (e.g., hashicorp/random)
        base_url = self.cfg.get_content_host_base_url()
        versions_url = urljoin(
            base_url, f"{distro.base_path}/v1/providers/hashicorp/random/versions"
        )

        response = requests.get(versions_url)
        self.assertEqual(response.status_code, 200)

        versions_data = response.json()
        self.assertIn("versions", versions_data)
        self.assertIsInstance(versions_data["versions"], list)

        # Verify version structure
        if len(versions_data["versions"]) > 0:
            version = versions_data["versions"][0]
            self.assertIn("version", version)
            self.assertIn("protocols", version)
            self.assertIn("platforms", version)

    def test_download_provider_package(self):
        """Test downloading a specific provider package."""
        # FIXME: This test requires synced provider content
        publication = self.publication_api.create({"repository": self.repo.pulp_href})
        monitor_task(publication.task)

        distro_data = {
            "name": "test-download",
            "base_path": "test-download",
            "publication": publication.pulp_href,
        }
        distro = self.distribution_api.create(distro_data)
        self.addCleanup(self.distribution_api.delete, distro.pulp_href)

        # Test download endpoint for a specific version and platform
        base_url = self.cfg.get_content_host_base_url()
        download_url = urljoin(
            base_url, f"{distro.base_path}/v1/providers/hashicorp/random/3.0.0/download/linux/amd64"
        )

        response = requests.get(download_url)
        self.assertEqual(response.status_code, 200)

        download_data = response.json()
        # Verify required fields per OpenTofu protocol
        required_fields = ["protocols", "os", "arch", "filename", "download_url", "shasum"]
        for field in required_fields:
            self.assertIn(field, download_data, f"Missing required field: {field}")

        # Verify the download_url is accessible
        artifact_response = requests.head(download_data["download_url"])
        self.assertEqual(artifact_response.status_code, 200)

    def test_provider_package_checksums(self):
        """Test that checksums are correctly provided and match."""
        # FIXME: This test requires synced provider content
        publication = self.publication_api.create({"repository": self.repo.pulp_href})
        monitor_task(publication.task)

        distro_data = {
            "name": "test-checksums",
            "base_path": "test-checksums",
            "publication": publication.pulp_href,
        }
        distro = self.distribution_api.create(distro_data)
        self.addCleanup(self.distribution_api.delete, distro.pulp_href)

        base_url = self.cfg.get_content_host_base_url()
        download_url = urljoin(
            base_url, f"{distro.base_path}/v1/providers/hashicorp/random/3.0.0/download/linux/amd64"
        )

        response = requests.get(download_url)
        download_data = response.json()

        # Verify checksum format (should be SHA256)
        self.assertIsNotNone(download_data["shasum"])
        self.assertEqual(len(download_data["shasum"]), 64)  # SHA256 is 64 hex chars

        # Optional: Download the artifact and verify the checksum
        # artifact_response = requests.get(download_data["download_url"])
        # import hashlib
        # actual_sha = hashlib.sha256(artifact_response.content).hexdigest()
        # self.assertEqual(actual_sha, download_data["shasum"])
