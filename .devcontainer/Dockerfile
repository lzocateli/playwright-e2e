FROM lzocateli/devops:3.12-bookworm

ENV HTTP_PROXY=
ENV HTTPS_PROXY=
ENV NO_PROXY=

RUN apt update -y && apt upgrade -y

ARG TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ >/etc/timezone

RUN wget -q https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb && \
  dpkg -i packages-microsoft-prod.deb && \
  rm packages-microsoft-prod.deb && \
  apt-get update && \
  apt-get install -y powershell

