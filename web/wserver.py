from logging import INFO, FileHandler, StreamHandler, basicConfig, getLogger
from os import path
from subprocess import check_output
from time import sleep, time
from aria2p import API as ariaAPI
from aria2p import Client as ariaClient
from flask import Flask, request
from psutil import boot_time, disk_usage, net_io_counters
from qbittorrentapi import Client as qbClient
from qbittorrentapi import NotFound404Error
from web.nodes import make_tree

app = Flask(__name__)

basicConfig(format='%(levelname)s | From %(name)s -> %(module)s line no: %(lineno)d | %(message)s',
                    handlers=[FileHandler('Z_Logs.txt'), StreamHandler()], level=INFO)

aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))

LOGGER = getLogger(__name__)

rawowners = "<h1 style='text-align: center'>See my Channel <a href='https://telegram.me/z_mirror'>@Telegram</a><br><br>By<br><br><a href='https://github.com/Dawn-India/Z-Mirror'>Z-Mirror</a></h1>"

pin_entry = '''
    <section>
      <form action="{form_url}">
        <div>
          <label for="pin_code">Pin Code :</label>
          <input
            type="text"
            name="pin_code"
            placeholder="Enter the code that you have got from Telegram to access the Torrent"
          />
        </div>
        <button type="submit" class="btn btn-primary">Submit</button>
      </form>
          <span>* Dont mess around. Your download will get messed up.</>
    </section>
'''
files_list = '''
    <div id="sticks">
        <h4>Selected files: <b id="checked_files">0</b> of <b id="total_files">0</b></h4>
        <h4>Selected files size: <b id="checked_size">0</b> of <b id="total_size">0</b></h4>
    </div>
    <section>
        <input type="hidden" name="URL" id="URL" value="{form_url}" />
        <form id="SelectedFilesForm" name="SelectedFilesForm">
            <!-- {My_content} -->
            <input type="submit" name="Submit" />
        </form>
    </section>
'''
rawindexpage = '''
<html lang="en">

<head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Torrent File Selector</title>
    <link rel="icon" href="https://graph.org/file/43af672249c94053356c7.jpg" type="image/jpg">
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
        href="https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap"
        rel="stylesheet" />
    <link rel="stylesheet" href="https://pro.fontawesome.com/releases/v5.10.0/css/all.css"
        integrity="sha384-AYmEC3Yw5cVb3ZcuHtOA93w35dYTsvhLPVnYs9eStHfGJvOvKxVfELGroGkvsg+p" crossorigin="anonymous" />
    <script src="//cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js"></script>
    <link href="//cdn.jsdelivr.net/npm/@sweetalert2/theme-dark@4/dark.css" rel="stylesheet">
    <script src="//cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.js"></script>
    <style>
        /* style1 */
        /* style2 */
    </style>
</head>

<body>
    <!--© Designed and coded by @bipuldey19-Telegram-->
    <header>
        <div class="brand">
            <img src="https://graph.org/file/43af672249c94053356c7.jpg" alt="logo" />
        </div>
        <h2 class="name">Qbittorrent Selection</h2>
        <div class="social">
            <a href="https://www.github.com/Dawn-India/Z-Mirror"><i class="fab fa-github"></i></a>
            <a href="https://telegram.me/Z_Mirror"><i class="fab fa-telegram"></i></a>
        </div>
    </header>
    <!-- pin_entry -->
    <!-- files_list -->
    <!-- Print -->
    <script>
        $(document).ready(function () {
            docready();
            var tags = $("li").filter(function () {
                return $(this).find("ul").length !== 0;
            });
            tags.each(function () {
                $(this).addClass("parent");
            });
            $("body").find("ul:first-child").attr("id", "treeview");
            $(".parent").prepend("<span>▶</span>");
            $("span").click(function (e) {
                e.stopPropagation();
                e.stopImmediatePropagation();
                $(this).parent(".parent").find(">ul").toggle("slow");
                if ($(this).hasClass("active")) $(this).removeClass("active");
                else $(this).addClass("active");
            });
        });
        if (document.getElementsByTagName("ul").length >= 10) {
            var labels = document.querySelectorAll("label");
            //Shorting the file/folder names
            labels.forEach(function (label) {
                if (label.innerText.toString().split(" ").length >= 9) {
                    let FirstPart = label.innerText
                        .toString()
                        .split(" ")
                        .slice(0, 5)
                        .join(" ");
                    let SecondPart = label.innerText
                        .toString()
                        .split(" ")
                        .splice(-5)
                        .join(" ");
                    label.innerText = `${FirstPart}... ${SecondPart}`;
                }
                if (label.innerText.toString().split(".").length >= 9) {
                    let first = label.innerText
                        .toString()
                        .split(".")
                        .slice(0, 5)
                        .join(" ");
                    let second = label.innerText
                        .toString()
                        .split(".")
                        .splice(-5)
                        .join(".");
                    label.innerText = `${first}... ${second}`;
                }
            });
        }
    </script>
    <script>
        var set_selections = function (url) {
            var promt = 'You selected ' + $('#checked_files').text() + ' files';
            promt += ' and size of ' + $('#checked_size').text();
            if ($("input[name^='filenode_']:checked").length == 0) {
                Swal.fire({
                    title: "Sorry!",
                    text: "You Have to select alist one file!",
                    icon: "error",
                    confirmButtonText: "Try Again",
                    heightAuto: true,
                    allowOutsideClick: false
                });
            } else {
                Swal.fire({
                    title: 'Are you sure?',
                    text: promt.toString(),
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#5cb85c',
                    cancelButtonColor: '#d33',
                    confirmButtonText: '<i class="fa fa-thumbs-up"></i>',
                    cancelButtonText: '<i class="fa fa-times"></i>'
                }).then((result) => {
                    if (result.isConfirmed) {
                        $.ajax({
                            url: url,
                            type: 'POST',
                            contentType: 'application/x-www-form-urlencoded',
                            data: $("#SelectedFilesForm").serialize(),
                            beforeSend: function () {
                                Swal.fire({
                                    title: 'Please wait...',
                                    allowOutsideClick: false,
                                    allowEscapeKey: false,
                                    allowEnterKey: false,
                                    didOpen: () => {
                                        Swal.showLoading()
                                    }
                                })
                            },
                            success: function (data, textStatus, jQxhr) {
                                Swal.fire({
                                    title: "Selection Updated!",
                                    text: "Now you can start download!",
                                    icon: "success",
                                    confirmButtonText: "Okay",
                                    heightAuto: true,
                                    allowOutsideClick: false
                                });

                            },
                            error: function (jqXhr, textStatus, errorThrown) {
                                Swal.fire({
                                    title: "Something went wrong!",
                                    text: "Check Console log!",
                                    icon: "error",
                                    confirmButtonText: "Okay",
                                    heightAuto: true,
                                    allowOutsideClick: false
                                });
                                console.log(errorThrown);
                            }
                        });
                    }
                });
            }
        }
        $(document).ready(function () {
            $("#SelectedFilesForm").on("submit", function (e) {
                e.preventDefault();
                var url = $("#URL").val();
                set_selections(url);
            });
        });
    </script>
    <script>
        $('input[type="checkbox"]').change(function (e) {
            var checked = $(this).prop("checked"),
                container = $(this).parent(),
                siblings = container.siblings();
            /*
            $(this).attr('value', function(index, attr){
               return attr == 'yes' ? 'noo' : 'yes';
            });
            */
            container.find('input[type="checkbox"]').prop({
                indeterminate: false,
                checked: checked
            });

            function checkSiblings(el) {
                var parent = el.parent().parent(),
                    all = true;
                el.siblings().each(function () {
                    let returnValue = all = ($(this).children('input[type="checkbox"]').prop(
                        "checked") === checked);
                    return returnValue;
                });

                if (all && checked) {
                    parent.children('input[type="checkbox"]').prop({
                        indeterminate: false,
                        checked: checked
                    });
                    checkSiblings(parent);
                } else if (all && !checked) {
                    parent.children('input[type="checkbox"]').prop("checked", checked);
                    parent.children('input[type="checkbox"]').prop("indeterminate", (parent.find(
                        'input[type="checkbox"]:checked').length > 0));
                    checkSiblings(parent);
                } else {
                    el.parents("li").children('input[type="checkbox"]').prop({
                        indeterminate: true,
                        checked: false
                    });
                }
            }
            checkSiblings(container);
        });
    </script>
    <script>
        function docready() {
            $("label[for^='filenode_']").css("cursor", "pointer");
            $("label[for^='filenode_']").click(function () {
                $(this).prev().click();
            });
            checked_size();
            checkingfiles();
            var total_files = $("label[for^='filenode_']").length;
            $("#total_files").text(total_files);
            var total_size = 0;
            var ffilenode = $("label[for^='filenode_']");
            ffilenode.each(function () {
                var size = parseFloat($(this).data("size"));
                total_size += size;
                $(this).append(" - " + humanFileSize(size));
            });
            $("#total_size").text(humanFileSize(total_size));
        };
        function checked_size() {
            var checked_size = 0;
            var checkedboxes = $("input[name^='filenode_']:checked");
            checkedboxes.each(function () {
                var size = parseFloat($(this).data("size"));
                checked_size += size;
            });
            $("#checked_size").text(humanFileSize(checked_size));
        }
        function checkingfiles() {
            var checked_files = $("input[name^='filenode_']:checked").length;
            $("#checked_files").text(checked_files);
        }
        $("input[name^='foldernode_']").change(function () {
            checkingfiles();
            checked_size();
        });
        $("input[name^='filenode_']").change(function () {
            checkingfiles();
            checked_size();
        });
        function humanFileSize(size) {
            var i = -1;
            var byteUnits = [' kB', ' MB', ' GB', ' TB', 'PB', 'EB', 'ZB', 'YB'];
            do {
                size = size / 1024;
                i++;
            } while (size > 1024);
            return Math.max(size, 0).toFixed(1) + byteUnits[i];
        }
        function sticking() {
            var window_top = $(window).scrollTop();
            var div_top = $('.brand').offset().top;
            if (window_top > div_top) {
                $('#sticks').addClass('stick');
            } else {
                $('#sticks').removeClass('stick');
            }
        }
        $(function () {
            $(window).scroll(sticking);
            sticking();
        });
    </script>
</body>

</html>
'''
stlye1 = '''
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: "Ubuntu", sans-serif;
  list-style: none;
  text-decoration: none;
  color: white;
}

body {
  background-color: #0d1117;
}

header {
  margin: 3vh 1vw;
  padding: 0.5rem 1rem 0.5rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: #161b22;
  border-radius: 30px;
  background-color: #161b22;
  border: 2px solid rgba(255, 255, 255, 0.11);
}

header:hover, section:hover {
  box-shadow: 0px 0px 15px black;
}

.brand {
  display: flex;
  align-items: center;
}

img {
  width: 2.5rem;
  height: 2.5rem;
  border: 2px solid black;
  border-radius: 50%;
}

.name {
  color: white;
  margin-left: 1vw;
  font-size: 1.5rem;
}

.intro {
  text-align: center;
  margin-bottom: 2vh;
  margin-top: 1vh;
}

.social a {
  font-size: 1.5rem;
  color: white;
  padding-left: 1vw;
}

.social a:hover, .brand:hover {
  filter: invert(0.3);
}

section {
  margin: 0vh 1vw;
  margin-bottom: 10vh;
  padding: 1vh 3vw;
  display: flex;
  flex-direction: column;
  border: 2px solid rgba(255, 255, 255, 0.11);
  border-radius: 20px;
  background-color: #161b22;
  color: white;
}

section form {
  display: flex;
  margin-left: auto;
  margin-right: auto;
  flex-direction: column;
}

section div {
  background-color: #0d1117;
  border-radius: 20px;
  max-width: fit-content;
  padding: 0.7rem;
  margin-top: 2vh;
}

section label {
  font-size: larger;
  font-weight: 500;
  margin: 0 0 0.5vh 1.5vw;
  display: block;
}

section input[type="text"] {
  border-radius: 20px;
  outline: none;
  width: 50vw;
  height: 4vh;
  padding: 1rem;
  margin: 0.5vh;
  border: 2px solid rgba(255, 255, 255, 0.11);
  background-color: #3e475531;
  box-shadow: inset 0px 0px 10px black;
}

section input[type="text"]:focus {
  border-color: rgba(255, 255, 255, 0.404);
}

section button {
  border-radius: 20px;
  margin-top: 1vh;
  width: 100%;
  height: 5.5vh;
  border: 2px solid rgba(255, 255, 255, 0.11);
  background-color: #0d1117;
  color: white;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 200ms ease;
}

section button:hover, section button:focus {
  background-color: rgba(255, 255, 255, 0.068);
}

section span {
  display: block;
  font-size: x-small;
  margin: 1vh;
  font-weight: 100;
  font-style: italic;
  margin-left: 23%;
  margin-right: auto;
  margin-bottom: 2vh;
}

@media (max-width: 768px) {
  section form {
    flex-direction: column;
    width: 90vw;
  }
  section div {
    max-width: 100%;
    margin-bottom: 1vh;
  }
  section label {
    margin-left: 3vw;
    margin-top: 1vh;
  }
  section input[type="text"] {
    width: calc(100% - 0.3rem);
  }
  section button {
    width: 100%;
    height: 5vh;
    display: block;
    margin-left: auto;
    margin-right: auto;
  }
  section span {
    margin-left: 5%;
  }
}
'''
stlye2 = '''
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: "Ubuntu", sans-serif;
  list-style: none;
  text-decoration: none;
  outline: none !important;
  color: white;
}

body {
  background-color: #0d1117;
}

header {
  margin: 3vh 1vw;
  padding: 0.5rem 1rem 0.5rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: #161b22;
  border-radius: 30px;
  background-color: #161b22;
  border: 2px solid rgba(255, 255, 255, 0.11);
}

header:hover, section:hover {
  box-shadow: 0px 0px 15px black;
}

.brand {
  display: flex;
  align-items: center;
}

img {
  width: 2.5rem;
  height: 2.5rem;
  border: 2px solid black;
  border-radius: 50%;
}

.name {
  margin-left: 1vw;
  font-size: 1.5rem;
}

.intro {
  text-align: center;
  margin-bottom: 2vh;
  margin-top: 1vh;
}

.social a {
  font-size: 1.5rem;
  padding-left: 1vw;
}

.social a:hover, .brand:hover {
  filter: invert(0.3);
}

section {
  margin: 0vh 1vw;
  margin-bottom: 10vh;
  padding: 1vh 3vw;
  display: flex;
  flex-direction: column;
  border: 2px solid rgba(255, 255, 255, 0.11);
  border-radius: 20px;
  background-color: #161b22;
}

li:nth-child(1) {
  padding: 1rem 1rem 0.5rem 1rem;
}

li:nth-child(n + 1) {
  padding-left: 1rem;
}

li label {
  padding-left: 0.5rem;
}

li {
  padding-bottom: 0.5rem;
}

form ul li span {
  margin-right: 0.5rem;
  cursor: pointer;
  user-select: none;
  transition: transform 200ms ease-out;
}

span.active {
  transform: rotate(90deg);
  /* for IE  */
  -ms-transform: rotate(90deg);
  /* for browsers supporting webkit (such as chrome, firefox, safari etc.). */
  -webkit-transform: rotate( 90deg);
  display: inline-block;
}

ul {
  margin: 1vh 1vw 1vh 1vw;
  padding: 0 0 0.5rem 0;
  border: 2px solid black;
  border-radius: 20px;
  background-color: #1c2129;
  overflow: hidden;
}

input[type="checkbox"] {
  cursor: pointer;
  user-select: none;
}

input[type="submit"] {
  border-radius: 20px;
  margin: 2vh auto 1vh auto;
  width: 50%;
  display: block;
  height: 5.5vh;
  border: 2px solid rgba(255, 255, 255, 0.11);
  background-color: #0d1117;
  font-size: 16px;
  font-weight: 500;
}

input[type="submit"]:hover, input[type="submit"]:focus {
  background-color: rgba(255, 255, 255, 0.068);
  cursor: pointer;
}

@media (max-width: 768px) {
  input[type="submit"] {
    width: 100%;
  }
}

#treeview .parent {
  position: relative;
}

#treeview .parent>ul {
  display: none;
}

#sticks {
  margin: 0vh 1vw;
  margin-bottom: 1vh;
  padding: 1vh 3vw;
  display: flex;
  flex-direction: column;
  border: 2px solid rgba(255, 255, 255, 0.11);
  border-radius: 20px;
  background-color: #161b22;
  align-items: center;
}

#sticks.stick {
  position: sticky;
  top: 0;
  z-index: 10000;
}
'''

