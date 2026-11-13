# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2016-2020 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Tests for qutebrowser.misc.utilcmds."""

import pytest
from PyQt5.QtCore import QUrl

from qutebrowser.misc import utilcmds
from qutebrowser.api import cmdutils
from qutebrowser.utils import objreg, usertypes
from qutebrowser.commands import runners
from qutebrowser.qt import sip


class TestLater:

    @pytest.fixture
    def timer(self, qapp, qtbot, mocker, mode_manager):
        timer = usertypes.Timer(name='later', parent=qapp)
        constructor = mocker.patch('qutebrowser.misc.utilcmds.usertypes.Timer',
                                   return_value=timer)
        yield timer
        constructor.assert_called_once_with(name='later', parent=qapp)
        if not sip.isdeleted(timer):
            timer.stop()
            timer.deleteLater()
        qtbot.waitUntil(lambda: sip.isdeleted(timer))

    @pytest.fixture
    def runner(self, mocker):
        return mocker.patch('qutebrowser.misc.utilcmds.runners.CommandRunner')

    @pytest.mark.parametrize('duration, expected', [
        ('5s', 5000), ('2m30s', 150000), ('1h', 3600000), ('90', 90),
        ('+1s', 1000), ('0ms', 0), ('-0s', 0),
        ('2147483647', 2147483647), ('596h31m23s647ms', 2147483647),
    ])
    def test_interval(self, duration, expected, timer, runner, qapp):
        utilcmds.later(duration, 'message-info later', win_id=42)
        assert timer.interval() == expected
        assert timer.isSingleShot()
        assert timer.isActive()
        assert timer.parent() is qapp
        assert timer.objectName() == 'later'
        runner.assert_called_once_with(42)
        runner.return_value.run_safely.assert_not_called()
        timer.stop()

    @pytest.mark.parametrize('duration', ['-1', '-1s', '-2147483649ms'])
    def test_negative(self, duration, runner):
        with pytest.raises(cmdutils.CommandError,
                           match="I can't run something in the past!"):
            utilcmds.later(duration, 'scroll down', win_id=0)
        runner.assert_not_called()

    @pytest.mark.parametrize('duration', ['1.5s', '1m 2s', '1m30', 'invalid'])
    def test_invalid(self, duration, runner):
        with pytest.raises(cmdutils.CommandError, match='Invalid duration:'):
            utilcmds.later(duration, 'scroll down', win_id=0)
        runner.assert_not_called()

    @pytest.mark.parametrize('duration', [
        '2147483648', '2147483648ms', '596h31m23s648ms',
        '36893488147419103232s',
    ])
    def test_overflow_cleanup(self, duration, timer, runner, qtbot):
        error = ('Numeric argument is too large for internal int '
                 'representation.')
        with pytest.raises(cmdutils.CommandError, match=error):
            utilcmds.later(duration, 'scroll down', win_id=0)
        assert not timer.isActive()
        qtbot.waitUntil(lambda: sip.isdeleted(timer))
        runner.return_value.run_safely.assert_not_called()

    def test_start_failure_cleanup(self, timer, runner, mocker, qtbot):
        mocker.patch.object(timer, 'start', side_effect=RuntimeError('start'))
        with pytest.raises(RuntimeError, match='start'):
            utilcmds.later('1ms', 'scroll down', win_id=0)
        qtbot.waitUntil(lambda: sip.isdeleted(timer))
        runner.return_value.run_safely.assert_not_called()

    @pytest.mark.parametrize('duration', ['0', '20ms', '+10ms10ms'])
    def test_execution(self, duration, timer, runner, qtbot):
        command = 'message-info "hello world" ;; message-info {url}'
        with qtbot.waitSignal(timer.destroyed):
            utilcmds.later(duration, command, win_id=42)
            runner.return_value.run_safely.assert_not_called()
        runner.return_value.run_safely.assert_called_once_with(command)
        assert sip.isdeleted(timer)

    def test_command_forwarding(self, timer, runner, mode_manager):
        command = 'message-info "hello world" ;; message-info {url}'
        parsed = runners.CommandParser().parse('later 2m30s ' + command)
        assert parsed.args == ['2m30s', command]
        parsed.cmd.run(win_id=0, args=parsed.args)
        assert timer.interval() == 150000
        timer.stop()


def test_repeat_command_initial(mocker, mode_manager):
    """Test repeat_command first-time behavior.

    If :repeat-command is called initially, it should err, because there's
    nothing to repeat.
    """
    objreg_mock = mocker.patch('qutebrowser.misc.utilcmds.objreg')
    objreg_mock.get.return_value = mode_manager
    with pytest.raises(cmdutils.CommandError,
                       match="You didn't do anything yet."):
        utilcmds.repeat_command(win_id=0)


class FakeWindow:

    """Mock class for window_only."""

    def __init__(self, deleted=False):
        self.closed = False
        self.deleted = deleted

    def close(self):
        """Flag as closed."""
        self.closed = True


def test_window_only(mocker, monkeypatch):
    """Verify that window_only doesn't close the current or deleted windows."""
    test_windows = {0: FakeWindow(), 1: FakeWindow(True), 2: FakeWindow()}
    winreg_mock = mocker.patch('qutebrowser.misc.utilcmds.objreg')
    winreg_mock.window_registry = test_windows
    sip_mock = mocker.patch('qutebrowser.misc.utilcmds.sip')
    sip_mock.isdeleted.side_effect = lambda window: window.deleted
    utilcmds.window_only(current_win_id=0)
    assert not test_windows[0].closed
    assert not test_windows[1].closed
    assert test_windows[2].closed


@pytest.fixture
def tabbed_browser(stubs, win_registry):
    tb = stubs.TabbedBrowserStub()
    objreg.register('tabbed-browser', tb, scope='window', window=0)
    yield tb
    objreg.delete('tabbed-browser', scope='window', window=0)


def test_version(tabbed_browser, qapp):
    utilcmds.version(win_id=0)
    assert tabbed_browser.loaded_url == QUrl('qute://version/')
