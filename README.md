
# Screeps Client For Private Server

---

## 1 screeps_client.py

Console client with ASCII map and log tracking etc.

Based on [private_server_backend](https://github.com/screeps/backend-local/tree/master/lib/game)
and [Websocket endpoints](https://github.com/screepers/node-screeps-api/blob/master/docs/Websocket_endpoints.md).

_I have not figured out how to authenticate with official server.
Connect to official server is impossible._

---

### 1.1 requirement

##### server side

[screepsmod-auth](https://github.com/ScreepsMods/screepsmod-auth)
is necessary for authentication

    npm install screepsmod-auth

##### client side

    pip install -r requirement.txt

---

### 1.2 config

Rename **config.example.py** to **config.py**.

Fill up **config.py** with your private server information. 

_DB\_ setting is not used, just leave it blank._

---

### 1.3 usage

    python screeps_client.py

Ctrl+1: Map

Ctrl+2: Console

##### TODO

Ctrl+3: Memory

---

#### 1.3.1 Map

HJKLYUBN: move around in room

Shift+HJKLYUBN: move faster

Ctrl+HJKLYUBN: change room

Tab: switch between objects on the same tile

Enter: open an operation menu, for creating construction site, etc (TODO)

Map character could be changed in config.py.

---

#### 1.3.2 Console

PageUp PageDown: scroll console log

↑↓: scroll command history

Enter: send command

Shift+Insert: Paste

---

## 2 screeps_console.py

A standalone console, for tracking log only.

---

## 3 screeps_auto_push.py

Detect local script changes and update to server automatically. 

