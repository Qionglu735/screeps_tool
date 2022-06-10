

### stat.py systemd config

   [Unit]
   Description=My script
   Before=
   After=screeps-world.service
   
   [Service]
   ExecStart=/usr/bin/python3 /home/pi/Desktop/myscript.py
   Requires=dhangioserver.service
   
   [Install]
   WantedBy=multi-user.target



### No module named MySQLdb

mysql-python can't install on Windows

1. Download from [Unofficial Packages Source](https://www.lfd.uci.edu/~gohlke/pythonlibs/#_mysql-python)
2. pip install whl file

   pip install ./MySQL_python-1.2.5-cp27-none-win_amd64.whl



### About Win .lnk File

1. Create shortcut form .bat
2. Property -> Font
   1. Size: 10
   2. Font: Consolas
3. Property -> Window size
   1. Width: 80
   2. Height: 25
4. Property -> Color
   1. Transparency: 30%

