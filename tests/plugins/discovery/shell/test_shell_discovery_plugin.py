"""Unit tests for the Shell discovery plugin."""

import contextlib
import os
import sys

import pytest

from statick_tool.exceptions import Exceptions
from statick_tool.package import Package
from statick_tool.plugins.discovery.shell import ShellDiscoveryPlugin

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


# From https://stackoverflow.com/questions/2059482/shell-temporarily-modify-the-current-processs-environment
@contextlib.contextmanager
def modified_environ(*remove, **update):
    """Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.
    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]


def test_shell_discovery_plugin_found():
    """Test that the plugin manager finds the Shell discovery plugin."""
    discovery_plugins = {}
    plugins = entry_points(group="statick_tool.plugins.discovery")
    for plugin_type in plugins:
        plugin = plugin_type.load()
        discovery_plugins[plugin_type.name] = plugin()
    assert any(
        plugin.get_name() == "shell" for _, plugin in list(discovery_plugins.items())
    )


def test_shell_discovery_plugin_scan_valid():
    """Test that the Shell discovery plugin finds valid shell files."""
    shdp = ShellDiscoveryPlugin()
    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    shdp.scan(package, "level")
    expected = ["test.sh", os.path.join("ignore_this", "ignoreme.bash")]
    if shdp.file_command_exists():
        expected += [
            "oddextensionsh.source",
            "oddextensionbash.source",
            "oddextensionzsh.source",
            "oddextensioncsh.source",
            "oddextensionksh.source",
            "oddextensiondash.source",
        ]
    # We have to add the path to each of the above...yuck
    expected_fullpath = [os.path.join(package.path, filename) for filename in expected]
    # Neat trick to verify that two unordered lists are the same
    assert set(package["shell_src"]) == set(expected_fullpath)


def test_shell_discovery_plugin_scan_invalid():
    """Test that the discovery plugin doesn't find non-shell files."""
    shdp = ShellDiscoveryPlugin()
    if not shdp.file_command_exists():
        pytest.skip("File command does not exist. Skipping test that requires it.")
    package = Package(
        "invalid_package", os.path.join(os.path.dirname(__file__), "invalid_package")
    )
    shdp.scan(package, "level")
    assert not package["shell_src"]


def test_shell_discovery_plugin_scan_exceptions():
    """Test that the shell discovery plugin properly respects exceptions."""
    shdp = ShellDiscoveryPlugin()
    if not shdp.file_command_exists():
        pytest.skip("File command does not exist. Skipping test that requires it.")
    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    exceptions = Exceptions(os.path.join(os.path.dirname(__file__), "exceptions.yaml"))
    shdp.scan(package, "level", exceptions)
    expected_src = [
        "test.sh",
        "oddextensionsh.source",
        "oddextensionbash.source",
        "oddextensionzsh.source",
        "oddextensioncsh.source",
        "oddextensionksh.source",
        "oddextensiondash.source",
    ]
    # We have to add the path to each of the above...yuck
    expected_src_fullpath = [
        os.path.join(package.path, filename) for filename in expected_src
    ]
    # Neat trick to verify that two unordered lists are the same
    assert set(package["shell_src"]) == set(expected_src_fullpath)


def test_shell_discovery_plugin_no_file_cmd():
    """Test when file command does not exist.

    Test that files are not discovered with file command output if file command does not
    exist.
    """
    with modified_environ(PATH=""):
        shdp = ShellDiscoveryPlugin()
        package = Package(
            "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
        )
        shdp.scan(package, "level")
        expected = ["test.sh", os.path.join("ignore_this", "ignoreme.bash")]
        # We have to add the path to each of the above...yuck
        expected_fullpath = [
            os.path.join(package.path, filename) for filename in expected
        ]
        # Neat trick to verify that two unordered lists are the same
        assert set(package["shell_src"]) == set(expected_fullpath)
