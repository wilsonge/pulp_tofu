# coding=utf-8
"""Tests that python plugin can fully mirror OpenTofu Registry and other Pulp repositories"""
import unittest

from pulp_smash import config, cli
from pulp_smash.pulp3.bindings import delete_orphans, monitor_task
from pulp_smash.pulp3.utils import gen_repo, get_content_summary

from pulp_tofu.tests.functional.constants import (
    PULP_CONTENT_BASE_URL,
    PULP_REGISTRY_BASE_URL,
    TOFU_CONTENT_NAME,
    REGISTRY_URL,
    TOFU_XS_FIXTURE_CHECKSUMS,
)
from pulp_tofu.tests.functional.utils import (
    cfg,
    gen_tofu_client,
    gen_tofu_remote,
    TestCaseUsingBindings,
    TestHelpersMixin,
)
from pulp_tofu.tests.functional.utils import set_up_module as setUpModule  # noqa:F401

from pulpcore.client.pulpcore import TasksApi, ApiClient as CoreApiClient, Configuration
from pulpcore.client.pulp_tofu import (
    RepositoriesTofuApi,
    RepositorySyncURL,
    RemotesTofuApi,
)
from pypi_simple import parse_repo_project_response
import requests
import socket
from urllib.parse import urljoin, urlsplit


@unittest.skip
class RegistryMirrorTestCase(unittest.TestCase):
    """
    Testing Pulp's full syncing ability of Tofu repositories

     This test targets the following issues:

    * `Pulp #985 <https://pulp.plan.io/issues/985>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = gen_tofu_client()
        configuration = Configuration()
        configuration.username = 'admin'
        configuration.password = 'password'
        configuration.host = 'http://{}:24817'.format(socket.gethostname())
        configuration.safe_chars_for_path_param = '/'
        cls.core_client = CoreApiClient(configuration)

    def test_on_demand_pypi_full_sync(self):
        """This test syncs all of PyPi"""
        repo_api = RepositoriesTofuApi(self.client)
        remote_api = RemotesTofuApi(self.client)
        tasks_api = TasksApi(self.core_client)

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        body = gen_tofu_remote("https://registry.opentofu.org", includes=[], policy="on_demand")
        remote = remote_api.create(body)
        self.addCleanup(remote_api.delete, remote.pulp_href)

        # Sync the repository.
        self.assertEqual(repo.latest_version_href, f"{repo.pulp_href}versions/0/")
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = repo_api.read(repo.pulp_href)

        sync_task = tasks_api.read(sync_response.task)
        time_diff = sync_task.finished_at - sync_task.started_at
        print("Delete time: {} seconds".format(time_diff.seconds))

        self.assertIsNotNone(repo.latest_version_href)
        # As of August 11 2020, all_packages() returns 253,587 packages,
        # only 248,677 of them were downloadable
        self.assertTrue(get_content_summary(repo.to_dict())[TOFU_CONTENT_NAME] > 245000)


class PullThroughMirror(TestCaseUsingBindings, TestHelpersMixin):
    """
    Testing Pulp's ability to act as a pull-through cache
    """

    @classmethod
    def setUpClass(cls):
        """Sets up class variables."""
        super().setUpClass()
        cls.cli_client = cli.Client(cfg)
        cls.HOST = cls.client.configuration.host
        cls.PYPI_HOST = urljoin(cls.HOST, PULP_REGISTRY_BASE_URL)

    def test_pull_through_install(self):
        """Tests that a pull-through distro can be installed from."""
        remote = self._create_remote(url=REGISTRY_URL)
        distro = self._create_distribution(remote=remote.pulp_href)

        PACKAGE = "pulpcore-releases"
        if self.cli_client.run(("pip", "list")).stdout.find(PACKAGE) == -1:
            content = self.content_api.list(name=PACKAGE)
            self.assertEqual(content.count, 0, msg=f"{PACKAGE} content already present in test")
            host = urlsplit(PULP_CONTENT_BASE_URL).hostname
            url = urljoin(self.PYPI_HOST, f"{distro.base_path}/simple/")
            out = self.cli_client.run(
                ("pip", "install", "--trusted-host", host, "-i", url, PACKAGE)
            )
            self.addCleanup(delete_orphans)
            self.assertTrue(self.cli_client.run(("pip", "list")).stdout.find(PACKAGE) != -1, out)
            self.addCleanup(self.cli_client.run, ("pip", "uninstall", PACKAGE, "-y"))
            content = self.content_api.list(name=PACKAGE)
            self.assertEqual(content.count, 1)
        else:
            self.skipTest(f"Uninstall {PACKAGE} before running this test")

    def test_pull_through_simple(self):
        """Tests that the simple page is properly modified when requesting a pull-through."""
        remote = self._create_remote(url=REGISTRY_URL)
        distro = self._create_distribution(remote=remote.pulp_href)

        url = urljoin(self.PYPI_HOST, f"{distro.base_path}/simple/shelf-reader/")
        response = requests.get(url)
        project_page = parse_repo_project_response("shelf-reader", response)

        self.assertEqual(len(project_page.packages), 2)
        for package in project_page.packages:
            self.assertIn(package.filename, TOFU_XS_FIXTURE_CHECKSUMS)
            relative_path = f"{distro.base_path}/{package.filename}?redirect="
            self.assertIn(urljoin(PULP_CONTENT_BASE_URL, relative_path), package.url)
            digests = package.get_digests()
            self.assertEqual(TOFU_XS_FIXTURE_CHECKSUMS[package.filename], digests["sha256"])

    def test_pull_through_with_repo(self):
        """Tests that if content is already in repository, pull-through isn't used."""
        remote = self._create_remote()
        repo = self._create_repo_and_sync_with_remote(remote)
        self.addCleanup(delete_orphans)
        distro = self._create_distribution(remote=remote.pulp_href, repository=repo.pulp_href)

        url = urljoin(self.PYPI_HOST, f"{distro.base_path}/simple/shelf-reader/")
        response = requests.get(url)
        project_page = parse_repo_project_response("shelf-reader", response)

        self.assertEqual(len(project_page.packages), 2)
        for package in project_page.packages:
            self.assertIn(package.filename, TOFU_XS_FIXTURE_CHECKSUMS)
            self.assertNotIn("?redirect=", package.url)
