# YK Pao School Utilities WSGI Site Deployment

My standard setup uses the [gunicorn](https://gunicorn.org) WSGI server under a [NGINX](https://nginx.org) reverse proxy.

I'd typically use the `gevent` worker as I need to handle a lot of concurrent requests.

`/etc/systemd/system/ykps-watcher.path`
```ini
[Path]
PathModified=/srv/git/ykps/current/ykps-wsgi.git/index.lock

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/ykps-watcher.service`
```ini
[Unit]
Description=ykps restarter
After=network.target

[Service]
Type=oneshot
User=root
Group=root
ExecStart=/usr/bin/systemctl reload ykps.service

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/ykps.service`
```ini
[Unit]
Description=ykps daemon
Requires=ykps.socket
After=network.target

[Service]
Type=notify
User=ykps
Group=nogroup
RuntimeDirectory=ykps
WorkingDirectory=/srv/ykps/ykps
ExecStart=/usr/bin/gunicorn --workers 2 -k gevent ykps:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/ykps.socket`
```ini
[Unit]
Description=ykps socket

[Socket]
ListenStream=/run/ykps.sock
SocketUser=www-data
SocketMode=600

[Install]
WantedBy=sockets.target
```

`/etc/nginx/sites-available/ykps`
```ini
server {
    server_name ykps.runxiyu.org;
    server_name sj.ykps.net;
    location / {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $http_host;
            proxy_pass http://unix:/run/ykps.sock;
    }
    location /static/ {
            root /srv/ykps/ykps;
            try_files $uri $uri/ =404;
    }
    listen [::]:80;
    listen 80;
}
```

The following `post-receive` hook may also be useful:
```sh
#!/bin/sh
DSTDIR="/srv/ykps/ykps"
sudo -u ykps git --work-tree=${DSTDIR} clean -fd
sudo -u ykps git --work-tree=${DSTDIR} checkout --force
```

Remember to configure users, groups, and sudoers.

You also need to configure it with Azure secret keys and create relevant directories for submissions and files.

Also remember to set the nginx max request size or something.
