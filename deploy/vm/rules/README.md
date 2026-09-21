# Caddy Modular Environment Rules (`deploy/vm/rules/`)

Este diretório permite estender a configuração do proxy reverso Caddy com regras específicas de cada ambiente **sem modificar o arquivo `Caddyfile` versionado no Git**.

## Como Funciona

1. O `Caddyfile` principal possui a diretiva:
   ```caddy
   import /etc/caddy/rules/*.caddy
   ```
2. O Docker Compose monta este diretório em `/etc/caddy/rules:ro`.
3. Todos os arquivos com extensão `.caddy` criados aqui são carregados automaticamente pelo Caddy.
4. **Isolamento no Git:** O `.gitignore` ignora todos os arquivos `*.caddy` criados aqui (exceto `.example`). Isso garante que a árvore de trabalho (`git status`) permaneça 100% limpa, permitindo que `git pull origin main` seja executado na VM sem conflitos ou necessidade de `git stash`.

## Exemplos de Uso

### 1. Ativar Autenticação Básica (Staging / Acesso Restrito)
```bash
cp auth.caddy.example auth.caddy
docker exec substrate_vm_caddy caddy reload --config /etc/caddy/Caddyfile
```

### 2. Whitelist de IPs de Origem (Exemplo em `ip_filter.caddy`)
```caddy
@blocked not remote_ip 200.100.50.0/24 10.0.0.0/8
abort @blocked
```

### 3. Cabeçalhos de Segurança Customizados (Exemplo em `headers.caddy`)
```caddy
header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options "nosniff"
}
```

Para aplicar qualquer alteração em tempo de execução sem reiniciar containeres:
```bash
docker exec substrate_vm_caddy caddy reload --config /etc/caddy/Caddyfile
```
