FROM ghcr.io/flaresolverr/flaresolverr:v3.5.2@sha256:c80ae007ce2ccdcd217a12426e4f039ef763ff90738c808d38810c3e59323767

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends iptables util-linux \
    && groupadd --gid 20000 flarecontrol \
    && usermod --append --groups flarecontrol flaresolverr \
    && rm -rf /var/lib/apt/lists/*

COPY flare-protected/patch_upstream.py /tmp/patch_upstream.py
RUN python /tmp/patch_upstream.py && rm /tmp/patch_upstream.py
COPY flare-protected/entrypoint.sh /usr/local/bin/protected-flare-entrypoint
RUN chmod 0755 /usr/local/bin/protected-flare-entrypoint

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/usr/local/bin/protected-flare-entrypoint"]
CMD ["/usr/local/bin/python", "-u", "/app/flaresolverr.py"]
