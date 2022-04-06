# -*- coding: utf-8 -*-

from .base import Base
from denite import util
import logging

import os
import site
import re
import inflection
from subprocess import Popen, PIPE

logger = logging.getLogger('DeniteSourceStLog')
logger.setLevel(10)

class Source(Base):

    def __init__(self, vim):
        super().__init__(vim)
        self.name = 'st'
        self.kind = 'file'

    def on_init(self, context):
        cbname = self.vim.current.buffer.name
        context['__cbname'] = cbname
        self.root_path = util.path2project(self.vim, cbname, context.get('root_markers', ''))
        # TODO: いつも、inputの数値が入力されてしまう、
        # context['prev_input'] = ""

        if 'denite-create-test' in self.root_path:
            fh = logging.FileHandler(self.root_path + '/log/st.log')
            logger.addHandler(fh)

    # git diff @ --name-only
    # git diff @^ --name-only
    # git diff @^^ --name-only
    def gather_candidates(self, context):
        number = context['args']

        if number == []:
            git_command = 'git diff @ --name-only'
        else:
            # :Denite -input=1 st
            git_command = f'git diff @~{number[0]} --name-only'

        files = self.exec_cmd(git_command)
        return [self._convert(f) for f in files]

    def _convert(self, file):
        return {
                    'word': file,
                    'action__path': file
                }

    def exec_cmd(self, cmd):
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        logger.info(out)
        return out.decode().split('\n')
