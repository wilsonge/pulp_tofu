import pytest
import uuid
from collections import defaultdict

from pulpcore.tests.functional.utils import BindingsNamespace


@pytest.fixture(scope="session")
def tofu_bindings(_api_client_set, bindings_cfg):
    """
    A namespace providing preconfigured pulp_tofu api clients.

    e.g. `tofu.RepositoriesTofuApi.list()`.
    """
    from pulpcore.client import pulp_tofu as tofu_bindings_module

    api_client = tofu_bindings_module.ApiClient(bindings_cfg)
    _api_client_set.add(api_client)
    yield BindingsNamespace(tofu_bindings_module, api_client)
    _api_client_set.remove(api_client)


@pytest.fixture(scope="class")
def tofu_repository_factory(tofu_bindings, gen_object_with_cleanup):
    def _tofu_repository_factory(remote=None, pulp_domain=None, **body):
        name = body.get("name") or str(uuid.uuid4())
        body.update({"name": name})
        kwargs = {}
        if pulp_domain:
            kwargs["pulp_domain"] = pulp_domain
        if remote:
            body["remote"] = remote if isinstance(remote, str) else remote.pulp_href
        return gen_object_with_cleanup(tofu_bindings.RepositoriesTofuApi, body, **kwargs)

    return _tofu_repository_factory


@pytest.fixture(scope="class")
def tofu_remote_factory(tofu_bindings, gen_object_with_cleanup):
    def _tofu_remote_factory(url=None, policy="immediate", pulp_domain=None, **body):
        name = body.get("name") or str(uuid.uuid4())
        body.update({"url": str(url), "policy": policy, "name": name})
        kwargs = {}
        if pulp_domain:
            kwargs["pulp_domain"] = pulp_domain
        return gen_object_with_cleanup(tofu_bindings.RemotesTofuApi, body, **kwargs)

    return _tofu_remote_factory


@pytest.fixture(scope="class")
def tofu_distribution_factory(tofu_bindings, gen_object_with_cleanup):
    def _tofu_distribution_factory(pulp_domain=None, **body):
        data = {"base_path": str(uuid.uuid4()), "name": str(uuid.uuid4())}
        data.update(body)
        kwargs = {}
        if pulp_domain:
            kwargs["pulp_domain"] = pulp_domain
        return gen_object_with_cleanup(tofu_bindings.DistributionsTofuApi, data, **kwargs)

    return _tofu_distribution_factory


@pytest.fixture(scope="function")
def tofu_repo(tofu_repository_factory):
    return tofu_repository_factory()


@pytest.fixture(scope="function")
def tofu_remote(tofu_remote_factory):
    return tofu_remote_factory()


@pytest.fixture
def get_tofu_content_paths(tofu_bindings):
    """Build closure for fetching content from a repository.

    :returns: A closure which returns content.
    """

    def _get_tofu_content_paths(repo, version_href=None):
        """Read the content units of a given repository.

        :param repo: An instance of TofuRepository.
        :param version_href: The repository version to read. If none, read the
            latest repository version.
        :returns: A list of information about the content units present in a
            given repository version.
        """
        version_href = version_href or repo.latest_version_href

        if version_href is None:
            # Repository has no latest version, and therefore no content.
            return defaultdict(list)

        repo_version = tofu_bindings.RepositoriesTofuVersionsApi.read(version_href)

        content = tofu_bindings.ContentPackagesApi.list(
            repository_version=repo_version.pulp_href
        ).results

        return [content_unit.relative_path for content_unit in content]

    return _get_tofu_content_paths
