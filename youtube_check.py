"""Read-only YouTube OAuth smoke test. No uploads and no saved tokens."""
import argparse
import json
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

def check_client(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    client = config.get("installed", {})
    if not all(client.get(k) for k in ("client_id", "client_secret", "auth_uri", "token_uri")):
        raise ValueError("Esperado cliente OAuth do tipo aplicativo para computador.")
    if client["auth_uri"] != "https://accounts.google.com/o/oauth2/auth" and client["auth_uri"] != "https://accounts.google.com/o/oauth2/v2/auth":
        raise ValueError("Endpoint de autorização inesperado.")
    if client["token_uri"] != "https://oauth2.googleapis.com/token":
        raise ValueError("Endpoint de token inesperado.")
    return config

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--client", required=True)
    p.add_argument("--check-config", action="store_true", help="Valida somente o arquivo, sem rede.")
    args = p.parse_args()
    try:
        config = check_client(args.client)
    except (OSError, ValueError, TypeError):
        print("FALHA: arquivo OAuth ausente ou inválido.", file=sys.stderr)
        return 1
    print("OK: formato do cliente OAuth.")
    if args.check_config:
        print("Conexão real não testada.")
        return 0
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        print("Instale requirements-youtube.txt.", file=sys.stderr)
        return 1
    try:
        flow = InstalledAppFlow.from_client_config(config, SCOPES, autogenerate_code_verifier=True)
        creds = flow.run_local_server(host="127.0.0.1", port=0,
                                      authorization_prompt_message="Abra a autorização no navegador: {url}",
                                      success_message="Autorização concluída. Pode fechar esta página.",
                                      access_type="offline", prompt="consent", timeout_seconds=180)
        with build("youtube", "v3", credentials=creds, cache_discovery=False) as api:
            result = api.channels().list(part="snippet", mine=True).execute(num_retries=0)
            if not result.get("items"):
                print("FALHA: conta autenticada sem canal retornado.")
                return 2
            for channel in result["items"]:
                print("OK: canal autenticado:", channel["snippet"]["title"], channel["id"])
            if not creds.refresh_token:
                print("PENDENTE: autorização sem refresh token.")
                return 3
            creds.refresh(Request())
            api.channels().list(part="id", mine=True).execute(num_retries=0)
            print("OK: renovação do token e nova consulta à API.")
            print("Somente leitura validada. Nenhum vídeo enviado; tokens não salvos.")
            return 0
    except HttpError as exc:
        print("FALHA: YouTube Data API HTTP", exc.resp.status, file=sys.stderr)
    except Exception as exc:
        print("FALHA na autorização ou conexão:", type(exc).__name__, file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
