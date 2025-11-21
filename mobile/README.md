# Daily Trainer Mobile (KivyMD)

Primeiro esqueleto mobile usando KivyMD consumindo a API **v2** já existente. Ajuste a URL da API em `mobile/api.py` (via variável de ambiente `DAILY_TRAINER_API_URL`, padrão `http://localhost:8000`).

## Requisitos
- Python 3.10+
- Kivy >= 2.3.0
- KivyMD >= 1.1.1
- requests

Instalação:
```bash
cd mobile
pip install -r requirements.txt
```

## Executar
```bash
cd mobile
python main.py
```

## O que tem pronto
- Abas para Alunos, Treinos e Exercícios.
- Botão de atualizar em cada aba.
- Consumo direto da API v2 (`/api/v2/alunos`, `/api/v2/treinos`, `/api/v2/exercicios`).
- Layout simples para listar nomes e dados principais.

Próximos passos sugeridos:
- Adicionar criação/edição via formulários.
- Armazenar token/headers se você ativar autenticação na API.
- Melhorar estados de loading/erro e paginação, se necessário.
