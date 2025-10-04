import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class BlingTokenManager:
    """Gerenciador de tokens do Bling com refresh automático"""

    def __init__(self, tokens_file: str = '/tmp/bling_tokens.json'):
        self.tokens_file = tokens_file
        self.load_tokens()

    def load_tokens(self):
        """Carrega tokens do arquivo"""
        with open(self.tokens_file, 'r') as f:
            self.tokens = json.load(f)

    def save_tokens(self):
        """Salva tokens no arquivo"""
        with open(self.tokens_file, 'w') as f:
            json.dump(self.tokens, f, indent=2)

    def is_token_expired(self) -> bool:
        """Verifica se o token está expirado"""
        if not self.tokens.get('token_generated_at'):
            return True

        generated_at = datetime.fromisoformat(self.tokens['token_generated_at'])
        expires_in = self.tokens.get('expires_in', 21600)  # 6 horas padrão

        # Considera expirado 5 minutos antes para margem de segurança
        expiration_time = generated_at + timedelta(seconds=expires_in - 300)

        return datetime.now() >= expiration_time

    def refresh_access_token(self) -> bool:
        """Renova o access token usando o refresh token"""
        if not self.tokens.get('refresh_token'):
            print("⚠️ Refresh token não disponível. Use o access token atual.")
            return False

        print("🔄 Renovando access token...")

        url = "https://www.bling.com.br/Api/v3/oauth/token"

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.tokens['refresh_token']
        }

        auth = (self.tokens['client_id'], self.tokens['client_secret'])

        try:
            response = requests.post(url, data=payload, auth=auth)

            if response.status_code == 200:
                data = response.json()

                self.tokens['access_token'] = data['access_token']
                self.tokens['refresh_token'] = data.get('refresh_token', self.tokens['refresh_token'])
                self.tokens['expires_in'] = data.get('expires_in', 21600)
                self.tokens['token_generated_at'] = datetime.now().isoformat()

                self.save_tokens()

                print("✅ Access token renovado com sucesso!")
                return True
            else:
                print(f"❌ Erro ao renovar token: {response.status_code}")
                print(f"   Resposta: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Exceção ao renovar token: {str(e)}")
            return False

    def get_valid_token(self) -> str:
        """Retorna um token válido, renovando se necessário"""
        if self.is_token_expired():
            print("⚠️ Token expirado, tentando renovar...")
            if not self.refresh_access_token():
                print("⚠️ Usando token atual (pode estar expirado)")

        return self.tokens['access_token']


class AutomacaoNFIndustrializacao:
    """
    Sistema de automação para emissão de NF-e de industrialização
    - NF de Retorno (CFOP 5902)
    - NF de Industrialização (CFOP 5124)

    VERSÃO 2.0 - Com gerenciamento automático de tokens Bling
    """

    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.load_config()
        self.token_manager = BlingTokenManager()
        print("✅ Sistema inicializado com gerenciamento automático de tokens")

    def load_config(self):
        """Carrega configurações"""
        with open('/tmp/automacao_config.json', 'r') as f:
            self.config = json.load(f)
        print("✅ Configurações carregadas")

    def ler_planilha(self, sheet_name: str, range_spec: str) -> List[List]:
        """Lê dados da planilha via Composio"""
        result, error = run_composio_tool(
            "GOOGLESHEETS_BATCH_GET",
            {
                "spreadsheet_id": self.spreadsheet_id,
                "ranges": [f"{sheet_name}!{range_spec}"]
            }
        )

        if error:
            print(f"❌ Erro ao ler {sheet_name}: {error}")
            return []

        values = result.get("data", {}).get("valueRanges", [{}])[0].get("values", [])
        return values

    def atualizar_planilha(self, sheet_name: str, cell: str, values: List[List]):
        """Atualiza células da planilha"""
        result, error = run_composio_tool(
            "GOOGLESHEETS_BATCH_UPDATE",
            {
                "spreadsheet_id": self.spreadsheet_id,
                "sheet_name": sheet_name,
                "first_cell_location": cell,
                "values": values
            }
        )

        if error:
            print(f"⚠️ Erro ao atualizar {sheet_name}: {error}")
            return False
        return True

    def emitir_nf_bling(self, nf_data: Dict, tipo_nf: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Emite NF via API do Bling com token válido (refresh automático)
        Retorna: (resposta, erro)
        """
        url = "https://www.bling.com.br/Api/v3/nfe"

        # Obter token válido (com refresh automático se necessário)
        access_token = self.token_manager.get_valid_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        print(f"\n📤 Emitindo {tipo_nf}...")
        print(f"Itens: {len(nf_data.get('itens', []))}")

        try:
            # Em modo teste, apenas simular
            if self.config["modo"] == "teste" and not self.config["transmitir_sefaz"]:
                print(f"⚠️  MODO TESTE - NF NÃO será realmente emitida!")
                print(f"Payload preparado:")
                print(json.dumps(nf_data, indent=2, ensure_ascii=False)[:500])

                # Simular resposta
                return {
                    "id": f"TESTE_{tipo_nf}_{datetime.now().strftime('%H%M%S')}",
                    "numero": "999999",
                    "serie": "1",
                    "situacao": "TESTE"
                }, None

            # Modo produção - emitir de verdade
            response = requests.post(url, json=nf_data, headers=headers)

            if response.status_code in [200, 201]:
                print(f"✅ {tipo_nf} emitida com sucesso!")
                return response.json(), None
            else:
                erro = f"Erro {response.status_code}: {response.text[:200]}"
                print(f"❌ {erro}")
                return None, erro

        except Exception as e:
            erro = f"Exceção: {str(e)}"
            print(f"❌ {erro}")
            return None, erro

# Código completo continua aqui com todos os outros métodos...
# (executar, processar_produto, montar_nf_retorno, montar_nf_industrial, etc.)
