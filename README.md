# Site pessoal - Eduardo Stalisz

Site pessoal estático para apresentação profissional de Eduardo Stalisz, com foco em infraestrutura de TI, cloud, automação e cybersecurity.

O projeto agora está preparado para rodar em container com Nginx, facilitando o deploy em uma VM, Container Instance, Kubernetes ou qualquer ambiente compatível com Docker.

## Tecnologias

- HTML5
- CSS3
- JavaScript
- Nginx
- Docker e Docker Compose
- Font Awesome e Google Fonts via CDN

## Estrutura do projeto

```text
.
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── index.html
├── styles.css
├── script.js
├── static/
│   └── img/
│       ├── OCI25FNDCFAV1.png
│       └── OCIF2023CA.png
├── README.md
└── TODO.md
```

## Como rodar com Docker

Pré-requisito:

- Docker instalado

Build da imagem:

```bash
docker build -t site-staliszeduardo:1.0 .
```

Executar o container:

```bash
docker network create site-staliszeduardo-net
docker run --rm \
  --name site-staliszeduardo \
  --network site-staliszeduardo-net \
  --cpus 0.50 \
  --memory 128m \
  --memory-reservation 32m \
  -p 0.0.0.0:8080:80 \
  site-staliszeduardo:1.0
```

Acesse:

```text
http://localhost:8080
```

## Como rodar com Docker Compose

Pré-requisito:

- Docker Compose v2

Subir o site:

```bash
docker compose up -d --build
```

O Compose cria uma rede Docker dedicada chamada `site-staliszeduardo-net` e publica o site no host pela porta `8080`.

Ver logs:

```bash
docker compose logs -f
```

Parar o site:

```bash
docker compose down
```

Acesse:

```text
http://localhost:8080
```

## Configuração do Nginx

O arquivo `nginx.conf` faz o Nginx servir os arquivos estáticos em `/usr/share/nginx/html`.

Regras principais:

- `index.html` com `Cache-Control: no-cache`
- arquivos estáticos como CSS, JS e imagens com cache longo
- endpoint `/health` para health check do Load Balancer
- fallback para `index.html` em rotas não encontradas
- gzip habilitado para arquivos de texto

## Deploy em servidor com Docker

Em um servidor Linux com Docker e Docker Compose instalados, use o Compose:

```bash
docker compose up -d --build
docker compose ps
```

O container roda com limites leves para uma VM pequena:

- ate `0.50` vCPU
- ate `128 MB` de memoria
- reserva de `32 MB` de memoria
- rede Docker dedicada `site-staliszeduardo-net`
- porta publicada no host: `8080`

Se a imagem estiver em um registry, substitua `site-staliszeduardo:1.0` pela URL completa da imagem no `docker-compose.yml`.

## OCI Compute + Load Balancer

Topologia recomendada:

```text
Internet -> OCI Load Balancer :80/:443 -> VM Compute :8080 -> Container Nginx :80
```

No Backend Set do Load Balancer:

- protocolo: `HTTP`
- backend: IP privado da VM
- porta: `8080`
- health check: `HTTP GET /health` na porta `8080`

Na Security List ou NSG da VM:

- liberar entrada TCP `8080`
- origem: subnet ou NSG do Load Balancer
- evitar liberar `8080` para `0.0.0.0/0`, a menos que seja temporario para teste

Se houver firewall no sistema operacional, libere a porta apenas para a origem do Load Balancer. Exemplo com UFW:

```bash
sudo ufw allow from <cidr-do-load-balancer> to any port 8080 proto tcp
```

Para validar na VM:

```bash
curl -I http://127.0.0.1:8080
curl -I http://127.0.0.1:8080/health
```

## Diagnóstico de erro 400 no Load Balancer

Se aparecer `HTTP Status 400 - Bad Request`, verifique primeiro o protocolo usado pelo Load Balancer.

Configuração esperada:

- Listener público: `HTTP :80` ou `HTTPS :443`
- Backend Set: `HTTP`
- Backend: IP privado da VM na porta `8080`
- Health check: `HTTP GET /health`
- Proxy Protocol: desabilitado

O container escuta HTTP puro. Portanto, o Load Balancer pode receber HTTPS na internet, mas a conexão entre Load Balancer e VM deve continuar como `HTTP :8080`.

Comandos úteis na VM:

```bash
docker compose ps
docker logs site-staliszeduardo --tail 50
curl -v http://127.0.0.1:8080/
curl -v http://127.0.0.1:8080/health
```

Resultado esperado:

- `curl http://127.0.0.1:8080/` retorna `200 OK`
- header `Server` deve indicar `nginx`
- `/health` retorna `ok`

Se `curl` local funcionar e o Load Balancer ainda retornar 400, o problema provavelmente está na configuração do listener/backend do Load Balancer, principalmente backend em `HTTPS` ou Proxy Protocol habilitado.

## Publicação no OCIR

Exemplo de fluxo para Oracle Cloud Infrastructure Registry:

```bash
docker build -t site-staliszeduardo:1.0 .
docker tag site-staliszeduardo:1.0 <region>.ocir.io/<namespace>/site-staliszeduardo:1.0
docker login <region>.ocir.io
docker push <region>.ocir.io/<namespace>/site-staliszeduardo:1.0
```

Depois disso, a imagem pode ser usada em:

- OCI Compute Instance com Docker
- OCI Container Instance
- Kubernetes/OKE
- outro provedor ou servidor próprio com Docker

## Atualização do site

Depois de alterar HTML, CSS, JavaScript ou imagens:

```bash
docker compose up -d --build
```

Ou, usando Docker puro:

```bash
docker build -t site-staliszeduardo:1.0 .
docker stop site-staliszeduardo
docker rm site-staliszeduardo
docker run -d --name site-staliszeduardo --restart unless-stopped -p 0.0.0.0:8080:80 site-staliszeduardo:1.0
```

## Personalização

Para adicionar novas imagens, salve os arquivos em:

```text
static/img/
```

E referencie no HTML:

```html
<img src="static/img/nome-do-arquivo.png" alt="Descrição da imagem">
```

Para alterar cores, fontes e responsividade, edite:

```text
styles.css
```

Para alterar interações, animações e carrossel, edite:

```text
script.js
```

## Licença

Projeto de uso pessoal.