def re_verfiy(paused, resumed, client, hash_id):

    paused = paused.strip()
    resumed = resumed.strip()
    if paused:
        paused = paused.split("|")
    if resumed:
        resumed = resumed.split("|")
    k = 0
    while True:

        res = client.torrents_files(torrent_hash=hash_id)
        verify = True

        for i in res:
            if str(i.id) in paused and i.priority != 0:
                verify = False
                break

            if str(i.id) in resumed and i.priority == 0:
                verify = False
                break

        if verify:
            break
        LOGGER.info("Reverification Failed! Correcting stuff...")
        client.auth_log_out()
        sleep(1)
        client = qbClient(host="localhost", port="8090")
        try:
            client.torrents_file_priority(torrent_hash=hash_id, file_ids=paused, priority=0)
        except NotFound404Error:
            raise NotFound404Error
        except Exception as e:
            LOGGER.error(f"{e} Errored in reverification paused!")
        try:
            client.torrents_file_priority(torrent_hash=hash_id, file_ids=resumed, priority=1)
        except NotFound404Error:
            raise NotFound404Error
        except Exception as e:
            LOGGER.error(f"{e} Errored in reverification resumed!")
        k += 1
        if k > 5:
            return False
    LOGGER.info(f"Verified! Hash: {hash_id}")
    return True

