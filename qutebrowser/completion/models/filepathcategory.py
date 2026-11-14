# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014-2020 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
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

"""Filesystem completion category for the open command."""

import glob
import os

from PyQt5.QtCore import QAbstractListModel, QModelIndex, Qt, QUrl

from qutebrowser.config import config


class Filesystem(QAbstractListModel):

    """Complete local paths and file URLs."""

    name = 'Filesystem'
    columns_to_filter = [0]
    delete_func = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paths = []

    def rowCount(self, parent=QModelIndex()):
        """Return the number of paths."""
        return 0 if parent.isValid() else len(self._paths)

    def data(self, index, role=Qt.DisplayRole):
        """Return a completion path for a valid index."""
        if (role != Qt.DisplayRole or not index.isValid() or
                index.column() != 0 or not 0 <= index.row() < len(self._paths)):
            return None
        return self._paths[index.row()]

    def set_pattern(self, pattern):
        """Replace the paths with matches for the given input."""
        paths = self._complete(pattern)
        self.beginResetModel()
        self._paths = paths
        self.endResetModel()

    @staticmethod
    def _complete(pattern):
        if not pattern:
            favorites = config.val.completion.favorite_paths
            return list(favorites) if favorites is not None else []

        is_url = pattern.startswith('file:///')
        path = QUrl(pattern).toLocalFile() if is_url else pattern
        home_prefix = ''
        expanded_home = ''
        try:
            if path.startswith('~'):
                home_prefix = path.split(os.sep, 1)[0]
                expanded_home = os.path.expanduser(home_prefix)
                if expanded_home == home_prefix:
                    return []
                path = expanded_home + path[len(home_prefix):]
            if not os.path.isabs(path) or '\0' in path:
                return []
            paths = sorted(glob.glob(glob.escape(path) + '*'))
        except (OSError, ValueError):
            return []

        if home_prefix:
            paths = [home_prefix + path[len(expanded_home):] for path in paths]
        if is_url:
            paths = [QUrl.fromLocalFile(path).toString() for path in paths]
        return paths
