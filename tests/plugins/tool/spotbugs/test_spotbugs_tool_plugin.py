"""Unit tests for the spotbugs plugin."""

import argparse
import os
import subprocess
import sys

import mock
import pytest

import statick_tool
from statick_tool.config import Config
from statick_tool.package import Package
from statick_tool.plugin_context import PluginContext
from statick_tool.plugins.tool.spotbugs import SpotbugsToolPlugin
from statick_tool.resources import Resources

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


def setup_spotbugs_tool_plugin(use_plugin_context=True, custom_rsc_path=None):
    """Initialize and return a spotbugs plugin."""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--mapping-file-suffix", dest="mapping_file_suffix", type=str
    )

    if custom_rsc_path is not None:
        resources = Resources([custom_rsc_path])
    else:
        resources = Resources(
            [os.path.join(os.path.dirname(statick_tool.__file__), "plugins")]
        )
    config = Config(resources.get_file("config.yaml"))
    plugin_context = PluginContext(arg_parser.parse_args([]), resources, config)
    plugin_context.args.output_directory = os.path.dirname(__file__)
    sbtp = SpotbugsToolPlugin()
    if use_plugin_context:
        sbtp.set_plugin_context(plugin_context)
    return sbtp


def test_spotbugs_tool_plugin_found():
    """Test that the plugin manager can find the spotbugs plugin."""
    plugins = {}
    tool_plugins = entry_points(group="statick_tool.plugins.tool")
    for plugin_type in tool_plugins:
        plugin = plugin_type.load()
        plugins[plugin_type.name] = plugin()
    assert any(
        plugin.get_name() == "spotbugs" for _, plugin in list(plugins.items())
    )


def test_spotbugs_tool_plugin_scan_valid():
    """Integration test: Make sure the spotbugs output hasn't changed."""
    sbtp = setup_spotbugs_tool_plugin()
    # Sanity check - make sure mvn exists
    if not sbtp.command_exists("mvn"):
        pytest.skip("Couldn't find 'mvn' command, can't run Spotbugs tests")
    elif sys.platform == "win32":
        pytest.skip("Don't know how to run spotbugs on Windows.")

    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    # Have to compile the package first
    try:
        subprocess.check_output(
            ["mvn", "clean", "compile"], universal_newlines=True, cwd=package.path
        )
    except subprocess.CalledProcessError as ex:
        print(f"Problem running Maven! Returncode = {str(ex.returncode)}")
        print(f"{ex.output}")
        pytest.fail("Failed running Maven")

    package["top_poms"] = [os.path.join(package.path, "pom.xml")]
    package["all_poms"] = [os.path.join(package.path, "pom.xml")]
    issues = sbtp.scan(package, "level")
    assert len(issues) == 1
    assert issues[0].line_number == 4
    assert issues[0].tool == "spotbugs"
    assert issues[0].issue_type == "MS_MUTABLE_COLLECTION_PKGPROTECT"
    assert issues[0].severity == 1
    assert (
        issues[0].message
        == "Test.h is a mutable collection which should be package protected"
    )


def test_spotbugs_tool_plugin_scan_no_plugin_context():
    """Test that issues are None when no plugin context is provided."""
    sbtp = setup_spotbugs_tool_plugin(False)
    # Sanity check - make sure mvn exists
    if not sbtp.command_exists("mvn"):
        pytest.skip("Couldn't find 'mvn' command, can't run Spotbugs tests")
    elif sys.platform == "win32":
        pytest.skip("Don't know how to run spotbugs on Windows.")

    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    # Have to compile the package first
    try:
        subprocess.check_output(
            ["mvn", "clean", "compile"], universal_newlines=True, cwd=package.path
        )
    except subprocess.CalledProcessError as ex:
        print(f"Problem running Maven! Returncode = {str(ex.returncode)}")
        print(f"{ex.output}")
        pytest.fail("Failed running Maven")

    package["top_poms"] = [os.path.join(package.path, "pom.xml")]
    package["all_poms"] = [os.path.join(package.path, "pom.xml")]
    issues = sbtp.scan(package, "level")
    assert issues is None


