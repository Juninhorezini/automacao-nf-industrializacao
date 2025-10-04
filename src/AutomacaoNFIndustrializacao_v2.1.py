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
        expires_in = self.tokens.get('expires_in', 21600)
        expiration_time = generated_at + timedelta(seconds=expires_in - 300)

        return datetime.now() >= expiration_time

    def refresh_access_token(self) -> bool:
        """Renova o access token usando o refresh token"""
        if not self.tokens.get('refresh_token'):
            print("⚠️ Refresh token não disponível")
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
                print("✅ Access token renovado!")
                return True
            else:
                print(f"❌ Erro ao renovar: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Exceção: {str(e)}")
            return False

    def get_valid_token(self) -> str:
        """Retorna um token válido, renovando se necessário"""
        if self.is_token_expired():
            self.refresh_access_token()
        return self.tokens['access_token']


class AutomacaoNFIndustrializacao:
    """
    Sistema de automação para emissão de NF-e de industrialização
    Versão 2.1 - Emissão sequencial de ambas as NF-e
    """

    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.load_config()
        self.token_manager = BlingTokenManager()
        print("✅ Sistema v2.1 - Emissão sequencial de NF-e")

    def load_config(self):
        """Carrega configurações"""
        with open('/tmp/automacao_config.json', 'r') as f:
            self.config = json.load(f)

    def emitir_nfe_sequencial(self, produto: str, quantidade: float, 
                              depara: Dict, valores: Dict, 
                              notas_usadas: List[Dict]) -> Dict:
        """
        Emite AMBAS as NF-e em sequência imediata:
        1. NF de Retorno (CFOP 5902)
        2. NF de Industrialização (CFOP 5124)

        Retorna: dict com status e números das NF-e
        """
        print("\n" + "="*70)
        print("📋 EMISSÃO SEQUENCIAL DE NF-e")
        print("="*70)
        print(f"Produto: {produto} | Quantidade: {quantidade}")

        resultado = {
            "sucesso": False,
            "nf_retorno": None,
            "nf_industrial": None,
            "erro": None
        }

        # PASSO 1: Montar NF de Retorno
        nf_retorno_payload = self.montar_nf_retorno(
            produto, quantidade, depara, valores, notas_usadas
        )

        # PASSO 2: Montar NF de Industrialização
        nf_industrial_payload = self.montar_nf_industrial(
            produto, quantidade, depara, valores, notas_usadas
        )

        # PASSO 3: Emitir NF de RETORNO (imediatamente)
        print("\n📤 [1/2] Emitindo NF de RETORNO...")
        resp_retorno, erro_retorno = self.emitir_nf_bling(
            nf_retorno_payload, "RETORNO"
        )

        if erro_retorno:
            resultado["erro"] = f"Falha na NF de Retorno: {erro_retorno}"
            return resultado

        resultado["nf_retorno"] = resp_retorno
        print(f"✅ NF Retorno emitida: {resp_retorno.get('numero', 'N/A')}")

        # PASSO 4: Emitir NF de INDUSTRIALIZAÇÃO (SEM DELAY)
        print("\n📤 [2/2] Emitindo NF de INDUSTRIALIZAÇÃO...")
        resp_industrial, erro_industrial = self.emitir_nf_bling(
            nf_industrial_payload, "INDUSTRIALIZAÇÃO"
        )

        if erro_industrial:
            resultado["erro"] = f"Falha na NF Industrial: {erro_industrial}"
            return resultado

        resultado["nf_industrial"] = resp_industrial
        resultado["sucesso"] = True

        print(f"✅ NF Industrial emitida: {resp_industrial.get('numero', 'N/A')}")
        print("\n" + "="*70)
        print("✅ AMBAS AS NF-e EMITIDAS EM SEQUÊNCIA!")
        print("="*70)

        return resultado

    def montar_nf_retorno(self, produto: str, quantidade: float,
                          depara: Dict, valores: Dict, notas_usadas: List[Dict]) -> Dict:
        """Monta payload da NF de Retorno (CFOP 5902)"""
        produto_retorno = depara[produto]["produto_retorno"]
        valor_unit = valores[produto]["retorno"]
        nf_principal = notas_usadas[0]

        return {
            "tipo": 1,
            "dataEmissao": datetime.now().strftime("%Y-%m-%d"),
            "dataOperacao": datetime.now().strftime("%Y-%m-%d"),
            "naturezaOperacao": {
                "descricao": "Retorno de mercadoria recebida para industrialização"
            },
            "contato": self.config["cliente_ficticio"],
            "itens": [{
                "codigo": produto_retorno,
                "descricao": "Produto Industrializado - Retorno",
                "quantidade": quantidade,
                "valor": valor_unit,
                "unidade": "KG",
                "tipo": "P",
                "cfop": "5902"
            }],
            "informacoesAdicionais": {
                "informacoesComplementares": f"NF Retorno ref. NF {nf_principal['nf_numero']}"
            }
        }

    def montar_nf_industrial(self, produto: str, quantidade: float,
                            depara: Dict, valores: Dict, notas_usadas: List[Dict]) -> Dict:
        """Monta payload da NF de Industrialização (CFOP 5124)"""
        produto_industrial = depara[produto]["produto_industrial"]
        material_codigo = depara[produto]["material_codigo"]
        nf_principal = notas_usadas[0]

        return {
            "tipo": 1,
            "dataEmissao": datetime.now().strftime("%Y-%m-%d"),
            "dataOperacao": datetime.now().strftime("%Y-%m-%d"),
            "naturezaOperacao": {
                "descricao": "Industrialização efetuada para terceiros"
            },
            "contato": self.config["cliente_ficticio"],
            "itens": [
                {
                    "codigo": produto_industrial,
                    "descricao": "Serviço de Industrialização",
                    "quantidade": quantidade,
                    "valor": valores[produto]["industrial"],
                    "unidade": "KG",
                    "tipo": "S",
                    "cfop": "5124"
                },
                {
                    "codigo": material_codigo,
                    "descricao": "Material Aplicado",
                    "quantidade": quantidade,
                    "valor": valores[produto]["material"],
                    "unidade": "KG",
                    "tipo": "P",
                    "cfop": "5124"
                }
            ],
            "informacoesAdicionais": {
                "informacoesComplementares": f"Industrialização ref. NF {nf_principal['nf_numero']}"
            }
        }

    def emitir_nf_bling(self, nf_data: Dict, tipo_nf: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Emite NF via API do Bling"""
        url = "https://www.bling.com.br/Api/v3/nfe"
        access_token = self.token_manager.get_valid_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            # Modo teste
            if self.config["modo"] == "teste" and not self.config["transmitir_sefaz"]:
                print(f"⚠️ MODO TESTE - Simulando emissão")
                return {
                    "id": f"TESTE_{tipo_nf}_{datetime.now().strftime('%H%M%S')}",
                    "numero": "999999"
                }, None

            # Modo produção
            response = requests.post(url, json=nf_data, headers=headers)

            if response.status_code in [200, 201]:
                return response.json().get('data', {}), None
            else:
                return None, f"Erro {response.status_code}: {response.text[:200]}"

        except Exception as e:
            return None, str(e)

# Uso:
# automacao = AutomacaoNFIndustrializacao("SPREADSHEET_ID")
# resultado = automacao.emitir_nfe_sequencial(produto, qtd, depara, valores, notas)
