from bot import CMD_SUFFIX


class _BotCommands:
    def __init__(self):
        self.StartCommand = "start"
        self.MirrorCommand = [
            f"mirror{CMD_SUFFIX}",
            f"m{CMD_SUFFIX}",
        ]
        self.QbMirrorCommand = [
            f"qbmirror{CMD_SUFFIX}",
            f"qbm{CMD_SUFFIX}",
        ]
        self.JdMirrorCommand = [
            f"jdmirror{CMD_SUFFIX}",
            f"jdm{CMD_SUFFIX}",
        ]
        self.NzbMirrorCommand = [
            f"nzbmirror{CMD_SUFFIX}",
            f"nzbm{CMD_SUFFIX}",
        ]
        self.YtdlCommand = [
            f"ytdlm{CMD_SUFFIX}",
            f"ytm{CMD_SUFFIX}",
        ]
        self.LeechCommand = [
            f"leech{CMD_SUFFIX}",
            f"l{CMD_SUFFIX}",
        ]
        self.QbLeechCommand = [
            f"qbleech{CMD_SUFFIX}",
            f"qbl{CMD_SUFFIX}",
        ]
        self.JdLeechCommand = [
            f"jdleech{CMD_SUFFIX}",
            f"jdl{CMD_SUFFIX}",
        ]
        self.NzbLeechCommand = [
            f"nzbleech{CMD_SUFFIX}",
            f"nzbl{CMD_SUFFIX}",
        ]
        self.YtdlLeechCommand = [
            f"ytdlleech{CMD_SUFFIX}",
            f"ytl{CMD_SUFFIX}",
        ]
        self.CloneCommand = f"clone{CMD_SUFFIX}"
        self.CountCommand = f"count{CMD_SUFFIX}"
        self.DeleteCommand = f"del{CMD_SUFFIX}"
        self.CancelTaskCommand = [
            f"abort{CMD_SUFFIX}",
            f"A{CMD_SUFFIX}",
        ]
        self.CancelAllCommand = f"cancelall{CMD_SUFFIX}"
        self.ForceStartCommand = [
            f"forcestart{CMD_SUFFIX}",
            f"fs{CMD_SUFFIX}",
        ]
        self.ListCommand = f"list{CMD_SUFFIX}"
        self.SearchCommand = f"search{CMD_SUFFIX}"
        self.StatusCommand = [
            f"status{CMD_SUFFIX}",
            "sall",
        ]
        self.UsersCommand = f"users{CMD_SUFFIX}"
        self.AuthorizeCommand = f"authorize{CMD_SUFFIX}"
        self.UnAuthorizeCommand = f"unauthorize{CMD_SUFFIX}"
        self.AddSudoCommand = f"addsudo{CMD_SUFFIX}"
        self.RmSudoCommand = f"rmsudo{CMD_SUFFIX}"
        self.PingCommand = [
            f"ping{CMD_SUFFIX}",
            "p",
        ]
        self.RestartCommand = f"restart{CMD_SUFFIX}"
        self.StatsCommand = [
            f"stats{CMD_SUFFIX}",
            "s",
        ]
        self.HelpCommand = f"help{CMD_SUFFIX}"
        self.LogCommand = f"log{CMD_SUFFIX}"
        self.ShellCommand = f"shell{CMD_SUFFIX}"
        self.AExecCommand = f"aexec{CMD_SUFFIX}"
        self.ExecCommand = f"exec{CMD_SUFFIX}"
        self.ClearLocalsCommand = f"clearlocals{CMD_SUFFIX}"
        self.BotSetCommand = [
            f"bsetting{CMD_SUFFIX}",
            f"bset{CMD_SUFFIX}",
            f"bs{CMD_SUFFIX}",
        ]
        self.UserSetCommand = [
            f"usetting{CMD_SUFFIX}",
            f"uset{CMD_SUFFIX}",
            f"us{CMD_SUFFIX}",
        ]
        self.SelectCommand = f"sel{CMD_SUFFIX}"
        self.RssCommand = f"rss{CMD_SUFFIX}"
        self.RmdbCommand = f"rmdb{CMD_SUFFIX}"
        self.RmalltokensCommand = f"rmat{CMD_SUFFIX}"


BotCommands = _BotCommands()