def test_spotbugs_tool_plugin_scan_custom_exclude():
    """Test that issues are still found when an exclude file is provided."""
    custom_rsc_path = os.path.dirname(__file__)
    sbtp = setup_spotbugs_tool_plugin(custom_rsc_path=custom_rsc_path)
    # Sanity check - make sure mvn exists
    if not sbtp.command_exists("mvn"):
        pytest.skip("Couldn't find 'mvn' command, can't run Spotbugs tests")
    elif sys.platform == "win32":
        pytest.skip("Don't know how to run spotbugs on Windows.")

    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    # Have to compile the package first
    try:
        subprocess.check_output(
            ["mvn", "clean", "compile"], universal_newlines=True, cwd=package.path
        )
    except subprocess.CalledProcessError as ex:
        print(f"Problem running Maven! Returncode = {str(ex.returncode)}")
        print(f"{ex.output}")
        pytest.fail("Failed running Maven")

    package["top_poms"] = [os.path.join(package.path, "pom.xml")]
    package["all_poms"] = [os.path.join(package.path, "pom.xml")]
    issues = sbtp.scan(package, "local")
    assert len(issues) == 1
    assert issues[0].line_number == 4
    assert issues[0].tool == "spotbugs"
    assert issues[0].issue_type == "MS_MUTABLE_COLLECTION_PKGPROTECT"
    assert issues[0].severity == 1
    assert (
        issues[0].message
        == "Test.h is a mutable collection which should be package protected"
    )


def test_spotbugs_tool_plugin_parse_valid():
    """Verify that we can parse the normal output of spotbugs."""
    sbtp = setup_spotbugs_tool_plugin()
    output = "<BugCollection version='3.1.11' threshold='low' effort='max'><file classname='Test'><BugInstance type='MS_MUTABLE_COLLECTION_PKGPROTECT' priority='Low' category='MALICIOUS_CODE' message='Test.h is a mutable collection which should be package protected' lineNumber='4'/></file><Error></Error><Project><SrcDir>{}</SrcDir></Project></BugCollection>".format(
        os.path.join(os.path.dirname(__file__), "valid_package", "src", "main", "java")
    )
    issues = sbtp.parse_file_output(output)
    assert len(issues) == 1
    assert issues[0].filename == os.path.join(
        os.path.dirname(__file__), "valid_package", "src", "main", "java", "Test.java"
    )
    assert issues[0].line_number == 4
    assert issues[0].tool == "spotbugs"
    assert issues[0].issue_type == "MS_MUTABLE_COLLECTION_PKGPROTECT"
    assert issues[0].severity == 1
    assert (
        issues[0].message
        == "Test.h is a mutable collection which should be package protected"
    )

    output = "<BugCollection version='3.1.11' threshold='low' effort='max'><file classname='Test'><BugInstance type='MS_MUTABLE_COLLECTION_PKGPROTECT' priority='Normal' category='MALICIOUS_CODE' message='Test.h is a mutable collection which should be package protected' lineNumber='4'/></file><Error></Error><Project><SrcDir>{}</SrcDir></Project></BugCollection>".format(
        os.path.join(os.path.dirname(__file__), "valid_package", "src", "main", "java")
    )
    assert len(issues) == 1
    issues = sbtp.parse_file_output(output)
    assert issues[0].severity == 3

    output = "<BugCollection version='3.1.11' threshold='low' effort='max'><file classname='Test'><BugInstance type='MS_MUTABLE_COLLECTION_PKGPROTECT' priority='High' category='MALICIOUS_CODE' message='Test.h is a mutable collection which should be package protected' lineNumber='4'/></file><Error></Error><Project><SrcDir>{}</SrcDir></Project></BugCollection>".format(
        os.path.join(os.path.dirname(__file__), "valid_package", "src", "main", "java")
    )
    issues = sbtp.parse_file_output(output)
    assert len(issues) == 1
    assert issues[0].severity == 5


