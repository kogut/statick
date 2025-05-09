"""Unit tests for the pycodestyle plugin."""

import argparse
import os
import subprocess
import sys

import mock

import statick_tool
from statick_tool.config import Config
from statick_tool.package import Package
from statick_tool.plugin_context import PluginContext
from statick_tool.plugins.tool.pycodestyle import PycodestyleToolPlugin
from statick_tool.resources import Resources

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


def setup_pycodestyle_tool_plugin():
    """Create and return an instance of the PyCodeStyle plugin."""
    arg_parser = argparse.ArgumentParser()

    resources = Resources(
        [os.path.join(os.path.dirname(statick_tool.__file__), "plugins")]
    )
    config = Config(resources.get_file("config.yaml"))
    plugin_context = PluginContext(arg_parser.parse_args([]), resources, config)
    plugin_context.args.output_directory = os.path.dirname(__file__)
    pcstp = PycodestyleToolPlugin()
    pcstp.set_plugin_context(plugin_context)
    return pcstp


def test_pycodestyle_tool_plugin_found():
    """Test that the plugin manager can find the PyCodeStyle plugin."""
    plugins = {}
    tool_plugins = entry_points(group="statick_tool.plugins.tool")
    for plugin_type in tool_plugins:
        plugin = plugin_type.load()
        plugins[plugin_type.name] = plugin()
    assert any(
        plugin.get_name() == "pycodestyle" for _, plugin in list(plugins.items())
    )


def test_pycodestyle_tool_plugin_scan_valid():
    """Integration test: Make sure the pycodestyle output hasn't changed."""
    pcstp = setup_pycodestyle_tool_plugin()
    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    package["python_src"] = [
        os.path.join(os.path.dirname(__file__), "valid_package", "e501.py")
    ]
    issues = pcstp.scan(package, "level")
    assert len(issues) == 1


def test_pycodestyle_tool_plugin_parse_valid():
    """Verify that we can parse the normal output of pycodestyle."""
    pcstp = setup_pycodestyle_tool_plugin()
    output = "valid_package/e501.py:1: [E501] line too long (88 > 79 characters)"
    issues = pcstp.parse_output([output])
    assert len(issues) == 1
    assert issues[0].filename == "valid_package/e501.py"
    assert issues[0].line_number == 1
    assert issues[0].tool == "pycodestyle"
    assert issues[0].issue_type == "E501"
    assert issues[0].severity == 5
    assert issues[0].message == "line too long (88 > 79 characters)"


def test_pycodestyle_tool_plugin_parse_multiple_types():
    """Verify that we can parse the output of pycodestyle with comma-separated types."""
    pcstp = setup_pycodestyle_tool_plugin()
    output = "valid_package/e501.py:1: [E501,S101] line too long (88 > 79 characters)"
    issues = pcstp.parse_output([output])
    assert len(issues) == 1
    assert issues[0].issue_type == "E501"

    output = "valid_package/e501.py:1: [S101,] line too long (88 > 79 characters)"
    issues = pcstp.parse_output([output])
    assert len(issues) == 1
    assert issues[0].issue_type == "S101"


def test_pycodestyle_tool_plugin_parse_invalid():
    """Verify that we can parse the normal output of pycodestyle."""
    pcstp = setup_pycodestyle_tool_plugin()
    output = "invalid text"
    issues = pcstp.parse_output(output)
    assert not issues


@mock.patch("statick_tool.plugins.tool.pycodestyle.subprocess.check_output")
def test_pycodestyle_tool_plugin_scan_oserror(mock_subprocess_check_output):
    """Test what happens when an OSError is raised (usually means pycodestyle doesn't
    exist).

    Expected result: issues is None
    """
    mock_subprocess_check_output.side_effect = OSError("mocked error")
    pcstp = setup_pycodestyle_tool_plugin()
    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    package["python_src"] = [
        os.path.join(os.path.dirname(__file__), "valid_package", "e501.py")
    ]
    issues = pcstp.scan(package, "level")
    assert issues is None


@mock.patch("statick_tool.plugins.tool.pycodestyle.subprocess.check_output")
def test_pycodestyle_tool_plugin_scan_calledprocesserror(mock_subprocess_check_output):
    """Test what happens when a CalledProcessError is raised (usually means pycodestyle
    hit an error).

    Expected result: issues is None
    """
    mock_subprocess_check_output.side_effect = subprocess.CalledProcessError(
        0, "", output="mocked error"
    )
    pcstp = setup_pycodestyle_tool_plugin()
    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    package["python_src"] = [
        os.path.join(os.path.dirname(__file__), "valid_package", "e501.py")
    ]
    issues = pcstp.scan(package, "level")
    assert issues is None
