# -*- coding: utf-8 -*-

# 参考: https://qiita.com/iyuuya/items/8a7e9cc0c9dd6d0e4c32
# http://koturn.hatenablog.com/category/neovim
from .base import Base
from denite import util
import logging

import os
import site
import re
import inflection

logger = logging.getLogger('DeniteSourceRailsActionLog')
logger.setLevel(10)

class Source(Base):
    default_log_file = '/log/meta_request.log'

    def __init__(self, vim):
        super().__init__(vim)
        self.name = 'rails_action'
        self.kind = 'file'

    def on_init(self, context):
        cbname = self.vim.current.buffer.name
        context['__cbname'] = cbname
        self.root_path = util.path2project(self.vim, cbname, context.get('root_markers', ''))

        buffer_name = os.path.basename(cbname)
        _, ext = os.path.splitext(cbname)
        context['__target_file'] = self.root_path + Source.default_log_file

        if 'denite-create-test' in self.root_path:
            fh = logging.FileHandler(self.root_path + '/log/rails_action.log')
            logger.addHandler(fh)

    def gather_candidates(self, context):
        target_file = context['__target_file']
        f = open(target_file, 'r')
        lines = f.readlines()
        f.close()
        # remove blank line
        lines = [line for line in lines if line.strip()]
        lines.reverse()

        return [self._convert(line) for line in lines]

    # sample of line string
    # 2022-04-06 15:16:26 Abc3Controller#index
    def _convert(self, line):
        controller_with_action = line.split()[2]
        action_name = controller_with_action.split('#')[1]
        controller_name = controller_with_action.split('#')[0]
        controller_name = inflection.underscore(controller_name).replace('::', '/')
        file_path = self.root_path + '/app/controllers/' + controller_name + '.rb'

        return {
                'word': line,
                'action__path': file_path,
                'action__pattern': '\<def ' + action_name + '\>'
                }

