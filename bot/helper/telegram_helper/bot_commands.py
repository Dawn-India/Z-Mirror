from bot import CMD_INDEX


class _BotCommands:
    def __init__(self):
        self.StartCommand = f'start{CMD_INDEX}'
        self.MirrorCommand = (f'mirror{CMD_INDEX}', f'm{CMD_INDEX}')
        self.UnzipMirrorCommand = (f'unzipmirror{CMD_INDEX}', f'um{CMD_INDEX}')
        self.ZipMirrorCommand = (f'zipmirror{CMD_INDEX}', f'zm{CMD_INDEX}')
        self.QbMirrorCommand = (f'qbmirror{CMD_INDEX}', f'qbm{CMD_INDEX}')
        self.QbUnzipMirrorCommand = (f'qbunzipmirror{CMD_INDEX}', f'qbum{CMD_INDEX}')
        self.QbZipMirrorCommand = (f'qbzipmirror{CMD_INDEX}', f'qbzm{CMD_INDEX}')
        self.YtdlCommand = (f'ytdl{CMD_INDEX}', f'y{CMD_INDEX}')
        self.YtdlZipCommand = (f'ytdlzip{CMD_INDEX}', f'yz{CMD_INDEX}')
        self.LeechCommand = (f'leech{CMD_INDEX}', f'l{CMD_INDEX}')
        self.UnzipLeechCommand = (f'unzipleech{CMD_INDEX}', f'ul{CMD_INDEX}')
        self.ZipLeechCommand = (f'zipleech{CMD_INDEX}', f'zl{CMD_INDEX}')
        self.QbLeechCommand = (f'qbleech{CMD_INDEX}', f'qbl{CMD_INDEX}')
        self.QbUnzipLeechCommand = (f'qbunzipleech{CMD_INDEX}', f'qbul{CMD_INDEX}')
        self.QbZipLeechCommand = (f'qbzipleech{CMD_INDEX}', f'qbzl{CMD_INDEX}')
        self.YtdlLeechCommand = (f'ytdlleech{CMD_INDEX}', f'yl{CMD_INDEX}')
        self.YtdlZipLeechCommand = (f'ytdlzipleech{CMD_INDEX}', f'yzl{CMD_INDEX}')
        self.CloneCommand = (f'clone{CMD_INDEX}', f'c{CMD_INDEX}')
        self.CountCommand = f'count{CMD_INDEX}'
        self.DeleteCommand = f'del{CMD_INDEX}'
        self.CancelMirror = f'cm{CMD_INDEX}'
        self.CancelAllCommand = (f'cancelall{CMD_INDEX}', f'ca{CMD_INDEX}')
        self.ListCommand = (f'list{CMD_INDEX}', f'find{CMD_INDEX}')
        self.SearchCommand = f'search{CMD_INDEX}'
        self.StatusCommand = (f'status{CMD_INDEX}', f's{CMD_INDEX}')
        self.AuthorizedUsersCommand = f'users{CMD_INDEX}'
        self.AuthorizeCommand = (f'authorize{CMD_INDEX}', f'a{CMD_INDEX}')
        self.UnAuthorizeCommand = (f'unauthorize{CMD_INDEX}', f'ua{CMD_INDEX}')
        self.AddSudoCommand = f'addsudo{CMD_INDEX}'
        self.RmSudoCommand = f'rmsudo{CMD_INDEX}'
        self.PingCommand = (f'ping{CMD_INDEX}', f'p{CMD_INDEX}')
        self.RestartCommand = (f'restart{CMD_INDEX}', f'r{CMD_INDEX}')
        self.StatsCommand = f'stats{CMD_INDEX}'
        self.HelpCommand = (f'help{CMD_INDEX}', f'h{CMD_INDEX}')
        self.LogCommand = f'log{CMD_INDEX}'
        self.ShellCommand = (f'shell{CMD_INDEX}', f'sh{CMD_INDEX}')
        self.EvalCommand = (f'eval{CMD_INDEX}', f'e{CMD_INDEX}')
        self.ExecCommand = f'exec{CMD_INDEX}'
        self.ClearLocalsCommand = f'clearlocals{CMD_INDEX}'
        self.LeechSetCommand = f'leechset{CMD_INDEX}'
        self.SetThumbCommand = f'setthumb{CMD_INDEX}'
        self.BtSelectCommand = f'btsel{CMD_INDEX}'
        self.RssListCommand = (f'rsslist{CMD_INDEX}', f'rl{CMD_INDEX}')
        self.RssGetCommand = (f'rssget{CMD_INDEX}', f'rg{CMD_INDEX}')
        self.RssSubCommand = (f'rsssub{CMD_INDEX}', f'rs{CMD_INDEX}')
        self.RssUnSubCommand = (f'rssunsub{CMD_INDEX}', f'rus{CMD_INDEX}')
        self.RssSettingsCommand = (f'rssset{CMD_INDEX}', f'rst{CMD_INDEX}')
        self.AddleechlogCommand = (f'addleechlog{CMD_INDEX}')
        self.RmleechlogCommand = (f'rmleechlog{CMD_INDEX}')

BotCommands = _BotCommands()
