# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from pytest import raises
from beehive3_cli.main import CliManagerTest

def test_beehive():
    # test beehive without any subcommands or arguments
    with CliManagerTest() as app:
        app.run()
        assert app.exit_code == 0


def test_beehive_debug():
    # test that debug mode is functional
    argv = ['--debug']
    with CliManagerTest(argv=argv) as app:
        app.run()
        assert app.debug is True


def test_command1():
    # test command1 without arguments
    argv = ['command1']
    with CliManagerTest(argv=argv) as app:
        app.run()
        data,output = app.last_rendered
        assert data['foo'] == 'bar'
        assert output.find('Foo => bar')


    # test command1 with arguments
    argv = ['command1', '--foo', 'not-bar']
    with CliManagerTest(argv=argv) as app:
        app.run()
        data,output = app.last_rendered
        assert data['foo'] == 'not-bar'
        assert output.find('Foo => not-bar')
