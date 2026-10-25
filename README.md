# Pokédex Kanto

Aplicativo desktop em Python para explorar os 151 Pokémon da primeira geração.
Não usa navegador. Informações e imagens consultadas na PokéAPI ficam salvas no
computador para os próximos acessos.

## Recursos

- Lista completa de Kanto disponível imediatamente
- Busca por nome ou número
- Favoritos persistentes
- Tipos, altura, peso, habilidades e atributos base
- Imagens oficiais
- Cache local em `%LOCALAPPDATA%\PokedexKanto`
- Tema escuro e interface nativa com PySide6

## Executar no VS Code

1. Instale o Python 3.11 ou mais recente e marque **Add Python to PATH**.
2. Abra esta pasta no VS Code.
3. No terminal PowerShell, execute:

   ```powershell
   .\run.ps1
   ```

Na primeira consulta de cada Pokémon é necessária conexão com a internet. Depois,
os dados consultados funcionam a partir do cache local.

## Gerar o executável

Execute no terminal:

```powershell
.\build-exe.ps1
```

O arquivo será criado em `dist\Pokedex-Kanto.exe`.

## Organização

- `main.py`: ponto de entrada
- `src/pokedex_app/app.py`: interface
- `src/pokedex_app/api.py`: PokéAPI e cache
- `src/pokedex_app/data.py`: índice local dos 151 Pokémon
- `src/pokedex_app/storage.py`: favoritos e pastas locais
- `src/pokedex_app/theme.py`: cores e tema
- `assets/`: ícones vetoriais próprios

## Personalização rápida

As cores ficam em `src/pokedex_app/theme.py`. O layout principal está no método
`MainWindow._build_ui`, dentro de `src/pokedex_app/app.py`.

