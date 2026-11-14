# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2026 qutebrowser contributors
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

"""Regression tests for the tab-select command."""

import pathlib
import types

import pytest

from qutebrowser.commands import cmdexc, runners
from qutebrowser.completion import completer
from qutebrowser.completion.models import configmodel, miscmodels
from qutebrowser.config import configdata
from qutebrowser.misc import objects


def test_tab_select_registration(configdata_init):
    command = objects.commands['tab-select']
    assert 'buffer' not in objects.commands
    assert command.takes_count()
    assert command._qute_args['index'].completion is miscmodels.buffer
    assert configdata.DATA['bindings.default'].default['normal']['gt'] == (
        'set-cmd-text -s :tab-select')


def test_buffer_is_unknown_unless_aliased(config_stub):
    parser = runners.CommandParser()
    with pytest.raises(cmdexc.NoSuchCommandError, match='buffer: no such command'):
        parser.parse_all('buffer')

    config_stub.val.aliases = {'buffer': 'tab-select'}
    assert parser.parse_all('buffer')[0].cmd.name == 'tab-select'


@pytest.mark.parametrize('factory,expected', [
    (miscmodels.command, 'tab-select'),
    (miscmodels.helptopic, ':tab-select'),
    (lambda *, info: configmodel.bind('gt', info=info), 'tab-select'),
])
@pytest.mark.parametrize('alias', [False, True])
def test_completion(factory, expected, alias, config_stub, key_config_stub,
                    monkeypatch):
    monkeypatch.setattr(objects, 'args', types.SimpleNamespace(debug=False))
    if alias:
        config_stub.val.aliases = {'buffer': 'tab-select'}
    info = completer.CompletionInfo(config=config_stub, keyconf=key_config_stub,
                                    win_id=0, cur_tab=None)
    model = factory(info=info)
    model.set_pattern('')
    names = [model.data(model.index(row, 0, parent=model.index(category, 0)))
             for category in range(model.rowCount())
             for row in range(model.rowCount(model.index(category, 0)))]
    assert expected in names
    assert ('buffer' in names) == (alias and expected == 'tab-select')
    assert ':buffer' not in names


def test_generated_help():
    root = pathlib.Path(__file__).resolve().parents[3]
    commands = (root / 'doc/help/commands.asciidoc').read_text(encoding='utf-8')
    settings = (root / 'doc/help/settings.asciidoc').read_text(encoding='utf-8')
    assert '[[tab-select]]' in commands
    assert 'Syntax: +:tab-select' in commands
    assert '[[buffer]]' not in commands
    assert 'set-cmd-text -s :tab-select' in settings
