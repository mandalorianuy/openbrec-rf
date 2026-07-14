# Publicar en GitHub

El repositorio ya está inicializado en la rama `main` y no contiene remoto ni credenciales.

## Opción GitHub CLI

```bash
gh auth login
gh repo create openbrec-rf --public --source=. --remote=origin --push
```

## Opción manual

1. Crear un repositorio vacío llamado `openbrec-rf`.
2. No generar README/licencia en GitHub, porque ya existen.
3. Ejecutar:

```bash
git remote add origin git@github.com:TU_USUARIO/openbrec-rf.git
git push -u origin main
```

Antes de hacerlo público, revisar información operacional, marcas, compras y política de disclosure.
