# -*- coding: utf-8 -*-
# 以下のようなRailsログにて、アクセス解析する
# 2019-03-03 11:17:53.541382 I [13042:puma 003] {request_id: d25efb37-436b-4fec-968a-afe1f1f79c9b, user_type: api_call} (29.6ms) Api::OrdersController -- Completed #update -- { :controller => "Api::OrdersController"・・・ }

from .base import Base
from denite import util
import logging

import os
import site
import re
import inflection

logger = logging.getLogger('DeniteSourceRailsLog')
logger.setLevel(10)

class Source(Base):
    # この行はone requestのなかで1つしかないと思っている

    # 最長: .*
    # 最短: .*?
    # 最長: .+
    # 最短: .+?
    # 最長: .?
    # 最短: .??

    # ローカル用
    pattern = re.compile("request_id: [a-z0-9-]{36}.*\s--\sCompleted\s#.*\s--\s(.*)")
    request_path_pattern = re.compile(",\s?:method\s?=>\s?\"(.*)\",.*\s?:path\s?=>\s?\"(.*)\",")
    request_controller_pattern = re.compile(":controller\s?=>\s?\"(.*?)\",") # 最短マッチ
    request_action_pattern = re.compile(":action\s?=>\s?\"(.*?)\",")     # 最短マッチ

    # cloudwatch log ログ用
    aws_pattern = re.compile(r'"request_id":"[a-z0-9-]{36}",.*"message":"Completed\s.*,"payload":(.*)')
    aws_request_path_pattern = re.compile(r'"method":"(.*?)","path":"(.*?)","status":([0-9]{3})')
    aws_request_controller_pattern = re.compile(r'"controller":"(.*?)",') # 最短マッチ
    aws_request_action_pattern = re.compile(r'"action":"(.*?)",')     # 最短マッチ
    aws_timestamp = re.compile(r',"timestamp":"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})\..*"')

    # 文字に対して、色をつけているコード(ANSI color codes)
    # ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    default_log_file = '/log/development.log'

    def __init__(self, vim):
        super().__init__(vim)
        self.name = 'rails_log'
        self.kind = 'rails_log'

    def on_init(self, context):
        cbname = self.vim.current.buffer.name
        context['__cbname'] = cbname
        self.root_path = util.path2project(self.vim, cbname, context.get('root_markers', ''))

        buffer_name = os.path.basename(cbname)
        _, ext = os.path.splitext(cbname)
        # 注意:
        #   - プロジェクトのRootの下でNeoVimを開いてください
        #   - development.log以外のファイルを処理したい時:
        #     - 拡張子: log
        #     - log/の下においてください。
        #     - vimで処理したいファイルを開いてください
        if (ext == '.log') and (buffer_name != '') and (buffer_name != 'development.log'):
            context['__target_rails_log_file'] = cbname
        else:
            context['__target_rails_log_file'] = self.root_path + Source.default_log_file

        # ログ見たいのであれば、development.logを denite-create-test/log/にいれてください。
        # tail -f log/rails_log.log
        if 'denite-create-test' in self.root_path:
            fh = logging.FileHandler(self.root_path + '/log/rails_log.log')
            logger.addHandler(fh)

    def gather_candidates(self, context):
        # logger.info(self.root_path)
        target_file = context['__target_rails_log_file']
        f = open(target_file, 'r')
        lines = f.readlines()
        f.close()

        if len(context['args']) == 0:
            target_lines = self._find_lines(lines)
            target_lines.reverse()
            return [self._convert(line_no, date_time, line, target_file) for line_no, date_time, line in target_lines]
        else:
            if context['args'][0] == 'aws':
                target_lines = self._find_lines_for_aws(lines)
                target_lines.reverse()
                return [self._convert_aws(line_no, date_time, line, target_file) for line_no, date_time, line in target_lines]
            else:
                print('nothing')

    # 2019-03-03 11:17:53.541382 I [13042:puma 003] {request_id: d25efb37-436b-4fec-968a-afe1f1f79c9b, user_type: api_call} (29.6ms) Api::OrdersController -- Completed #update -- { :controller => "Api::OrdersController"・・・ }
    def _find_lines(self, lines):
        target_lines = []
        for index, line in enumerate(lines):
            result = Source.pattern.search(line)
            if result is not None:
                date_time = line[0:19]
                line_no = index + 1
                target_lines.append([line_no, date_time, result])
        return target_lines

    def _convert(self, line_no, date_time, result, target_rails_log_file):
        params          = result[1]
        path            = self.get_request_path(params)
        controller_name = self.get_request_controller(params)
        action_name     = self.get_request_action(params)
        # logger.info(path)
        # logger.info(controller_name)
        # logger.info(action_name)
        return {
                    'word': str(line_no) + ':' + '[' + date_time + '] ' + path + ' => ' + controller_name + "#" + action_name,
                    'rails_log_line_no': str(line_no),
                    'target_rails_log_file': target_rails_log_file,
                    'action__path': self.get_controller_full_name(controller_name),
                    'action__pattern': '\<def ' + action_name + '\>'
                }

    def get_request_path(self, params):
        request_path = Source.request_path_pattern.search(params)
        if request_path is not None:
            return request_path[1] + ' ' + request_path[2]

    def get_request_controller(self, params):
        request_controller = Source.request_controller_pattern.search(params)
        if request_controller is not None:
            return request_controller[1]

    def get_request_action(self, params):
        request_action = Source.request_action_pattern.search(params)
        if request_action is not None:
            return request_action[1]

    def get_controller_full_name(self, conroller_name):
        conroller_name = inflection.underscore(conroller_name).replace('::', '/')
        return self.root_path + '/app/controllers/' + conroller_name + '.rb'

    #--------------------for_aws-----------------------------------------------
    def _find_lines_for_aws(self, lines):
        target_lines = []
        for index, line in enumerate(lines):
            result = Source.aws_pattern.search(line)
            if result is not None:
                line_no = index + 1
                date_time = Source.aws_timestamp.search(line)
                target_lines.append([line_no, date_time[1] + ' ' + date_time[2], result])
        return target_lines

    def _convert_aws(self, line_no, date_time, result, target_rails_log_file):
        params          = result[1]
        path            = self.get_request_path_for_aws(params)
        controller_name = self.get_request_controller_for_aws(params)
        action_name     = self.get_request_action_for_aws(params)

        return {
                    'word': str(line_no) + ':' + '['+ date_time + '] ' + path + ' => ' + controller_name + "#" + action_name,
                    'rails_log_line_no': str(line_no),
                    'target_rails_log_file': target_rails_log_file,
                    'action__path': self.get_controller_full_name(controller_name),
                    'action__pattern': '\<def ' + action_name + '\>'
                }

    def get_request_path_for_aws(self, params):
        request_path = Source.aws_request_path_pattern.search(params)
        if request_path is not None:
            return request_path[1] + ':' + request_path[3] + ' ' + request_path[2]

    def get_request_controller_for_aws(self, params):
        request_controller = Source.aws_request_controller_pattern.search(params)
        if request_controller is not None:
            return request_controller[1]

    def get_request_action_for_aws(self, params):
        request_action = Source.aws_request_action_pattern.search(params)
        if request_action is not None:
            return request_action[1]

