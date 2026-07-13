from kikuchi_lab.cli.main import main


def test_version_command_reports_package_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "kikuchi-lab 0.1.0"