@app.route('/app/files/<string:id_>', methods=['GET'])
def list_torrent_contents(id_):

    if "pin_code" not in request.args.keys():
        return rawindexpage.replace("/* style1 */", stlye1).replace("<!-- pin_entry -->", pin_entry) \
            .replace("{form_url}", f"/app/files/{id_}")

    pincode = ""
    for nbr in id_:
        if nbr.isdigit():
            pincode += str(nbr)
        if len(pincode) == 4:
            break
    if request.args["pin_code"] != pincode:
        return rawindexpage.replace("/* style1 */", stlye1).replace(
            "<!-- Print -->", "<h1 style='text-align: center;color: red;'>Incorrect pin code</h1>")

    if len(id_) > 20:
        client = qbClient(host="localhost", port="8090")
        res = client.torrents_files(torrent_hash=id_)
        cont = make_tree(res)
        client.auth_log_out()
    else:
        aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))
        res = aria2.client.get_files(id_)
        cont = make_tree(res, True)
    return rawindexpage.replace("/* style2 */", stlye2).replace("<!-- files_list -->", files_list) \
        .replace("{form_url}", f"/app/files/{id_}?pin_code={pincode}") \
        .replace("<!-- {My_content} -->", cont[0])

@app.route('/app/files/<string:id_>', methods=['POST'])
def set_priority(id_):
    data = dict(request.form)
    resume = ""
    if len(id_) > 20:
        pause = ""

        for i, value in data.items():
            if "filenode" in i:
                node_no = i.split("_")[-1]

                if value == "on":
                    resume += f"{node_no}|"
                else:
                    pause += f"{node_no}|"

        pause = pause.strip("|")
        resume = resume.strip("|")

        client = qbClient(host="localhost", port="8090")

        try:
            client.torrents_file_priority(torrent_hash=id_, file_ids=pause, priority=0)
        except NotFound404Error:
            raise NotFound404Error
        except Exception as e:
            LOGGER.error(f"{e} Errored in paused")
        try:
            client.torrents_file_priority(torrent_hash=id_, file_ids=resume, priority=1)
        except NotFound404Error:
            raise NotFound404Error
        except Exception as e:
            LOGGER.error(f"{e} Errored in resumed")
        sleep(1)
        if not re_verfiy(pause, resume, client, id_):
            LOGGER.error(f"Verification Failed! Hash: {id_}")
        client.auth_log_out()
    else:
        for i, value in data.items():
            if "filenode" in i and value == "on":
                node_no = i.split("_")[-1]
                resume += f'{node_no},'

        resume = resume.strip(",")

        aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))
        res = aria2.client.change_option(id_, {'select-file': resume})
        if res == "OK":
            LOGGER.info(f"Verified! Gid: {id_}")
        else:
            LOGGER.info(f"Verification Failed! Report! Gid: {id_}")
    return list_torrent_contents(id_)

botStartTime = time()
if path.exists('.git'):
    commit_date = check_output(["git log -1 --date=format:'%y/%m/%d %H:%M' --pretty=format:'%cd'"], shell=True).decode()
else:
    commit_date = 'No UPSTREAM_REPO'

@app.route('/status', methods=['GET'])
def status():
    bot_uptime = time() - botStartTime
    uptime = time() - boot_time()
    sent = net_io_counters().bytes_sent
    recv = net_io_counters().bytes_recv
    return {
        'commit_date': commit_date,
        'uptime': uptime,
        'on_time': bot_uptime,
        'free_disk': disk_usage('.').free,
        'total_disk': disk_usage('.').total,
        'network': {
            'sent': sent,
            'recv': recv,
        },
    }
@app.route('/')
def homepage():
    return rawindexpage.replace("/* style2 */", stlye2).replace("<!-- Print -->", rawowners)

@app.errorhandler(Exception)
def page_not_found(e):
    return rawindexpage.replace("/* style2 */", stlye2) \
                    .replace("<!-- Print -->", f"<h1 style='text-align: center;color: red;'>404: Torrent not found! Mostly wrong input. <br><br>Error: {e}</h1>"), 404

if __name__ == "__main__":
    app.run()
