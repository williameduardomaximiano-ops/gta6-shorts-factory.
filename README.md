# GTA6 Shorts Factory — modo econômico

Protótipo de processamento local, sem chamadas a APIs de IA pagas. Não precisa de chave OpenAI. O modelo Whisper é baixado uma vez e executado em CPU. O custo de servidor, armazenamento e tráfego é separado.

## Executar
Instale Python 3.10+, FFmpeg e FFprobe (com libass e libx264). Crie um ambiente virtual e instale:
```sh
python -m pip install -r requirements.txt
python factory.py cut video.mp4 --authorized --output runs/teste --language pt
python factory.py review --output runs/teste --clip clip_01 --decision approved
```
Use exclusivamente gravações próprias ou autorizadas, em conformidade com os termos da plataforma. Cada execução cria até três cortes de 30 segundos em 1080x1920 com legendas e um manifesto review.json. A seleção usa heurísticas de fala, não interpretação visual; pode não encontrar os melhores momentos. Revise o vídeo antes de aprovar. Nenhum vídeo é publicado automaticamente.

Limites iniciais: CPU, modelo base, até 15 minutos por entrada (configurável até 30 minutos), até cinco cortes. Vídeos maiores devem ser divididos em blocos. Não use este CLI como serviço web público. O manifesto local não substitui autenticação e aprovação em um servidor multiusuário.

## Próximas etapas
- Ingestão de lives autorizadas via fonte de mídia permitida, com processamento em blocos e fila persistente.
- Hospedagem de worker CPU com orçamento explicitamente limitado; não contratar plano pago sem autorização.
- Painel de revisão autenticado, armazenamento privado e limpeza automática.
- YouTube e TikTok: OAuth oficial, revisão das permissões, testes de upload privado quando suportado, aprovação manual obrigatória antes de cada publicação e prevenção de duplicidade.
- Títulos e descrições por regras locais ou modelo aberto opcional, sem fallback pago.
- Analytics pelas APIs oficiais e revisão dos resultados.

Nunca comitar credenciais OAuth, tokens, vídeos ou dados privados neste repositório público. A configuração de YouTube mencionada pelo proprietário ainda precisa ser validada; TikTok e deploy ainda não integrados.
