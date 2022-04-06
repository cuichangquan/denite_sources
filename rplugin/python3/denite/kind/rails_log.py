from denite.kind.file import Kind as File 

class Kind(File):
    def __init__(self, vim):
        super().__init__(vim)
        self.name = 'rails_log'
        self.default_action = 'open'

    def action_jumpto_rails_log(self, context):
        # contextにはカーソルが置いている１行の関連Objectが入っている
        target = context['targets'][0]
        # debug 方法( カレントバファに出力 )
        # self._vim.current.buffer[:] = [str(target)]
        target_rails_log_file = target['target_rails_log_file']
        rails_log_line_no = target['rails_log_line_no']
        self._vim.command('edit +' + rails_log_line_no + ' ' + str(target_rails_log_file))