def test_make_tool_plugin_parse_warnings_mapping():
    """Verify that we can associate a make warning with a SEI Cert warning."""
    sbtp = setup_spotbugs_tool_plugin()
    output = "<BugCollection version='3.1.11' threshold='low' effort='max'><file classname='Test'><BugInstance type='MS_MUTABLE_ARRAY' priority='Low' category='MALICIOUS_CODE' message='Test.h is a mutable collection which should be package protected' lineNumber='4'/></file><Error></Error><Project><SrcDir>{}</SrcDir></Project></BugCollection>".format(
        os.path.join(os.path.dirname(__file__), "valid_package", "src", "main", "java")
    )
    issues = sbtp.parse_file_output(output)
    assert len(issues) == 1
    assert issues[0].cert_reference == "OBJ10-J"


def test_spotbugs_tool_plugin_parse_invalid():
    """Verify that we can parse the normal output of spotbugs."""
    sbtp = setup_spotbugs_tool_plugin()
    output = "invalid text"
    issues = sbtp.parse_file_output(output)
    assert not issues


def test_spotbugs_tool_plugin_parse_wrong_file_path():
    """Verify that the wrong file path results in no issues found."""
    sbtp = setup_spotbugs_tool_plugin()
    output = "<BugCollection version='3.1.11' threshold='low' effort='max'><file classname='Test'><BugInstance type='MS_MUTABLE_COLLECTION_PKGPROTECT' priority='Low' category='MALICIOUS_CODE' message='Test.h is a mutable collection which should be package protected' lineNumber='4'/></file><Error></Error><Project></Project></BugCollection>"
    issues = sbtp.parse_file_output(output)
    assert len(issues) == 1
    assert issues[0].filename == "Test.java"


@mock.patch("statick_tool.plugins.tool.spotbugs.ToolPlugin.command_exists")
def test_spotbugs_tool_plugin_scan_commandnotfound(mock_command_exists):
    """Test what happens when self.command_exists returns False.

    Expected result: issues is an empty list
    """
    mock_command_exists.return_value = False
    sbtp = setup_spotbugs_tool_plugin()
    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    issues = sbtp.scan(package, "level")
    assert not issues


@mock.patch("statick_tool.plugins.tool.spotbugs.subprocess.check_output")
def test_spotbugs_tool_plugin_scan_oserror(mock_subprocess_check_output):
    """
    Test what happens when an OSError is raised (usually means maven doesn't exist - unlikely).

    Expected result: issues is None
    """
    mock_subprocess_check_output.side_effect = OSError("mocked error")
    sbtp = setup_spotbugs_tool_plugin()
    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    package["top_poms"] = [os.path.join(package.path, "pom.xml")]
    package["all_poms"] = [os.path.join(package.path, "pom.xml")]
    issues = sbtp.scan(package, "level")
    assert issues is None


@mock.patch("statick_tool.plugins.tool.spotbugs.subprocess.check_output")
def test_spotbugs_tool_plugin_scan_calledprocesserror(mock_subprocess_check_output):
    """Test what happens when a CalledProcessError is raised (usually means maven hit an
    error).

    Expected result: issues is None
    """
    mock_subprocess_check_output.side_effect = subprocess.CalledProcessError(
        1, "", output="error"
    )
    sbtp = setup_spotbugs_tool_plugin()
    package = Package(
        "valid_package", os.path.join(os.path.dirname(__file__), "valid_package")
    )
    package["top_poms"] = [os.path.join(package.path, "pom.xml")]
    package["all_poms"] = [os.path.join(package.path, "pom.xml")]
    issues = sbtp.scan(package, "level")
    assert issues is None
