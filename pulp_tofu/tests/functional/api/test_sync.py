"""Tests that sync tofu plugin repositories."""
import unittest

from pulp_smash import config
from pulp_smash.pulp3.bindings import monitor_task, PulpTaskError
from pulp_smash.pulp3.utils import gen_repo, get_added_content_summary, get_content_summary

from pulp_tofu.tests.functional.constants import (
    TOFU_FIXTURE_SUMMARY,
    TOFU_INVALID_FIXTURE_URL,
)
from pulp_tofu.tests.functional.utils import (
    gen_tofu_client,
    gen_tofu_remote,
)
from pulp_tofu.tests.functional.utils import set_up_module as setUpModule  # noqa:F401

from pulpcore.client.pulp_tofu import (
    RepositoriesTofuApi,
    RepositorySyncURL,
    RemotesTofuApi,
)


# Implement sync support before enabling this test.
@unittest.skip("FIXME: plugin writer action required")
class BasicSyncTestCase(unittest.TestCase):
    """Sync a repository with the tofu plugin."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = gen_tofu_client()

    def test_sync(self):
        """Sync repositories with the tofu plugin.

        In order to sync a repository a remote has to be associated within
        this repository. When a repository is created this version field is set
        as None. After a sync the repository version is updated.

        Do the following:

        1. Create a repository, and a remote.
        2. Assert that repository version is None.
        3. Sync the remote.
        4. Assert that repository version is not None.
        5. Assert that the correct number of units were added and are present
           in the repo.
        6. Sync the remote one more time.
        7. Assert that repository version is different from the previous one.
        8. Assert that the same number of are present and that no units were
           added.
        """
        repo_api = RepositoriesTofuApi(self.client)
        remote_api = RemotesTofuApi(self.client)

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        body = gen_tofu_remote()
        remote = remote_api.create(body)
        self.addCleanup(remote_api.delete, remote.pulp_href)

        # Sync the repository.
        self.assertEqual(repo.latest_version_href, f"{repo.pulp_href}versions/0/")
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = repo_api.read(repo.pulp_href)

        self.assertIsNotNone(repo.latest_version_href)
        self.assertDictEqual(get_content_summary(repo.to_dict()), TOFU_FIXTURE_SUMMARY)
        self.assertDictEqual(get_added_content_summary(repo.to_dict()), TOFU_FIXTURE_SUMMARY)

        # Sync the repository again.
        latest_version_href = repo.latest_version_href
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        repo = repo_api.read(repo.pulp_href)

        self.assertEqual(latest_version_href, repo.latest_version_href)
        self.assertDictEqual(get_content_summary(repo.to_dict()), TOFU_FIXTURE_SUMMARY)


# Implement sync support before enabling this test.
@unittest.skip("FIXME: plugin writer action required")
class SyncInvalidTestCase(unittest.TestCase):
    """Sync a repository with a given url on the remote."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.client = gen_tofu_client()

    def test_invalid_url(self):
        """Sync a repository using a remote url that does not exist.

        Test that we get a task failure. See :meth:`do_test`.
        """
        with self.assertRaises(PulpTaskError) as cm:
            task = self.do_test("http://i-am-an-invalid-url.com/invalid/")
        task = cm.exception.task.to_dict()
        self.assertIsNotNone(task["error"]["description"])

    # Provide an invalid repository and specify keywords in the anticipated error message
    @unittest.skip("FIXME: Plugin writer action required.")
    def test_invalid_tofu_content(self):
        """Sync a repository using an invalid plugin_content repository.

        Assert that an exception is raised, and that error message has
        keywords related to the reason of the failure. See :meth:`do_test`.
        """
        with self.assertRaises(PulpTaskError) as cm:
            task = self.do_test(TOFU_INVALID_FIXTURE_URL)
        task = cm.exception.task.to_dict()
        for key in ("mismached", "empty"):
            self.assertIn(key, task["error"]["description"])

    def do_test(self, url):
        """Sync a repository given ``url`` on the remote."""
        repo_api = RepositoriesTofuApi(self.client)
        remote_api = RemotesTofuApi(self.client)

        repo = repo_api.create(gen_repo())
        self.addCleanup(repo_api.delete, repo.pulp_href)

        body = gen_tofu_remote(url=url)
        remote = remote_api.create(body)
        self.addCleanup(remote_api.delete, remote.pulp_href)

        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = repo_api.sync(repo.pulp_href, repository_sync_data)
        return monitor_task(sync_response.task)
