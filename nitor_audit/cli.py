import argparse
import webbrowser
import socket
import socketserver
import contextlib
import sys
import os
import _thread
from http.server import BaseHTTPRequestHandler
from tempfile import mkstemp
from subprocess import Popen, PIPE

try:
    # For Python 3.5 and later
    from urllib.parse import quote
except ImportError:
    from urlparse import quote  # noqa: F401



SERVER = None
CREATE_USER_DATA = None
CRONTAB = \
"""SHELL=/bin/bash
PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin
MAILTO=root
*/2 * * * * root audit.sh \"{}\" \"{}\" \"{}\" >> /var/log/nitor-audit.log 2>&1
"""

SUDO_EXEC = \
"""mkdir -p /root/.ssh && \\
  chmod 700 /root/.ssh && \\
  cp {} /root/.ssh/nitor-audit && \\
  chown -R root:root /root/.ssh/ && \\
  gpg --receive-keys {}  && \\
  cp {} /etc/cron.d/nitor-audit
"""
@contextlib.contextmanager
def stdchannel_redirected(stdchannel, dest_filename):
    """
    A context manager to temporarily redirect stdout or stderr
    e.g.:
    with stdchannel_redirected(sys.stderr, os.devnull):
        if compiler.has_function('clock_gettime', libraries=['rt']):
            libraries.append('rt')
    """

    try:
        oldstdchannel = os.dup(stdchannel.fileno())
        dest_file = open(dest_filename, 'w')
        os.dup2(dest_file.fileno(), stdchannel.fileno())
        yield
    finally:
        if oldstdchannel is not None:
            os.dup2(oldstdchannel, stdchannel.fileno())
        if dest_file is not None:
            dest_file.close()

def _to_str(data):
    ret = data
    decode_method = getattr(data, "decode", None)
    if callable(decode_method):
        try:
            ret = data.decode()
        except:
            ret = _to_str(base64.b64encode(data))
    return str(ret)


def _to_bytes(data):
    ret = data
    encode_method = getattr(data, "encode", None)
    if callable(encode_method):
        ret = data.encode("utf-8")
    return bytes(ret)


def _get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("",0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port

def init():
    parser = argparse.ArgumentParser(description="Initialize nitor audit")
    parser.add_argument("usercreate", help="The rest endpoint that creates the user")
    parser.add_argument("-k", "--key", help="Use an existing key to authenticate to audit upload sftp server. Needs to be accompanied by a [keyname].pub public key in the same directory, or one will be generated.")
    args = parser.parse_args()
    key_file = None
    pubkey_file = None
    unlink_key = False
    if args.key:
        pubkey_file = args.key + ".pub"
        try:
            with open(pubkey_file, "r") as pubkey:
                pubkey_data = pubkey.readline()
        except:
            proc = Popen(["ssh-keygen", "-y", "-f", args.key], stdout=PIPE)
            pubkey_data, _ = proc.communicate()
            if proc.returncode == 0:
                with open(pubkey_file, "w") as pubkey:
                    pubkey.write(_to_str(pubkey_data))
    else:
        unlink_key = True
        fh, key_file = mkstemp()
        pubkey_file = key_file + ".pub"
        proc = Popen(["ssh-keygen", "-f", key_file, "-b", "4096", "-q", "-N", ""], stdout=PIPE, stdin=PIPE)
        _, _ = proc.communicate(input=b'y')
        if proc.returncode == 0:
            with open(pubkey_file, "r") as pubkey:
                pubkey_data = pubkey.readline()
    
    if not (key_file and pubkey_file and pubkey_data):
        print("Failed to get a valid key")
        exit(1)

    user, ssh_server, gpg_key = account(args.usercreate, pubkey_data)
    fh, crontab_file = mkstemp()
    with open(crontab_file, "w") as crontab:
        crontab.write(CRONTAB.format(user, ssh_server, gpg_key))
    proc = Popen(["sudo", "sh", "-c", SUDO_EXEC.format(key_file, gpg_key, crontab_file)])
    _, _ = proc.communicate()
    if unlink_key:
        os.unlink(key_file)
        os.unlink(pubkey_file)
    os.unlink(crontab_file)
    
def account(create_endpoint, pubkey):
    global SERVER
    port = _get_open_port()
    Handler = KeyResponseHandler
    SERVER = socketserver.TCPServer(("127.0.0.1", port), Handler)
    url = create_endpoint + "?key=" + quote(pubkey) + "&port=" + str(port)

    webbrowser.open(url, new=2, autoraise=False)
    try:
        SERVER.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        SERVER.shutdown()
    if CREATE_USER_DATA:
        return CREATE_USER_DATA
    else:
        return None

user_create_response = """
<html>
  <head><title>Account created</title></head>
  <body>
  <p>Account created, you may close this window.</p>
  <script>
    window.close();
  </script>
  </body>
</html>"""

class KeyResponseHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            try:
                self.wfile.write(f.encode())
            finally:
                self.wfile.flush()
            global SERVER
            def stop_server(server):
                server.shutdown()
            _thread.start_new_thread(stop_server, (SERVER,))

    def do_HEAD(self):
        """Serve a HEAD request."""
        self.send_head()

    def send_head(self):
        self._set_headers()
        global CREATE_USER_DATA
        CREATE_USER_DATA = self.path.split("/")[1:]
        return user_create_response

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    init()