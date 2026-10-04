# Runbook: Nginx

Nginx is the load balancer and reverse proxy for every Andes Cloud
service. This guide covers the base configuration and the problems
the infrastructure team handles most often.

## Configuration location

The files live in `/etc/nginx/`. Each service has its own file inside
`conf.d/`. Never edit `nginx.conf` directly: global changes are made
in the `infra-config` repository and deployed with Ansible.

## Validate and reload

Before applying any change, validate the syntax with `nginx -t`. If
validation passes, reload without dropping active connections using
`systemctl reload nginx`. Avoid `restart` unless Nginx is unresponsive.

## Logs

Access requests are recorded in `/var/log/nginx/access.log` and errors
in `/var/log/nginx/error.log`. To see only upstream errors, filter
the error log by the word `upstream`.

## Upload size limits

The maximum request size is controlled by `client_max_body_size`.
The default is 10 MB. For the documents service it is raised to 50 MB.
If a user reports that a file upload is rejected with a 413, check
this parameter before touching the application.

## Compression and cache

We enable gzip for `text/*`, `application/json` and `application/javascript`.
Static files are served with `expires 7d`. Cache changes must be
coordinated with the frontend team so assets are not invalidated at
peak hours.

## Slow site that ends in a 504 error

If the website loads slowly, the user waits a long time and then
gets an error screen, the server was too slow to respond.
```nginx
proxy_read_timeout 120s;  # 504 if exceeded
```

Raising the value is only a patch: first review the slow query in
the application and only then adjust the proxy limit.

## Certificates

TLS certificates renew automatically. See the TLS certificates
runbook for the manual emergency procedure.

## Contact

For reviews of Nginx configuration changes, ask the infrastructure
team in the `#infra-config` channel and attach the diff of your
`conf.d` file.
