# Site de Apresentação Profissional - Eduardo Stalisz

## 🚀 Sobre o Projeto

Site pessoal desenvolvido para apresentar a trajetória profissional em TI Infrastructure e Cybersecurity. O site conta a história desde jovem aprendiz até especialista atual, destacando projetos e competências técnicas.

## 🛠️ Tecnologias Utilizadas

- **HTML5** - Estrutura semântica e acessível
- **CSS3** - Design responsivo com Flexbox e Grid
- **JavaScript ES6+** - Interatividade e animações
- **Font Awesome** - Ícones profissionais
- **Google Fonts** - Tipografia moderna (Inter)

## 📁 Estrutura do Projeto

```
SiteLita/
├── index.html          # Página principal
├── styles.css          # Estilos e responsividade
├── script.js           # Funcionalidades JavaScript
├── assets/             # Recursos (imagens, documentos)
│   └── .gitkeep
├── README.md           # Documentação
└── TODO.md            # Lista de tarefas
```

## 🎨 Funcionalidades

### ✅ Implementadas
- **Design Responsivo** - Adaptável a todos os dispositivos
- **Navegação Suave** - Scroll animado entre seções
- **Timeline Interativa** - Histórico profissional animado
- **Formulário de Contato** - Com validação e notificações
- **Animações CSS** - Efeitos visuais profissionais
- **Menu Mobile** - Navegação otimizada para celular
- **Efeito Typing** - Animação de digitação no subtítulo
- **Scroll Animations** - Elementos aparecem ao rolar a página
- **Easter Egg** - Código Konami para desenvolvedores

### 🔧 Seções do Site
1. **Hero Section** - Apresentação principal com call-to-action
2. **Sobre Mim** - História pessoal e jornada na TI
3. **Experiência** - Timeline profissional detalhada
4. **Competências** - Skills organizadas por categoria
5. **Projetos** - Principais realizações e implementações
6. **Contato** - Formulário e links profissionais

## 🌐 Deploy na Oracle Cloud Infrastructure (OCI)

### Pré-requisitos
- Conta na Oracle Cloud (Free Tier disponível)
- OCI CLI instalado (opcional)
- Conhecimento básico de Object Storage

### Método 1: Object Storage + CDN (Recomendado)

#### 1. Criar Bucket no Object Storage
```bash
# Via OCI CLI
oci os bucket create \
    --compartment-id <seu-compartment-id> \
    --name site-eduardo-stalisz \
    --public-access-type ObjectRead
```

#### 2. Upload dos Arquivos
```bash
# Upload via CLI
oci os object put \
    --bucket-name site-eduardo-stalisz \
    --file index.html \
    --name index.html \
    --content-type text/html

oci os object put \
    --bucket-name site-eduardo-stalisz \
    --file styles.css \
    --name styles.css \
    --content-type text/css

oci os object put \
    --bucket-name site-eduardo-stalisz \
    --file script.js \
    --name script.js \
    --content-type application/javascript
```

#### 3. Configurar Website Estático
- Acesse o Console OCI
- Vá para Object Storage > Buckets
- Selecione seu bucket
- Em "Edit Visibility", marque "Public"
- Configure Index Document: `index.html`
- Configure Error Document: `index.html`

#### 4. URL de Acesso
Seu site estará disponível em:
```
https://objectstorage.<region>.oraclecloud.com/n/<namespace>/b/site-eduardo-stalisz/o/index.html
```

### Método 2: Compute Instance + Nginx

#### 1. Criar Compute Instance
```bash
# Criar instância Always Free
oci compute instance launch \
    --availability-domain <AD> \
    --compartment-id <compartment-id> \
    --image-id <ubuntu-image-id> \
    --shape VM.Standard.E2.1.Micro \
    --subnet-id <subnet-id> \
    --display-name "site-eduardo-server"
```

#### 2. Configurar Nginx
```bash
# Conectar via SSH
ssh -i <private-key> ubuntu@<public-ip>

# Instalar Nginx
sudo apt update
sudo apt install nginx -y

# Copiar arquivos do site
sudo cp index.html /var/www/html/
sudo cp styles.css /var/www/html/
sudo cp script.js /var/www/html/
sudo cp -r assets /var/www/html/

# Configurar permissões
sudo chown -R www-data:www-data /var/www/html/
sudo chmod -R 755 /var/www/html/

# Iniciar Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### 3. Configurar Security List
- Liberar porta 80 (HTTP) e 443 (HTTPS)
- Configurar regras de ingress no Security List

### Método 3: Container Instance (Serverless)

#### 1. Criar Dockerfile
```dockerfile
FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### 2. Build e Push para OCIR
```bash
# Build da imagem
docker build -t site-eduardo .

# Tag para OCIR
docker tag site-eduardo <region>.ocir.io/<namespace>/site-eduardo:latest

# Push para registry
docker push <region>.ocir.io/<namespace>/site-eduardo:latest
```

#### 3. Criar Container Instance
```bash
oci container-instances container-instance create \
    --compartment-id <compartment-id> \
    --availability-domain <AD> \
    --shape CI.Standard.E4.Flex \
    --containers '[{
        "displayName": "site-eduardo",
        "imageUrl": "<region>.ocir.io/<namespace>/site-eduardo:latest"
    }]'
```

## 🔧 Personalização

### Adicionar Sua Foto
1. Coloque sua foto na pasta `assets/`
2. Atualize o HTML na seção hero:
```html
<div class="hero-image">
    <img src="assets/sua-foto.jpg" alt="Eduardo Stalisz" class="profile-image">
</div>
```

### Modificar Cores
Edite as variáveis CSS no início do `styles.css`:
```css
:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
    --accent-color: #f093fb;
}
```

### Adicionar Novas Seções
1. Adicione o HTML na `index.html`
2. Crie os estilos correspondentes no `styles.css`
3. Atualize a navegação no JavaScript

## 📱 Responsividade

O site é totalmente responsivo e otimizado para:
- **Desktop** (1200px+)
- **Tablet** (768px - 1199px)
- **Mobile** (até 767px)

## 🔍 SEO e Performance

### Otimizações Implementadas
- Meta tags apropriadas
- Estrutura HTML semântica
- Lazy loading para imagens
- Compressão de assets
- Cache headers configuráveis

### Lighthouse Score Esperado
- **Performance**: 95+
- **Accessibility**: 100
- **Best Practices**: 100
- **SEO**: 100

## 🚀 Melhorias Futuras

### Funcionalidades Planejadas
- [ ] Blog integrado
- [ ] Sistema de comentários
- [ ] Analytics integrado
- [ ] PWA (Progressive Web App)
- [ ] Modo escuro/claro
- [ ] Múltiplos idiomas
- [ ] Integração com APIs sociais

### Otimizações Técnicas
- [ ] Service Worker para cache
- [ ] Compressão de imagens automática
- [ ] CDN para assets estáticos
- [ ] Minificação automática

## 📞 Suporte

Para dúvidas ou sugestões sobre o site:

- **LinkedIn**: [Eduardo Stalisz](https://www.linkedin.com/in/eduardo-stalisz-8b3065192/)
- **Email**: contato@eduardostalisz.com

## 📄 Licença

Este projeto é de uso pessoal. Sinta-se livre para usar como inspiração para seu próprio site profissional.

---

**Desenvolvido com ❤️ por Eduardo Stalisz**  
*TI Infrastructure & Cybersecurity Specialist*
