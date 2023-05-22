import socket
import signal
import sys
import random

# Read a command line argument for the port where the server
# must run.
port = 8080
if len(sys.argv) > 1:
    port = int(sys.argv[1])
else:
    print("Using default port 8080")
    print("Server started on port", port)
    print("Listening for incoming connections...")

# Start a listening server socket on the port
sock = socket.socket()
sock.bind(('', port))
sock.listen(2)

### Contents of pages we will serve.
# Read login credentials for all the users
passwords = {}
with open('passwords.txt', 'r') as f:
    for line in f:
        user, passwd = line.strip().split()
        passwords[user] = passwd

# Read secret data of all the users
secrets = {}
with open('secrets.txt', 'r') as f:
    for line in f:
        user, secret = line.strip().split()
        secrets[user] = secret

# Login form
login_form = """
   <form action = "http://localhost:%d" method = "post">
   Name: <input type = "text" name = "username">  <br/>
   Password: <input type = "password" name = "password" /> <br/>
   <input type = "submit" value = "Submit" />
   </form>
""" % port
# Default: Login page.
login_page = "<h1>Please login</h1>" + login_form
# Error page for bad credentials
bad_creds_page = "<h1>Bad user/pass! Try again</h1>" + login_form
# Successful logout
logout_page = "<h1>Logged out successfully</h1>" + login_form
# A part of the page that will be displayed after successful
# login or the presentation of a valid cookie
success_page = """
   <h1>Welcome, %s!</h1>
   <form action="http://localhost:%d" method = "post">
   <input type = "hidden" name = "password" value = "new" />
   <input type = "submit" value = "Click here to Change Password" />
   </form>
   <form action="http://localhost:%d" method = "post">
   <input type = "hidden" name = "action" value = "logout" />
   <input type = "submit" value = "Click here to logout" />
   </form>
   <br/><br/>
   <h1>Your secret data is here:</h1>
   <p>%s</p>
"""

new_password_page = """
   <form action="http://localhost:%d" method = "post">
   New Password: <input type = "text" name = "NewPassword" /> <br/>
   <input type = "submit" value = "Submit" />
</form>
""" % port


#### Helper functions
# Printing.
def print_value(tag, value):
    print
    "Here is the", tag
    print
    "\"\"\""
    print
    value
    print
    "\"\"\""
    print


# Signal handler for graceful exit
def sigint_handler(sig, frame):
    print('Finishing up by closing listening socket...')
    sock.close()
    sys.exit(0)


# Register the signal handler
signal.signal(signal.SIGINT, sigint_handler)

# TODO: put your application logic here!
username = ''
password = ''
new_pass = ''
cookie_dict = {}

# Infinite loop to accept incoming HTTP connections and respond
while True:
    client, addr = sock.accept()
    req = client.recv(1024)
    headers_to_send = ""

    # split the headers and body
    header_body = req.split('\r\n\r\n')
    headers = header_body[0]
    body = '' if len(header_body) == 1 else header_body[1]

    print("headers:", headers)
    print("entity body:", body)

    # parse headers and body
    if headers:
        method = headers.split()[0]
    else:
        method = ''

    if method == "POST":
        # username and password parse
        try:
            data = body.decode("utf-8")
            username_field = data.split('&')[0]

            if (username_field != "password=new") & ("NewPassword" not in username_field):

                password_field = data.split('&')[1]
                username = username_field.split('=')[1]
                password = password_field.split('=')[1]

            elif "NewPassword" in username_field:
                new_pass = username_field.split('=')[1]

        except:
            # if fail return bad credentials page
            html_content_to_send = bad_creds_page
            headers_to_send = ''

        if "action=logout" in body:
            # clear cookies
            headers_to_send = 'Set-Cookie: token=; expires=Thu, 01 Jan 1970 00:00:00 GMT\r\n'
            html_content_to_send = logout_page
        else:
            # check if the username and password are valid
            if username_field == "password=new":
                html_content_to_send = new_password_page

            elif "NewPassword" in username_field:
                html_content_to_send = success_page % (username, port, port, secrets[username])
                headers_to_send = ''
                with open('passwords.txt', 'r') as f:
                    lines = f.readlines()
                    for ind, line in enumerate(lines):
                        user, passwd = line.strip().split()
                        if user == username:
                            lines[ind] = user + " " + new_pass + "\n"
                            passwords[user] = user + " " + new_pass + "\n"

                with open('passwords.txt', 'w') as f:
                    f.writelines(lines)

                with open('passwords.txt', 'r') as f:
                    for line in f:
                        user, passwd = line.strip().split()
                        passwords[user] = passwd

                rand_val = random.getrandbits(64)
                headers_to_send = 'Set-Cookie: token=' + str(rand_val) + '\r\n'

            elif username in passwords and passwords[username] == password:
                html_content_to_send = success_page % (username, port, port, secrets[username])
                rand_val = random.getrandbits(64)
                headers_to_send = 'Set-Cookie: token=' + str(rand_val) + '\r\n'

            else:
                html_content_to_send = bad_creds_page
                headers_to_send = ''
    else:
        # check if cookie is valid
        if 'Cookie' in headers:
            cookie_header = headers.split('Cookie: ')[1].split('\r\n')[0]
            cookie_parts = cookie_header.split('; ')
            for part in cookie_parts:
                if 'token=' in part:
                    cookie_value = part.split('token=')[1]
                    if cookie_value in cookie_dict.values():
                        # get corresponding username
                        username = [k for k, v in cookie_dict.items() if v == cookie_value][0]
                        html_content_to_send = success_page % (username, port, port, secrets[username])
                        headers_to_send = 'Set-Cookie: token=' + cookie_value + '\r\n'
                        break
                    else:
                        # invalid cookie
                        html_content_to_send = bad_creds_page
                        headers_to_send = ''
                    # update cookie dict
                    if username in passwords and cookie_value not in cookie_dict.values():
                        cookie_dict[username] = cookie_value
        else:
            # no valid cookie
            # find username and password with parse
            try:
                data = body.decode("utf-8")
                username_field = data.split('&')[0]
                password_field = data.split('&')[1]
                username = username_field.split('=')[1]
                password = password_field.split('=')[1]
            except:
                # return login page
                html_content_to_send = login_page
                headers_to_send = ''
            else:
                # check if the username and password are valid
                if username in passwords and passwords[username] == password:
                    html_content_to_send = success_page % (username, port, port, secrets[username])
                    rand_val = random.getrandbits(64)
                    headers_to_send = 'Set-Cookie: token=' + str(rand_val) + '\r\n'
                    cookie_dict[username] = str(rand_val)
                else:
                    html_content_to_send = bad_creds_page
                    headers_to_send = ''

    response = 'HTTP/1.1 200 OK\r\n'
    response += headers_to_send
    response += 'Content-Type: text/html\r\n\r\n'
    response += html_content_to_send

    print("response:", response)

    client.send(response.encode("utf-8"))
    client.close()

    print("Served one request/connection!")
    print()
