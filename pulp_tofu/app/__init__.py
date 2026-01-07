from pulpcore.plugin import PulpPluginAppConfig


class PulpTofuPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the tofu plugin."""

    name = "pulp_tofu.app"
    label = "tofu"
    version = "0.0.1.dev"
    python_package_name = "pulp_tofu"
