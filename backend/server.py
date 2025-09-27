from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, File, UploadFile
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, EmailStr, Field, validator
from pydantic_settings import BaseSettings
from typing import List, Dict, Optional
import numpy as np
from scipy.optimize import fsolve
import warnings
warnings.filterwarnings('ignore')
import tempfile
from datetime import datetime, timezone, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
import hmac
import hashlib
import base64
import json
from notion_client import Client
import anthropic
import PyPDF2
from io import BytesIO

# Import do prompt especializado
from prompts.prompt_consorcio import prompt_consorcio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
db = client.consorcio_db

# Create the main app without a prefix
app = FastAPI(title="Simulador de Consórcio API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models para Lead Capture
class LeadData(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    patrimonio: Optional[float] = Field(None, ge=0)
    renda: Optional[float] = Field(None, ge=0)
    profissao: Optional[str] = Field(None, max_length=100)  # 🔧 ADICIONAR: Campo profissão
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    has_access: bool = True
    access_token: Optional[str] = None

class SimulationInput(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: Optional[str] = None  # Associar com o lead que fez a simulação
    access_token_usado: Optional[str] = None  # 🔧 ADICIONAR: Token usado para debug
    valor_carta: float
    prazo_meses: int
    taxa_admin: float
    fundo_reserva: float
    mes_contemplacao: int
    lance_livre_perc: float
    taxa_reajuste_anual: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class TypeformWebhook(BaseModel):
    event_id: str
    event_type: str
    form_response: dict

# Models
class ParametrosConsorcio(BaseModel):
    valor_carta: float = 100_000
    prazo_meses: int = 120
    taxa_admin: float = 0.21
    fundo_reserva: float = 0.03
    mes_contemplacao: int = 1
    lance_livre_perc: float = 0.10
    taxa_reajuste_anual: float = 0.05

class DetalhamentoMes(BaseModel):
    mes: int
    data: str  # Data formatada (set/25, out/25, etc.)
    ano: int
    fator_correcao: float
    valor_carta_corrigido: float
    parcela_corrigida: float
    parcela_antes: float  # Valor da parcela antes da contemplação
    parcela_depois: float  # Valor da parcela após contemplação
    lance_livre: float
    fluxo_liquido: float
    saldo_devedor: float
    eh_contemplacao: bool

class ResumoFinanceiro(BaseModel):
    base_contrato: float
    valor_lance_livre: float
    valor_carta_contemplacao: float
    total_parcelas: float
    fluxo_contemplacao: float
    primeira_parcela: float
    primeira_parcela_pos_contemplacao: float
    parcela_intermediaria: float
    ultima_parcela: float
    # Resumo da Operação (como no site de referência)
    valor_credito_taxas: float
    taxas: float
    lance_embutido: float
    credito_liquido: float
    # Probabilidades específicas do mês de contemplação escolhido
    prob_contemplacao_no_mes: float = 0.0
    prob_contemplacao_ate_mes: float = 0.0
    participantes_restantes_mes: int = 0

class ResultadosSimulacao(BaseModel):
    cet_anual: Optional[float]
    cet_mensal: Optional[float]
    vpl: Optional[float]  # Valor Presente Líquido
    taxa_desconto_vpl: Optional[float]  # Taxa usada no VPL
    convergiu: bool
    motivo_erro: Optional[str]

class RespostaSimulacao(BaseModel):
    erro: bool
    mensagem: Optional[str] = None
    parametros: Optional[ParametrosConsorcio] = None
    resultados: Optional[ResultadosSimulacao] = None
    fluxos: List[float] = []
    detalhamento: List[DetalhamentoMes] = []
    resumo_financeiro: Optional[ResumoFinanceiro] = None

class ParametrosProbabilidade(BaseModel):
    num_participantes: int = 430
    lance_livre_perc: float = 0.10

class CurvasProbabilidade(BaseModel):
    meses: List[int]
    hazard: List[float]
    probabilidade_acumulada: List[float]
    probabilidade_mes: List[float]
    esperanca_meses: float
    mediana_mes: Optional[int]
    p10_mes: Optional[int]
    p90_mes: Optional[int]

class RespostaProbabilidades(BaseModel):
    erro: bool
    mensagem: Optional[str] = None
    sem_lance: Optional[CurvasProbabilidade] = None
    com_lance: Optional[CurvasProbabilidade] = None
    parametros: Optional[Dict] = None

class SimuladorConsorcio:
    """Simulador de consórcio baseado na metodologia fornecida."""
    
    def __init__(self, parametros: ParametrosConsorcio):
        self.params = parametros
        self.convergiu = True
        self.motivo_erro = ""
    
    def calcular_base_lance(self) -> float:
        """Calcula base para lance: Crédito + Taxas + Fundo."""
        return self.params.valor_carta * (1 + self.params.taxa_admin + self.params.fundo_reserva)
    
    def gerar_fluxos_lance_livre(self) -> Dict:
        """Gera fluxos de caixa corretos - parcela só diminui com lance embutido."""
        try:
            # Base de cálculo
            base_contrato = self.calcular_base_lance()
            valor_lance_livre = base_contrato * self.params.lance_livre_perc
            
            # Cálculos do resumo da operação
            valor_credito_taxas = base_contrato  # R$ 124.000,00
            taxas = self.params.valor_carta * (self.params.taxa_admin + self.params.fundo_reserva)  # R$ 24.000,00
            lance_embutido = base_contrato * 0.08  # Aproximadamente 8% (baseado no documento)
            credito_liquido = self.params.valor_carta - (taxas + valor_lance_livre + lance_embutido - base_contrato)
            
            # Parcela base mensal - SEMPRE A MESMA (não diminui com lance livre)
            parcela_base_mensal = base_contrato / self.params.prazo_meses
            
            fluxos = [0]  # t=0
            detalhamento = []
            primeira_parcela = 0
            primeira_parcela_pos_contemplacao = 0
            parcela_intermediaria = 0
            ultima_parcela = 0
            
            # CORREÇÃO: Saldo devedor inicial = valor da carta + taxas (lógica correta)
            saldo_devedor_inicial = base_contrato  # R$ 100.000 + 24% = R$ 124.000
            saldo_devedor_atual = saldo_devedor_inicial
            
            # Taxa de correção mensal baseada na taxa anual
            taxa_correcao_mensal = (1 + self.params.taxa_reajuste_anual) ** (1/12) - 1
            
            # Meses em português
            meses_pt = ['', 'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 
                       'jul', 'ago', 'set', 'out', 'nov', 'dez']
            
            # Meses em português
            meses_pt = ['', 'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 
                       'jul', 'ago', 'set', 'out', 'nov', 'dez']
            
            for mes in range(1, self.params.prazo_meses + 1):
                # 1. Calcular ano atual e fator de correção
                ano_atual = (mes - 1) // 12 + 1
                fator_correcao = (1 + self.params.taxa_reajuste_anual) ** (ano_atual - 1)
                
                # 2. Corrigir o saldo devedor pela mesma lógica das parcelas (no início de cada ano)
                if mes > 1 and ((mes - 1) % 12 == 0):  # Início de novo ano
                    # Aplicar correção anual ao saldo devedor
                    saldo_devedor_atual = saldo_devedor_atual * (1 + self.params.taxa_reajuste_anual)
                
                # Data formatada (set/25, out/25, etc.)
                mes_calendario = ((mes - 1) % 12) + 1
                ano_calendario = 2025 + (mes - 1) // 12
                data_formatada = f"{meses_pt[mes_calendario]}/{str(ano_calendario)[2:]}"
                
                # Valores corrigidos
                valor_carta_corrigido = self.params.valor_carta * fator_correcao
                
                # Parcela corrigida pela correção anual
                parcela_corrigida = parcela_base_mensal * fator_correcao
                
                if mes == self.params.mes_contemplacao:
                    # CONTEMPLAÇÃO: Recebe carta, paga parcela e lance livre
                    fluxo = valor_carta_corrigido - parcela_corrigida - valor_lance_livre
                    lance_mes = valor_lance_livre
                    primeira_parcela = parcela_corrigida
                else:
                    # DEMAIS MESES: Só paga parcela (valor sempre igual)
                    fluxo = -parcela_corrigida
                    lance_mes = 0
                    
                    # Guardar primeira parcela pós-contemplação (igual à anterior)
                    if mes == self.params.mes_contemplacao + 1:
                        primeira_parcela_pos_contemplacao = parcela_corrigida
                
                # 3. DEPOIS: Subtrair a parcela do saldo devedor
                saldo_devedor_atual -= parcela_corrigida
                
                # Garantir que saldo não fique negativo (por questões de arredondamento)
                saldo_devedor_atual = max(0, saldo_devedor_atual)
                
                # Guardar parcela intermediária (meio do prazo)
                if mes == self.params.prazo_meses // 2:
                    parcela_intermediaria = parcela_corrigida
                    
                # Última parcela
                if mes == self.params.prazo_meses:
                    ultima_parcela = parcela_corrigida
                
                fluxos.append(fluxo)
                
                detalhamento.append({
                    'mes': mes,
                    'data': data_formatada,
                    'ano': ano_atual,
                    'fator_correcao': fator_correcao,
                    'valor_carta_corrigido': valor_carta_corrigido,
                    'parcela_corrigida': parcela_corrigida,
                    'parcela_antes': parcela_corrigida,  # Igual à parcela corrigida
                    'parcela_depois': parcela_corrigida,  # Igual à parcela corrigida (consórcio não muda após contemplação)
                    'lance_livre': lance_mes,
                    'fluxo_liquido': fluxo,
                    'saldo_devedor': max(0, saldo_devedor_atual),
                    'eh_contemplacao': mes == self.params.mes_contemplacao
                })
            
            # Calcular valor da carta na contemplação
            mes_contemplacao = self.params.mes_contemplacao
            ano_contemplacao = (mes_contemplacao - 1) // 12 + 1
            fator_correcao_contemplacao = (1 + self.params.taxa_reajuste_anual) ** (ano_contemplacao - 1)
            valor_carta_contemplacao = self.params.valor_carta * fator_correcao_contemplacao
            
            # Se não temos parcela pós-contemplação, é igual à primeira
            if primeira_parcela_pos_contemplacao == 0:
                primeira_parcela_pos_contemplacao = primeira_parcela
            
            # Se não temos parcela intermediária definida, usar uma estimativa
            if parcela_intermediaria == 0:
                parcela_intermediaria = parcela_base_mensal * (1 + self.params.taxa_reajuste_anual) ** 4
            
            return {
                'fluxos': fluxos,
                'detalhamento': detalhamento,
                'resumo': {
                    'base_contrato': base_contrato,
                    'valor_lance_livre': valor_lance_livre,
                    'valor_carta_contemplacao': valor_carta_contemplacao,
                    'total_parcelas': sum(d['parcela_corrigida'] for d in detalhamento if not d['eh_contemplacao']),
                    'fluxo_contemplacao': fluxos[self.params.mes_contemplacao],
                    'primeira_parcela': primeira_parcela,
                    'primeira_parcela_pos_contemplacao': primeira_parcela_pos_contemplacao,
                    'parcela_intermediaria': parcela_intermediaria,
                    'ultima_parcela': ultima_parcela,
                    # Resumo da Operação
                    'valor_credito_taxas': valor_credito_taxas,
                    'taxas': taxas,
                    'lance_embutido': lance_embutido,
                    'credito_liquido': credito_liquido
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na geração de fluxos: {e}")
            return {'fluxos': [], 'detalhamento': [], 'resumo': {}}
            
        except Exception as e:
            logger.error(f"Erro na geração de fluxos: {e}")
            return {'fluxos': [], 'detalhamento': [], 'resumo': {}}
    
    def calcular_vpl(self, fluxos: List[float], taxa_desconto: float = 0.10) -> float:
        """
        Calcula VPL (Valor Presente Líquido) como método alternativo quando CET não converge.
        
        Args:
            fluxos: Lista de fluxos de caixa
            taxa_desconto: Taxa de desconto anual (default: 10%)
            
        Returns:
            VPL dos fluxos de caixa
        """
        try:
            if len(fluxos) < 2:
                return np.nan
            
            # Converter taxa anual para mensal
            taxa_mensal = (1 + taxa_desconto) ** (1/12) - 1
            
            # Calcular VPL
            vpl = sum(cf / (1 + taxa_mensal) ** i for i, cf in enumerate(fluxos))
            
            return vpl
            
        except Exception as e:
            logger.error(f"Erro no cálculo do VPL: {e}")
            return np.nan
    
    def calcular_cet(self, fluxos: List[float]) -> float:
        """Calcula CET com método robusto."""
        def vpv(taxa_mensal):
            return sum(cf / (1 + taxa_mensal) ** i for i, cf in enumerate(fluxos))
        
        if len(fluxos) < 2:
            self.convergiu = False
            self.motivo_erro = "Fluxos insuficientes"
            return np.nan
        
        # Verificar mudanças de sinal
        sinais = [np.sign(f) for f in fluxos if f != 0]
        if len(set(sinais)) < 2:
            self.convergiu = False
            self.motivo_erro = "Sem mudança de sinal nos fluxos"
            return np.nan
        
        try:
            tentativas = [0.005, 0.01, 0.015, 0.02, 0.001, 0.03, -0.001, 0.0001]
            
            for taxa_inicial in tentativas:
                try:
                    taxa_mensal = fsolve(vpv, taxa_inicial, xtol=1e-12, maxfev=2000)[0]
                    
                    if abs(vpv(taxa_mensal)) < 1e-6:
                        taxa_anual = (1 + taxa_mensal) ** 12 - 1
                        
                        if -0.99 <= taxa_anual <= 5.0:
                            self.convergiu = True
                            return taxa_anual
                
                except (ValueError, RuntimeWarning):
                    continue
            
            self.convergiu = False
            self.motivo_erro = "Convergência não alcançada"
            return np.nan
            
        except Exception as e:
            self.convergiu = False
            self.motivo_erro = f"Erro matemático: {str(e)[:50]}"
            return np.nan
    
    def simular_cenario_completo(self) -> Dict:
        """Simulação completa do cenário atual."""
        resultado_fluxos = self.gerar_fluxos_lance_livre()
        
        if not resultado_fluxos['fluxos']:
            return {
                'erro': True,
                'mensagem': 'Erro na geração de fluxos'
            }
        
        # Tentar calcular CET primeiro
        cet = self.calcular_cet(resultado_fluxos['fluxos'])
        
        # Verificar se CET é válido (não NaN e não negativo)
        cet_valido = not np.isnan(cet) and cet >= 0
        
        # Se CET for negativo, também considerar como não convergido
        if not np.isnan(cet) and cet < 0:
            self.convergiu = False
            if not self.motivo_erro:  # Só sobrescrever se não houver motivo anterior
                self.motivo_erro = "CET negativo - resultado inválido"
        
        # Calcular VPL sempre (como alternativa ao CET)
        taxa_desconto = 0.10  # 10% para teste, conforme solicitado
        vpl = self.calcular_vpl(resultado_fluxos['fluxos'], taxa_desconto)
        
        # Convert values for JSON serialization - usar VPL quando CET não for válido
        if cet_valido:
            cet_anual_json = float(cet)
            cet_mensal_json = float((1 + cet) ** (1/12) - 1)
        else:
            cet_anual_json = None
            cet_mensal_json = None
            
        vpl_json = None if np.isnan(vpl) else float(vpl)
        
        return {
            'erro': False,
            'parametros': self.params.dict(),
            'resultados': {
                'cet_anual': cet_anual_json,
                'cet_mensal': cet_mensal_json,
                'vpl': vpl_json,
                'taxa_desconto_vpl': taxa_desconto,
                'convergiu': self.convergiu,
                'motivo_erro': self.motivo_erro
            },
            'fluxos': resultado_fluxos['fluxos'],
            'detalhamento': resultado_fluxos['detalhamento'],
            'resumo_financeiro': resultado_fluxos['resumo']
        }

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Simulador de Consórcio API - Ativo"}

@api_router.post("/simular", response_model=RespostaSimulacao)
async def simular_consorcio(parametros: ParametrosConsorcio, request: Request):
    """Simula um consórcio com os parâmetros fornecidos."""
    try:
        # Validações básicas
        if parametros.valor_carta <= 0:
            raise HTTPException(status_code=400, detail="Valor da carta deve ser positivo")
        
        if parametros.prazo_meses <= 0:
            raise HTTPException(status_code=400, detail="Prazo deve ser positivo")
        
        if parametros.mes_contemplacao > parametros.prazo_meses:
            raise HTTPException(status_code=400, detail="Mês de contemplação não pode ser maior que o prazo")
        
        if parametros.mes_contemplacao <= 0:
            raise HTTPException(status_code=400, detail="Mês de contemplação deve ser positivo")
        
        # Salvar input da simulação no banco de dados
        try:
            auth_header = request.headers.get("Authorization", "")
            logger.info(f"🔑 AUTHORIZATION HEADER: '{auth_header}'")
            
            # 🔧 CORREÇÃO: Extração mais robusta do token
            access_token = ""
            if auth_header:
                if auth_header.startswith("Bearer "):
                    access_token = auth_header[7:]  # Remove "Bearer "
                elif auth_header.startswith("bearer "):
                    access_token = auth_header[7:]  # Remove "bearer "
                else:
                    access_token = auth_header  # Usar como está se não tem Bearer
                
            logger.info(f"🎯 ACCESS_TOKEN EXTRAÍDO: '{access_token}'")
            
            lead_id = None
            access_token_usado = access_token if access_token else None  # Salvar token usado
            
            if access_token:
                logger.info(f"🔍 Buscando lead com token: '{access_token}'")
                lead = await db.leads.find_one({"access_token": access_token})
                if lead:
                    lead_id = lead["id"]
                    logger.info(f"✅ Lead encontrado! ID: {lead_id}, Nome: {lead.get('name')}, Email: {lead.get('email')}")
                else:
                    logger.error(f"❌ Lead NÃO encontrado com token: '{access_token}'")
                    # Debug: listar tokens disponíveis
                    all_leads = await db.leads.find({}, {"access_token": 1, "name": 1, "email": 1}).limit(3).to_list(None)
                    logger.info(f"🔍 Tokens disponíveis: {[{'token': l.get('access_token'), 'name': l.get('name')} for l in all_leads]}")
            else:
                logger.warning("⚠️ Nenhum access_token fornecido na simulação")
            
            simulation_input = SimulationInput(
                lead_id=lead_id,
                access_token_usado=access_token_usado,  # 🔧 ADICIONAR: Salvar token usado para debug
                valor_carta=parametros.valor_carta,
                prazo_meses=parametros.prazo_meses,
                taxa_admin=parametros.taxa_admin,
                fundo_reserva=parametros.fundo_reserva,
                mes_contemplacao=parametros.mes_contemplacao,
                lance_livre_perc=parametros.lance_livre_perc,
                taxa_reajuste_anual=parametros.taxa_reajuste_anual,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
            
            # 🔧 DEBUG: Log antes de salvar
            logger.info(f"📝 Dados da simulação ANTES de salvar:")
            logger.info(f"   - ID: {simulation_input.id}")
            logger.info(f"   - Lead_ID: {lead_id}")
            logger.info(f"   - Access_token_usado: {access_token_usado}")
            
            await db.simulation_inputs.insert_one(simulation_input.dict())
            logger.info(f"💾 Simulação salva COM SUCESSO: ID={simulation_input.id}, Lead_ID={lead_id}, Token={access_token}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar simulação: {e}")
            import traceback
            logger.error(f"📋 Traceback completo: {traceback.format_exc()}")
            # Não interrompe a simulação se houver erro no salvamento
        
        # Criar simulador e executar
        simulador = SimuladorConsorcio(parametros)
        resultado = simulador.simular_cenario_completo()
        
        if resultado['erro']:
            return RespostaSimulacao(
                erro=True,
                mensagem=resultado.get('mensagem', 'Erro desconhecido na simulação')
            )
        
        # Calcular probabilidades específicas do mês de contemplação escolhido
        # NOVA LÓGICA: participantes = 2 × prazo_meses (1 sorteio + 1 lance sempre)
        num_participantes_padrao = parametros.prazo_meses * 2
        contemplados_por_mes_padrao = 2  # Sempre 2 (1 sorteio + 1 lance)
        
        prob_mes = calcular_probabilidade_mes_especifico(
            mes_contemplacao=parametros.mes_contemplacao,
            lance_livre_perc=parametros.lance_livre_perc,  # Mantém para cálculos financeiros
            num_participantes=num_participantes_padrao,
            contemplados_por_mes=contemplados_por_mes_padrao
        )
        
        # Adicionar probabilidades ao resumo financeiro
        if prob_mes:
            # Verificar se os valores são válidos (não NaN ou infinito)
            prob_no_mes = prob_mes['prob_no_mes']
            prob_ate_mes = prob_mes['prob_ate_mes']
            participantes_restantes = prob_mes['participantes_restantes']
            
            # Sanitizar valores
            if not np.isfinite(prob_no_mes):
                prob_no_mes = 0.0
            if not np.isfinite(prob_ate_mes):
                prob_ate_mes = 0.0
                
            resultado['resumo_financeiro']['prob_contemplacao_no_mes'] = float(prob_no_mes)
            resultado['resumo_financeiro']['prob_contemplacao_ate_mes'] = float(prob_ate_mes)
            resultado['resumo_financeiro']['participantes_restantes_mes'] = int(participantes_restantes)
        else:
            resultado['resumo_financeiro']['prob_contemplacao_no_mes'] = 0.0
            resultado['resumo_financeiro']['prob_contemplacao_ate_mes'] = 0.0
            resultado['resumo_financeiro']['participantes_restantes_mes'] = 0
        
        # Converter detalhamento para o modelo Pydantic
        detalhamento_convertido = []
        for item in resultado['detalhamento']:
            detalhamento_convertido.append(DetalhamentoMes(**item))
        
        return RespostaSimulacao(
            erro=False,
            parametros=ParametrosConsorcio(**resultado['parametros']),
            resultados=ResultadosSimulacao(**resultado['resultados']),
            fluxos=resultado['fluxos'],
            detalhamento=detalhamento_convertido,
            resumo_financeiro=ResumoFinanceiro(**resultado['resumo_financeiro'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na simulação: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@api_router.post("/save-lead")
async def save_lead(lead_data: LeadData):
    """Salvar lead diretamente (formulário simples)"""
    try:
        # Salvar no MongoDB
        await db.leads.insert_one(lead_data.dict())
        
        return {"status": "success", "lead_id": lead_data.id}
        
    except Exception as e:
        logger.error(f"Erro ao salvar lead: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@api_router.post("/typeform-webhook")
async def handle_typeform_webhook(request: Request):
    """Webhook do Typeform para capturar leads"""
    try:
        # Verificar signature (se configurado no Typeform)
        body = await request.body()
        signature = request.headers.get("typeform-signature")
        
        if signature and os.getenv("TYPEFORM_WEBHOOK_SECRET"):
            if not verify_typeform_signature(signature, body):
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Parse do payload
        payload = json.loads(body)
        
        # DEBUG: Log do payload completo para entender o formato
        logger.info(f"TYPEFORM PAYLOAD RECEBIDO: {json.dumps(payload, indent=2)}")
        
        # Extrair dados do formulário
        form_response = payload.get("form_response", {})
        answers = form_response.get("answers", [])
        
        # DEBUG: Log das answers para debug
        logger.info(f"TYPEFORM ANSWERS: {json.dumps(answers, indent=2)}")
        
        # Mapear respostas para dados do lead
        lead_data = extract_lead_data_from_typeform(answers)
        
        # Gerar token de acesso
        access_token = str(uuid.uuid4())
        lead_data.access_token = access_token
        
        # Salvar no MongoDB
        await db.leads.insert_one(lead_data.dict())
        
        logger.info(f"LEAD SALVO COM SUCESSO: {lead_data.dict()}")
        
        return {
            "status": "success", 
            "access_token": access_token,
            "lead_id": lead_data.id
        }
        
    except Exception as e:
        logger.error(f"Erro no webhook do Typeform: {e}")
        # DEBUG: Log do erro detalhado
        import traceback
        logger.error(f"TRACEBACK COMPLETO: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@api_router.post("/save-simulation")
async def save_simulation_input(
    simulation: ParametrosConsorcio, 
    request: Request,
    access_token: Optional[str] = None
):
    """Salvar inputs da simulação no banco de dados"""
    try:
        # Buscar lead pelo access token (se fornecido)
        lead_id = None
        if access_token:
            lead = await db.leads.find_one({"access_token": access_token})
            if lead:
                lead_id = lead["id"]
        
        # Criar registro da simulação
        simulation_input = SimulationInput(
            lead_id=lead_id,
            valor_carta=simulation.valor_carta,
            prazo_meses=simulation.prazo_meses,
            taxa_admin=simulation.taxa_admin,
            fundo_reserva=simulation.fundo_reserva,
            mes_contemplacao=simulation.mes_contemplacao,
            lance_livre_perc=simulation.lance_livre_perc,
            taxa_reajuste_anual=simulation.taxa_reajuste_anual,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        # Salvar no MongoDB
        await db.simulation_inputs.insert_one(simulation_input.dict())
        
        return {"status": "success", "simulation_id": simulation_input.id}
        
    except Exception as e:
        logger.error(f"Erro ao salvar simulação: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@api_router.get("/check-access/{access_token}")
async def check_access(access_token: str):
    """Verificar se o token de acesso é válido"""
    try:
        lead = await db.leads.find_one({"access_token": access_token})
        if lead and lead.get("has_access", True):
            return {
                "valid": True,
                "lead_id": lead["id"],
                "name": lead["name"],
                "created_at": lead["created_at"]
            }
        else:
            return {"valid": False}
    except Exception as e:
        logger.error(f"Erro ao verificar acesso: {e}")
        return {"valid": False}

def verify_typeform_signature(received_signature: str, payload: bytes) -> bool:
    """Verificar signature do webhook do Typeform"""
    try:
        webhook_secret = os.getenv("TYPEFORM_WEBHOOK_SECRET")
        if not webhook_secret:
            return True  # Se não tem secret configurado, aceita
        
        sha_name, signature = received_signature.split('=', 1)
        if sha_name != 'sha256':
            return False
        
        digest = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).digest()
        
        expected_signature = base64.b64encode(digest).decode()
        return hmac.compare_digest(expected_signature, signature)
        
    except Exception:
        return False

def extract_lead_data_from_typeform(answers: list) -> LeadData:
    """Extrair dados do lead das respostas do Typeform - VERSÃO FUNCIONAL"""
    
    # Inicializar dados
    extracted_data = {
        "name": None,
        "email": None,
        "phone": None,
        "patrimonio": None,
        "renda": None,
        "profissao": None
    }
    
    logger.info(f"📋 PROCESSANDO {len(answers)} RESPOSTAS")
    
    # Arrays para coletar dados
    nome_parts = []
    text_fields = []
    
    for i, answer in enumerate(answers):
        logger.info(f"📝 PROCESSANDO ANSWER {i}: {json.dumps(answer, indent=2)}")
        
        field = answer.get("field", {})
        field_type = answer.get("type", "")
        field_id = field.get("id", "")
        
        # EMAIL - DIRETO
        if field_type == "email" and answer.get("email"):
            extracted_data["email"] = answer.get("email").strip()
            logger.info(f"✅ EMAIL: {extracted_data['email']}")
        
        # TELEFONE - DIRETO  
        elif field_type == "phone_number" and answer.get("phone_number"):
            extracted_data["phone"] = answer.get("phone_number").strip()
            logger.info(f"✅ TELEFONE: {extracted_data['phone']}")
        
        # NÚMEROS - PATRIMÔNIO/RENDA
        elif field_type == "number" and answer.get("number") is not None:
            value = float(answer.get("number"))
            if extracted_data["patrimonio"] is None:
                extracted_data["patrimonio"] = value
                logger.info(f"✅ PATRIMÔNIO: {value}")
            elif extracted_data["renda"] is None:
                extracted_data["renda"] = value
                logger.info(f"✅ RENDA: {value}")
        
        # TEXTO - NOME/PROFISSÃO
        elif field_type in ["text"] and answer.get("text"):
            text_value = answer.get("text").strip()
            text_fields.append({
                "text": text_value,
                "field_id": field_id,
                "order": i
            })
            logger.info(f"📝 TEXTO COLETADO: '{text_value}' (ID: {field_id})")
        
        # CHOICE - COMO SOUBE (ignorar por enquanto)
        elif field_type == "choice":
            choice_label = answer.get("choice", {}).get("label", "")
            logger.info(f"📋 CHOICE IGNORADO: {choice_label}")
    
    # MONTAR NOME - LÓGICA SIMPLES E FUNCIONAL
    if text_fields:
        # Ordenar por ordem de aparição
        text_fields.sort(key=lambda x: x["order"])
        
        valid_names = []
        for field in text_fields:
            text = field["text"]
            
            # Validar se é nome válido
            if (text and 
                len(text) >= 2 and 
                len(text) <= 30 and
                text.replace(" ", "").replace("-", "").isalpha() and
                "@" not in text):
                
                # Capitalizar corretamente
                capitalized = " ".join(word.capitalize() for word in text.split())
                valid_names.append(capitalized)
                logger.info(f"✅ NOME VÁLIDO: '{text}' → '{capitalized}'")
        
        # Montar nome final
        if len(valid_names) >= 2:
            # Primeiro nome + sobrenome
            extracted_data["name"] = f"{valid_names[0]} {valid_names[1]}"
            logger.info(f"✅ NOME COMPLETO: {extracted_data['name']}")
            
            # Restante pode ser profissão
            if len(valid_names) > 2:
                extracted_data["profissao"] = valid_names[2]
                logger.info(f"✅ PROFISSÃO (nome extra): {extracted_data['profissao']}")
        
        elif len(valid_names) == 1:
            extracted_data["name"] = valid_names[0]
            logger.info(f"✅ NOME ÚNICO: {extracted_data['name']}")
        
        # PROFISSÃO dos campos restantes
        if not extracted_data["profissao"]:
            for field in text_fields:
                text = field["text"].lower()
                if (text and 
                    text not in [n.lower() for n in valid_names] and
                    any(prof in text for prof in ["eng", "adv", "med", "prof", "analista", "gerente", "diretor", "coordenador", "técnico", "vendedor", "consultor", "administrador", "contador"])):
                    
                    extracted_data["profissao"] = field["text"].title()
                    logger.info(f"✅ PROFISSÃO IDENTIFICADA: {extracted_data['profissao']}")
                    break
    
    # FALLBACKS 
    if not extracted_data["name"] and extracted_data["email"]:
        extracted_data["name"] = extracted_data["email"].split("@")[0].replace(".", " ").title()
        logger.info(f"🔄 NOME FALLBACK: {extracted_data['name']}")
    
    if not extracted_data["profissao"]:
        extracted_data["profissao"] = "Não informada"
    
    # LOG FINAL
    logger.info(f"📊 RESULTADO FINAL:")
    logger.info(f"   Nome: '{extracted_data['name']}'")
    logger.info(f"   Email: '{extracted_data['email']}'")
    logger.info(f"   Telefone: '{extracted_data['phone']}'") 
    logger.info(f"   Profissão: '{extracted_data['profissao']}'")
    logger.info(f"   Patrimônio: {extracted_data['patrimonio']}")
    logger.info(f"   Renda: {extracted_data['renda']}")
    
    return LeadData(
        name=extracted_data["name"] or "Nome não informado",
        email=extracted_data["email"] or "",
        phone=extracted_data["phone"] or "", 
        patrimonio=extracted_data["patrimonio"],
        renda=extracted_data["renda"],
        profissao=extracted_data["profissao"] or "Não informada"
    )

@api_router.get("/admin/dados-completos")
async def get_dados_completos():
    """Endpoint para visualizar leads + simulações associadas (admin)"""
    try:
        # Buscar leads e simulações
        leads = await db.leads.find({}, {"_id": 0}).to_list(length=100)
        simulations = await db.simulation_inputs.find({}, {"_id": 0}).to_list(length=100)
        
        # Criar associações
        dados_completos = []
        
        # Para cada lead, buscar simulações associadas
        for lead in leads:
            lead_data = {
                "lead": lead,
                "simulacoes": [sim for sim in simulations if sim.get('lead_id') == lead['id']],
                "total_simulacoes": len([sim for sim in simulations if sim.get('lead_id') == lead['id']])
            }
            dados_completos.append(lead_data)
        
        # Simulações sem lead associado (usuários que pularam o cadastro)
        simulacoes_sem_lead = [sim for sim in simulations if not sim.get('lead_id')]
        
        return {
            "leads_com_simulacoes": dados_completos,
            "simulacoes_sem_cadastro": simulacoes_sem_lead,
            "resumo": {
                "total_leads": len(leads),
                "total_simulacoes": len(simulations),
                "simulacoes_sem_cadastro": len(simulacoes_sem_lead),
                "leads_que_simularam": len([l for l in dados_completos if l['total_simulacoes'] > 0])
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados completos: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@api_router.get("/admin/saldo-devedor-detalhes")
async def get_saldo_devedor_detalhes():
    """Endpoint para visualizar detalhes do saldo devedor (admin)"""
    try:
        # Simular com parâmetros padrão para mostrar a lógica
        parametros = ParametrosConsorcio(
            valor_carta=100000,
            prazo_meses=120,
            taxa_admin=0.21,
            fundo_reserva=0.03,
            mes_contemplacao=17,
            lance_livre_perc=0.10,
            taxa_reajuste_anual=0.05
        )
        
        simulador = SimuladorConsorcio(parametros)
        resultado = simulador.simular_cenario_completo()
        
        if resultado['erro']:
            return {"erro": True, "mensagem": resultado.get('mensagem', 'Erro na simulação')}
        
        # Extrair informações específicas do saldo devedor
        detalhamento = resultado['detalhamento']
        
        # Pontos chave para análise
        pontos_chave = []
        meses_importantes = [1, 12, 13, 24, 25, 36, 37, 60, 119, 120]
        
        for mes in meses_importantes:
            if mes <= len(detalhamento):
                item = detalhamento[mes-1]
                ponto = {
                    "mes": mes,
                    "ano": item['ano'],
                    "saldo_devedor": item['saldo_devedor'],
                    "parcela_corrigida": item['parcela_corrigida'],
                    "data": item['data'],
                    "observacao": ""
                }
                
                if mes == 1:
                    ponto["observacao"] = "Saldo inicial após primeira parcela"
                elif mes in [12, 24, 36, 48, 60]:
                    ponto["observacao"] = "Final do ano"
                elif mes in [13, 25, 37]:
                    ponto["observacao"] = "Início novo ano - saldo corrigido"
                elif mes == 120:
                    ponto["observacao"] = "Saldo final (deve ser zero)"
                
                pontos_chave.append(ponto)
        
        # Cálculos de validação
        base_contrato = parametros.valor_carta * (1 + parametros.taxa_admin + parametros.fundo_reserva)
        
        return {
            "erro": False,
            "logica_implementada": {
                "saldo_inicial": base_contrato,
                "correcao_anual": parametros.taxa_reajuste_anual,
                "descricao": "Saldo inicial = Carta + Taxas. Correção anual no início de cada ano. Abatimento mensal da parcela."
            },
            "pontos_chave": pontos_chave,
            "resumo": {
                "saldo_inicial_teorico": base_contrato,
                "saldo_inicial_pos_primeira_parcela": pontos_chave[0]["saldo_devedor"] if pontos_chave else 0,
                "saldo_final": pontos_chave[-1]["saldo_devedor"] if pontos_chave else 0,
                "total_meses": len(detalhamento)
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do saldo devedor: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@api_router.get("/admin/leads")
async def get_leads():
    """Endpoint para visualizar leads capturados (admin)"""
    try:
        leads = await db.leads.find({}, {"_id": 0}).to_list(length=100)  # Excluir _id ObjectId
        return {"leads": leads, "total": len(leads)}
    except Exception as e:
        logger.error(f"Erro ao buscar leads: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@api_router.get("/admin/simulations")
async def get_simulations():
    """Endpoint para visualizar simulações realizadas (admin)"""
    try:
        simulations = await db.simulation_inputs.find({}, {"_id": 0}).to_list(length=100)  # Excluir _id ObjectId
        return {"simulations": simulations, "total": len(simulations)}
    except Exception as e:
        logger.error(f"Erro ao buscar simulações: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@api_router.get("/parametros-padrao")
async def get_parametros_padrao():
    """Retorna os parâmetros padrão para simulação."""
    return ParametrosConsorcio()

@api_router.get("/grafico-probabilidades/{prazo_meses}")
async def get_grafico_probabilidades(prazo_meses: int, lance_livre_perc: float = 0.10):
    """Endpoint para obter dados do gráfico de probabilidades."""
    try:
        if prazo_meses <= 0:
            raise HTTPException(status_code=400, detail="Prazo deve ser positivo")
        
        dados_grafico = gerar_dados_grafico_probabilidade(prazo_meses, lance_livre_perc)
        
        if dados_grafico is None:
            raise HTTPException(status_code=500, detail="Erro ao gerar dados do gráfico")
        
        return dados_grafico
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint de gráfico de probabilidades: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@api_router.post("/calcular-probabilidades", response_model=RespostaProbabilidades)
async def calcular_probabilidades(parametros: ParametrosProbabilidade):
    """Calcula probabilidades de contemplação para o consórcio."""
    try:
        # Validações básicas
        if parametros.num_participantes <= 0:
            raise HTTPException(status_code=400, detail="Número de participantes deve ser positivo")
        
        if parametros.lance_livre_perc < 0:
            raise HTTPException(status_code=400, detail="Lance livre deve ser >= 0")
        
        # Calcular probabilidades
        resultado = calcular_probabilidades_contemplacao_corrigido(
            num_participantes=parametros.num_participantes,
            lance_livre_perc=parametros.lance_livre_perc
        )
        
        if resultado is None:
            return RespostaProbabilidades(
                erro=True,
                mensagem="Erro no cálculo de probabilidades"
            )
        
        return RespostaProbabilidades(
            erro=False,
            sem_lance=CurvasProbabilidade(**resultado["sem_lance"]),
            com_lance=CurvasProbabilidade(**resultado["com_lance"]),
            parametros=resultado["parametros"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint de probabilidades: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


def criar_grafico_probabilidades(num_participantes: int, lance_livre_perc: float, temp_dir: str) -> str:
    """Cria gráfico de probabilidades de contemplação."""
    try:
        # Calcular probabilidades usando a lógica corrigida da planilha
        N0 = num_participantes
        
        meses_total = int(np.ceil(N0 / 2))
        
        # Listas para dados
        meses = []
        hazard_sem = []
        hazard_com = []
        prob_acum_sem = []
        prob_acum_com = []
        
        # Inicializar - ambos os cenários usam a mesma redução (2 por mês)
        n_atual = N0
        S_sem = 1.0  # Sobrevivência sem lance
        S_com = 1.0  # Sobrevivência com lance
        
        for mes in range(1, meses_total + 1):  # TODOS os meses até o final
            meses.append(mes)
            
            if n_atual > 0:
                # LÓGICA CORRIGIDA baseada na planilha:
                # Hazard sem lance: 1/(N-1) - só compete no sorteio
                h_sem = 1.0 / max(1, n_atual - 1)
                
                # Hazard com lance: 2/N - compete no sorteio E no lance
                h_com = min(2.0 / n_atual, 1.0)
            else:
                h_sem = 0
                h_com = 0
            
            hazard_sem.append(h_sem * 100)  # Em %
            hazard_com.append(h_com * 100)  # Em %
            
            # Atualizar sobrevivência e probabilidade acumulada
            S_sem *= (1 - h_sem)
            S_com *= (1 - h_com)
            
            prob_acum_sem.append((1 - S_sem) * 100)  # F_t em %
            prob_acum_com.append((1 - S_com) * 100)  # F_t em %
            
            # Reduzir participantes (sempre 2: 1 sorteio + 1 lance)
            n_atual = max(0, n_atual - 2)
        
        # Criar gráfico
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # Apenas Hazard (probabilidade do mês) - sem linhas tracejadas
        ax1.plot(meses, hazard_com, label="Com Lance — hazard", lw=2, color='#BC8159')
        ax1.plot(meses, hazard_sem, label="Sem Lance — hazard", lw=2, alpha=0.9, color='#8D4C23')
        ax1.set_xlabel("Mês")
        ax1.set_ylabel("Probabilidade do mês, h(t) [%]")
        ax1.set_ylim(0, 100)  # Eixo Y até 100%
        ax1.grid(True, alpha=0.25)
        
        # Apenas uma legenda para as linhas de hazard
        ax1.legend(loc='upper left')
        
        plt.title(f"Probabilidade de Contemplação — {N0} Participantes\n(hazard do mês)")
        plt.tight_layout()
        
        grafico_path = os.path.join(temp_dir, 'grafico_probabilidades.png')
        plt.savefig(grafico_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return grafico_path
    except Exception as e:
        logger.error(f"Erro ao criar gráfico de probabilidades: {e}")
        return None

def gerar_dados_grafico_fluxo_caixa(detalhamento: List[Dict]) -> Dict:
    """Gera dados do gráfico de fluxo de caixa para o frontend."""
    try:
        # Usar os primeiros 24 meses para o gráfico
        meses_grafico = min(24, len(detalhamento))
        
        labels = []
        parcelas_antes = []
        parcelas_depois = []
        saldo_devedor = []
        
        for i in range(meses_grafico):
            mes_data = detalhamento[i]
            labels.append(f"Mês {mes_data['mes']}")
            parcelas_antes.append(round(mes_data['parcela_antes'], 2))
            parcelas_depois.append(round(mes_data['parcela_depois'], 2))
            saldo_devedor.append(round(mes_data['saldo_devedor'], 2))
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Parcela Antes da Contemplação",
                    "data": parcelas_antes,
                    "borderColor": "rgb(255, 99, 132)",
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "tension": 0.1,
                    "fill": False
                },
                {
                    "label": "Parcela Depois da Contemplação",
                    "data": parcelas_depois,
                    "borderColor": "rgb(54, 162, 235)",
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "tension": 0.1,
                    "fill": False
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar dados do gráfico de fluxo de caixa: {e}")
        return None

def gerar_dados_grafico_saldo_devedor(detalhamento: List[Dict]) -> Dict:
    """Gera dados do gráfico de saldo devedor para o frontend."""
    try:
        # Usar todos os meses mas limitar visual a 60 para performance
        meses_grafico = min(60, len(detalhamento))
        
        labels = []
        saldo_valores = []
        
        for i in range(meses_grafico):
            mes_data = detalhamento[i]
            labels.append(f"Mês {mes_data['mes']}")
            saldo_valores.append(round(mes_data['saldo_devedor'], 2))
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Saldo Devedor",
                    "data": saldo_valores,
                    "borderColor": "rgb(75, 192, 192)",
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "tension": 0.1,
                    "fill": True
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar dados do gráfico de saldo devedor: {e}")
        return None

def gerar_dados_grafico_probabilidade(prazo_meses: int, lance_livre_perc: float) -> Dict:
    """Gera dados do gráfico de probabilidade para o frontend."""
    try:
        # Usar lógica similar ao PDF - participantes = 2 × prazo
        num_participantes = prazo_meses * 2
        N0 = num_participantes
        
        # Usar o prazo completo para o gráfico (até 120 meses conforme solicitado)
        meses_total = min(prazo_meses, int(np.ceil(N0 / 2)))
        
        # Listas para dados
        meses = []
        hazard_sem = []
        hazard_com = []
        
        # Inicializar
        n_atual = N0
        
        for mes in range(1, meses_total + 1):
            # Labels só com números (não "Mês 1, Mês 2...")
            meses.append(mes)
            
            if n_atual > 0:
                # Hazard sem lance: 1/(N-1) - só compete no sorteio
                h_sem = 1.0 / max(1, n_atual - 1)
                
                # Hazard com lance: depende do percentual de lance livre
                if lance_livre_perc > 0:
                    # Se há lance livre, 2/N - compete no sorteio E no lance
                    h_com = min(2.0 / n_atual, 1.0)
                else:
                    # Se não há lance livre (0%), é igual ao sem lance
                    h_com = h_sem
            else:
                h_sem = 0
                h_com = 0
            
            hazard_sem.append(round(h_sem * 100, 2))  # Em %
            hazard_com.append(round(h_com * 100, 2))  # Em %
            
            # Reduzir participantes (2 por mês)
            n_atual = max(0, n_atual - 2)
        
        # Retornar formato compatível com Chart.js
        return {
            "labels": meses,  # Agora só números
            "datasets": [
                {
                    "label": "Sem Lance Livre",
                    "data": hazard_sem,
                    "borderColor": "rgb(75, 192, 192)",
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "tension": 0.1,
                    "fill": False
                },
                {
                    "label": "Com Lance Livre" if lance_livre_perc > 0 else "Sem Lance Livre (Lance = 0%)",
                    "data": hazard_com,
                    "borderColor": "rgb(255, 99, 132)" if lance_livre_perc > 0 else "rgb(128, 128, 128)",
                    "backgroundColor": "rgba(255, 99, 132, 0.2)" if lance_livre_perc > 0 else "rgba(128, 128, 128, 0.2)",
                    "tension": 0.1,
                    "fill": False
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar dados do gráfico de probabilidade: {e}")
        return None

def gerar_relatorio_pdf(dados_simulacao: Dict, temp_dir: str) -> str:
    """Gera relatório PDF da simulação de consórcio."""
    try:
        # Criar arquivo PDF temporário
        pdf_path = os.path.join(temp_dir, f'relatorio_consorcio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
        
        # Configurar documento
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#26282A')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#26282A')
        )
        
        # Título
        # Horário de Brasília (UTC-3)
        brasilia_tz = timezone(timedelta(hours=-3))
        agora_brasilia = datetime.now(brasilia_tz)
        
        story.append(Paragraph("Relatório de Simulação de Consórcio", title_style))
        story.append(Paragraph(f"Gerado em: {agora_brasilia.strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Parâmetros da Simulação
        story.append(Paragraph("Parâmetros da Simulação", heading_style))
        
        parametros_data = [
            ['Parâmetro', 'Valor'],
            ['Valor da Carta', f"R$ {dados_simulacao['parametros']['valor_carta']:,.2f}"],
            ['Prazo', f"{dados_simulacao['parametros']['prazo_meses']} meses"],
            ['Taxa de Administração', f"{dados_simulacao['parametros']['taxa_admin'] * 100:.1f}%"],
            ['Fundo de Reserva', f"{dados_simulacao['parametros']['fundo_reserva'] * 100:.1f}%"],
            ['Mês de Contemplação', f"{dados_simulacao['parametros']['mes_contemplacao']}º mês"],
            ['Lance Livre', f"{dados_simulacao['parametros']['lance_livre_perc'] * 100:.1f}%"],
            ['Taxa de Reajuste Anual', f"{dados_simulacao['parametros']['taxa_reajuste_anual'] * 100:.1f}%"]
        ]
        
        parametros_table = Table(parametros_data, colWidths=[3*inch, 2*inch])
        parametros_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C1AFA2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(parametros_table)
        story.append(Spacer(1, 20))
        
        # Resultados Principais
        story.append(Paragraph("Resultados Principais", heading_style))
        
        if dados_simulacao['resultados']['convergiu']:
            cet_anual = dados_simulacao['resultados']['cet_anual'] * 100
            cet_mensal = dados_simulacao['resultados']['cet_mensal'] * 100
        else:
            cet_anual = "Erro no cálculo"
            cet_mensal = "Erro no cálculo"
        
        resultados_data = [
            ['Indicador', 'Valor'],
            ['CET Anual', f"{cet_anual:.2f}%" if isinstance(cet_anual, float) else cet_anual],
            ['CET Mensal', f"{cet_mensal:.3f}%" if isinstance(cet_mensal, float) else cet_mensal],
            ['Lance Livre', f"R$ {dados_simulacao['resumo_financeiro']['valor_lance_livre']:,.2f}"],
            ['Base do Contrato', f"R$ {dados_simulacao['resumo_financeiro']['base_contrato']:,.2f}"],
            ['Carta na Contemplação', f"R$ {dados_simulacao['resumo_financeiro']['valor_carta_contemplacao']:,.2f}"],
            ['Fluxo na Contemplação', f"R$ {dados_simulacao['resumo_financeiro']['fluxo_contemplacao']:,.2f}"],
            ['Total em Parcelas', f"R$ {dados_simulacao['resumo_financeiro']['total_parcelas']:,.2f}"]
        ]
        
        resultados_table = Table(resultados_data, colWidths=[3*inch, 2*inch])
        resultados_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#BC8159')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(resultados_table)
        story.append(Spacer(1, 20))
        
        # REMOVIDO: Gráfico de fluxo de caixa conforme solicitado pelo usuário
        
        # Adicionar gráfico de probabilidades - REMOVIDO para usar apenas dados JSON
        # A nova função gerar_dados_grafico_probabilidade retorna dados para o frontend
        # O PDF não incluirá mais gráficos gerados pelo matplotlib
        
        # Tabela de Amortização (primeiros 24 meses + meses anuais)
        story.append(Paragraph("Fluxo de Caixa Detalhado", heading_style))
        story.append(Paragraph("Primeiros 24 meses detalhados, depois apenas meses anuais (36, 48, 60...) para mostrar evolução do saldo devedor e parcelas.", styles['Normal']))
        story.append(Spacer(1, 10))
        
        tabela_data = [['Mês', 'Data', 'Parcela', 'Valor da Carta', 'Fluxo de Caixa', 'Saldo Devedor']]
        
        # Criar lista filtrada: primeiros 24 + anuais
        detalhamento_filtrado = []
        detalhamento_completo = dados_simulacao['detalhamento']
        
        # Primeiros 24 meses
        for i in range(min(24, len(detalhamento_completo))):
            detalhamento_filtrado.append(detalhamento_completo[i])
        
        # Meses anuais (36, 48, 60, 72, etc.)
        if len(detalhamento_completo) > 24:
            for mes in range(36, len(detalhamento_completo) + 1, 12):
                index = mes - 1  # Convert to 0-based index
                if index < len(detalhamento_completo):
                    detalhamento_filtrado.append(detalhamento_completo[index])
        
        for item in detalhamento_filtrado:
            mes = str(item['mes'])
            data = item['data']
            parcela = f"R$ {item['parcela_corrigida']:,.2f}"
            # Valor da carta corrigido (sofre variação anual)
            valor_carta = f"R$ {item['valor_carta_corrigido']:,.2f}"
            fluxo = f"R$ {item['fluxo_liquido']:,.2f}"
            saldo = f"R$ {item['saldo_devedor']:,.2f}"
            
            tabela_data.append([mes, data, parcela, valor_carta, fluxo, saldo])
        
        tabela_amortizacao = Table(tabela_data, colWidths=[0.6*inch, 0.8*inch, 1.0*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        tabela_amortizacao.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8D4C23')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Fluxos negativos em vermelho
            ('TEXTCOLOR', (4, 1), (4, -1), colors.red),
        ]))
        
        # Destacar linha de contemplação com fluxo positivo em verde
        for i, item in enumerate(detalhamento_filtrado):
            if item['eh_contemplacao']:
                tabela_amortizacao.setStyle(TableStyle([
                    ('BACKGROUND', (0, i+1), (-1, i+1), colors.HexColor('#E8F5E8')),
                    ('TEXTCOLOR', (4, i+1), (4, i+1), colors.green)
                ]))
        
        story.append(tabela_amortizacao)
        
        # Rodapé
        story.append(Spacer(1, 30))
        story.append(Paragraph("Relatório gerado pelo Simulador de Consórcio", 
                             ParagraphStyle('Footer', parent=styles['Normal'], 
                                          fontSize=8, alignment=TA_CENTER, 
                                          textColor=colors.grey)))
        
        # Gerar PDF
        doc.build(story)
        return pdf_path
        
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório PDF: {str(e)}")

@api_router.post("/gerar-relatorio-pdf")
async def gerar_relatorio_pdf_endpoint(parametros: ParametrosConsorcio):
    """Gera e retorna relatório PDF da simulação."""
    try:
        # Executar simulação
        simulador = SimuladorConsorcio(parametros)
        resultado = simulador.simular_cenario_completo()
        
        if resultado['erro']:
            raise HTTPException(status_code=400, detail=resultado.get('mensagem', 'Erro na simulação'))
        
        # Criar diretório temporário
        temp_dir = tempfile.mkdtemp()
        
        # Gerar PDF
        pdf_path = gerar_relatorio_pdf(resultado, temp_dir)
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="Erro ao gerar arquivo PDF")
        
        # Retornar arquivo
        filename = f"relatorio_consorcio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint de PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração do Notion
notion_api_key = os.environ.get("NOTION_API_KEY")
notion_database_id = os.environ.get("NOTION_DATABASE_ID")

# Configuração do Claude (Anthropic)
claude_api_key = os.environ.get("CLAUDE_API_KEY")

# Inicializar cliente do Notion
notion_client = None
if notion_api_key and notion_database_id:
    try:
        notion_client = Client(auth=notion_api_key)
        logger.info("✅ Cliente Notion inicializado com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar cliente Notion: {e}")
else:
    logger.warning("⚠️ Credenciais do Notion não encontradas")

# Inicializar cliente do Claude
claude_client = None
if claude_api_key:
    try:
        # Remover aspas se existirem
        cleaned_key = claude_api_key.strip('"').strip("'")
        claude_client = anthropic.Anthropic(api_key=cleaned_key)
        logger.info("✅ Cliente Claude inicializado com sucesso")
        logger.info(f"🔑 Chave API Claude (primeiros 20 chars): {cleaned_key[:20]}...")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar cliente Claude: {e}")
else:
    logger.warning("⚠️ Chave API do Claude não encontrada")

# ----------------------------
# SERVIÇO DE ANÁLISE DE CONTRATOS COM CLAUDE
# ----------------------------

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extrair texto de um arquivo PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
        text = ""
        
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Página {page_num + 1} ---\n"
                    text += page_text
            except Exception as e:
                logger.warning(f"Erro ao extrair texto da página {page_num + 1}: {e}")
                continue
        
        # Limpar texto
        text = text.strip()
        if not text:
            raise Exception("Nenhum texto encontrado no PDF")
        
        logger.info(f"✅ Texto extraído com sucesso: {len(text)} caracteres")
        return text
        
    except Exception as e:
        logger.error(f"❌ Erro ao extrair texto do PDF: {e}")
        raise Exception(f"Erro ao processar PDF: {str(e)}")

class ContractAnalysisService:
    """Serviço para análise de contratos de consórcio usando Claude AI"""
    
    def __init__(self):
        self.client = claude_client
    
    async def analyze_contract_text(self, contract_text: str) -> dict:
        """Analisar texto de contrato de consórcio usando prompt especializado"""
        if not self.client:
            return {"success": False, "error": "Claude AI não configurado"}
        
        try:
            # Usar o prompt especializado e estruturado para análise de consórcios
            full_prompt = f"""
{prompt_consorcio}

---

AGORA ANALISE O SEGUINTE CONTRATO DE CONSÓRCIO:

```
{contract_text}
```

IMPORTANTE: Use EXATAMENTE o formato de resposta especificado nas instruções acima. Seja detalhista, cite legislação específica e use o sistema de pontuação para classificar o risco de cada cláusula encontrada.
            """

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,  # Aumentado para acomodar análise mais detalhada
                temperature=0.1,  # Reduzido para análise mais consistente
                messages=[
                    {"role": "user", "content": full_prompt}
                ]
            )

            analysis_text = message.content[0].text

            logger.info("✅ Análise de contrato realizada com sucesso")
            return {
                "success": True,
                "analysis": analysis_text,
                "model_used": "claude-3-5-sonnet-20241022",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Erro na análise do contrato: {e}")
            return {"success": False, "error": str(e)}

@api_router.post("/analisar-contrato")
async def analisar_contrato(pdf_file: UploadFile = File(...)):
    """Endpoint para análise de contratos de consórcio via upload de PDF"""
    try:
        # Verificar se é um arquivo PDF
        if not pdf_file.content_type == "application/pdf":
            raise HTTPException(
                status_code=400, 
                detail="Apenas arquivos PDF são aceitos"
            )
        
        # Verificar tamanho do arquivo (limite: 10MB)
        if pdf_file.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Arquivo muito grande (limite: 10MB)"
            )
        
        logger.info(f"📄 Processando PDF: {pdf_file.filename} ({pdf_file.size} bytes)")
        
        # Ler conteúdo do arquivo
        pdf_content = await pdf_file.read()
        
        # Extrair texto do PDF
        contract_text = extract_text_from_pdf(pdf_content)
        
        if len(contract_text) < 100:
            raise HTTPException(
                status_code=400, 
                detail="Texto extraído do PDF muito curto (mínimo 100 caracteres)"
            )
        
        logger.info(f"📝 Texto extraído: {len(contract_text)} caracteres")
        
        # Realizar análise com Claude
        result = await contract_analysis_service.analyze_contract_text(contract_text)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500, 
                detail=f"Erro na análise: {result.get('error')}"
            )
        
        return {
            "success": True,
            "filename": pdf_file.filename,
            "file_size": pdf_file.size,
            "text_length": len(contract_text),
            "analysis": result["analysis"],
            "model_used": result["model_used"],
            "timestamp": result["timestamp"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no endpoint de análise de PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# Instanciar serviço de análise
contract_analysis_service = ContractAnalysisService()

class NotionLeadService:
    """Serviço para gerenciar leads no Notion"""
    
    def __init__(self):
        self.client = notion_client
        self.database_id = notion_database_id
    
    async def create_lead_in_notion(self, lead_data: dict) -> dict:
        """Criar lead no Notion database"""
        if not self.client or not self.database_id:
            logger.warning("❌ Cliente Notion não configurado")
            return {"success": False, "error": "Notion não configurado"}
        
        try:
            # Formattar dados para o Notion
            properties = {
                "Nome": {
                    "title": [
                        {
                            "text": {
                                "content": f"{lead_data.get('nome', '')} {lead_data.get('sobrenome', '')}".strip()
                            }
                        }
                    ]
                },
                "email": {
                    "email": lead_data.get("email", "")
                },
                "Telefone": {
                    "phone_number": lead_data.get("telefone", "")
                },
                "Profissão": {
                    "rich_text": [
                        {
                            "text": {
                                "content": lead_data.get("profissao", "")
                            }
                        }
                    ]
                },
                "Como nos conheceu": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "Cadastro Interno"
                            }
                        }
                    ]
                },
                "Simulações": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "Nenhuma simulação ainda"
                            }
                        }
                    ]
                }
            }
            
            # Criar página no Notion
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            logger.info(f"✅ Lead criado no Notion: {response.get('id')}")
            return {
                "success": True, 
                "notion_id": response.get("id"),
                "created_time": response.get("created_time")
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar lead no Notion: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_lead_in_notion(self, notion_id: str, lead_data: dict) -> dict:
        """Atualizar lead no Notion"""
        if not self.client:
            return {"success": False, "error": "Notion não configurado"}
        
        try:
            properties = {
                "Nome Completo": {
                    "title": [
                        {
                            "text": {
                                "content": f"{lead_data.get('nome', '')} {lead_data.get('sobrenome', '')}"
                            }
                        }
                    ]
                },
                "Nome": {
                    "rich_text": [
                        {
                            "text": {
                                "content": lead_data.get("nome", "")
                            }
                        }
                    ]
                },
                "Sobrenome": {
                    "rich_text": [
                        {
                            "text": {
                                "content": lead_data.get("sobrenome", "")
                            }
                        }
                    ]
                },
                "Email": {
                    "email": lead_data.get("email", "")
                },
                "Telefone": {
                    "phone_number": lead_data.get("telefone", "")
                },
                "Profissão": {
                    "rich_text": [
                        {
                            "text": {
                                "content": lead_data.get("profissao", "")
                            }
                        }
                    ]
                }
            }
            
            response = self.client.pages.update(
                page_id=notion_id,
                properties=properties
            )
            
            logger.info(f"✅ Lead atualizado no Notion: {notion_id}")
            return {"success": True, "updated_time": response.get("last_edited_time")}
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar lead no Notion: {e}")
            return {"success": False, "error": str(e)}

# Instanciar serviço Notion
notion_service = NotionLeadService()

# Endpoint para criar lead (usado pelo frontend CadastroForm)
@api_router.post("/criar-lead")
async def criar_lead(lead_data: dict):
    """Criar lead com dados do formulário interno"""
    try:
        # Gerar ID e token únicos
        lead_id = str(uuid.uuid4())
        access_token = str(uuid.uuid4())
        
        # Preparar dados do lead
        lead_completo = {
            "id": lead_id,
            "access_token": access_token,
            "nome": lead_data.get("nome", ""),
            "sobrenome": lead_data.get("sobrenome", ""),
            "email": lead_data.get("email", ""),
            "telefone": lead_data.get("telefone", ""),
            "profissao": lead_data.get("profissao", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "cadastro_interno",
            "has_access": True
        }
        
        # Salvar no MongoDB
        await db.leads.insert_one(lead_completo)
        logger.info(f"✅ Lead salvo no MongoDB: {lead_id}")
        
        # Tentar salvar no Notion (não falha se der erro)
        try:
            notion_result = await notion_service.create_lead_in_notion(lead_completo)
            if notion_result.get("success"):
                logger.info(f"✅ Lead salvo no Notion: {notion_result.get('notion_id')}")
            else:
                logger.warning(f"⚠️  Falha ao salvar no Notion: {notion_result.get('error')}")
        except Exception as e:
            logger.warning(f"⚠️  Erro ao salvar no Notion (não crítico): {e}")
        
        return {
            "success": True,
            "lead_id": lead_id,
            "access_token": access_token,
            "message": "Lead criado com sucesso!"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar lead: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar lead: {str(e)}")

def _as_float_array(x):
    """Converte para array numpy float."""
    a = np.asarray(list(x), dtype=float)
    if a.ndim != 1:
        raise ValueError("Forneça vetores 1D.")
    return a

def _percentile_month(F, p):
    """Primeiro mês (1-index) em que F_t ≥ p. Retorna None se não atingir."""
    idx = np.argmax(F >= p)
    if F[-1] < p:
        return None
    return int(np.where(F >= p)[0][0] + 1)

def hazards_from_counts(participantes_restantes, sorteio, lance=None):
    """Calcula hazards (prob. condicionais) a partir de CONTAGENS mensais."""
    pr = _as_float_array(participantes_restantes)
    s = _as_float_array(sorteio)
    l = _as_float_array(lance) if lance is not None else np.zeros_like(s)
    
    if np.any(pr <= 0):
        raise ValueError("Há 'participantes_restantes' ≤ 0. Use valores estritamente positivos.")

    h_sem = np.divide(s, pr, out=np.zeros_like(s), where=pr>0)
    h_com = np.divide(s + l, pr, out=np.zeros_like(s), where=pr>0)

    h_sem = np.clip(h_sem, 0.0, 1.0)
    h_com = np.clip(h_com, 0.0, 1.0)

    return {"h_sem": h_sem, "h_com": h_com}

def curvas_from_hazard(h):
    """Calcula curvas de probabilidade a partir de hazards."""
    h = _as_float_array(h)
    h = np.clip(h, 0.0, 1.0)

    # Sobrevivência e acumulada
    S = np.cumprod(1.0 - h)
    F = 1.0 - S

    # f_t = h_t * S_{t-1}
    S_prev = np.r_[1.0, S[:-1]]
    f = h * S_prev

    # Métricas de distribuição do mês de contemplação
    meses = np.arange(1, len(h) + 1, dtype=int)
    esperanca = float(np.sum(meses * f))
    p50 = _percentile_month(F, 0.50)
    p10 = _percentile_month(F, 0.10)
    p90 = _percentile_month(F, 0.90)

    return {
        "meses": meses.tolist(),
        "hazard": h.tolist(),
        "probabilidade_acumulada": F.tolist(),
        "probabilidade_mes": f.tolist(),
        "esperanca_meses": esperanca,
        "mediana_mes": p50,
        "p10_mes": p10,
        "p90_mes": p90
    }

def calcular_probabilidades_contemplacao(num_participantes=430, contemplados_por_mes=2, lance_livre_perc=0.10):
    """
    Calcula probabilidades de contemplação baseado na lógica da planilha.
    
    Args:
        num_participantes: Número total de participantes do grupo
        contemplados_por_mes: Número de contemplados por mês (sorteio + lance)
    """
    try:
        # Calcular quantos meses até contemplar todos
        meses_total = int(np.ceil(num_participantes / contemplados_por_mes))
        
        # Listas para armazenar dados
        meses = []
        participantes_restantes = []
        prob_sem_lance = []  # Col5 da planilha
        prob_com_lance = []  # Col6 da planilha
        prob_acumulada_sem = []
        prob_acumulada_com = []
        
        # Inicializar
        participantes_atual = num_participantes
        acum_sem = 0.0
        acum_com = 0.0
        
        for mes in range(1, meses_total + 1):
            meses.append(mes)
            participantes_restantes.append(participantes_atual)
            
            # Lógica da planilha:
            # - 1 contemplado por sorteio (sempre)
            # - 1 contemplado por lance (col4 = 1)
            # - Probabilidade sem lance = 1 / participantes_restantes
            # - Probabilidade com lance = 2 / participantes_restantes
            
            if participantes_atual > 0:
                prob_mes_sem = 1.0 / participantes_atual  # Col5: probabilidade apenas sorteio
                prob_mes_com = 2.0 / participantes_atual  # Col6: probabilidade sorteio + lance
            else:
                prob_mes_sem = 0.0
                prob_mes_com = 0.0
            
            prob_sem_lance.append(prob_mes_sem)
            prob_com_lance.append(prob_mes_com)
            
            # Probabilidades acumuladas (aproximação simples)
            acum_sem += prob_mes_sem
            acum_com += prob_mes_com
            
            # Garantir que não passe de 1.0
            acum_sem = min(acum_sem, 1.0)
            acum_com = min(acum_com, 1.0)
            
            prob_acumulada_sem.append(acum_sem)
            prob_acumulada_com.append(acum_com)
            
            # Reduzir participantes para próximo mês
            participantes_atual = max(0, participantes_atual - contemplados_por_mes)
        
        # Calcular métricas estatísticas
        def calcular_metricas(probabilidades):
            total_prob = sum(probabilidades)
            if total_prob > 0:
                # Normalizar para que some 1
                probs_norm = [p/total_prob for p in probabilidades]
                esperanca = sum((i+1) * p for i, p in enumerate(probs_norm))
                
                # Mediana e percentis
                acum = 0.0
                p50 = p10 = p90 = None
                for i, p in enumerate(probs_norm):
                    acum += p
                    if p10 is None and acum >= 0.10:
                        p10 = i + 1
                    if p50 is None and acum >= 0.50:
                        p50 = i + 1
                    if p90 is None and acum >= 0.90:
                        p90 = i + 1
                        break
                
                return esperanca, p50, p10, p90
            else:
                return 0, None, None, None
        
        esp_sem, med_sem, p10_sem, p90_sem = calcular_metricas(prob_sem_lance)
        esp_com, med_com, p10_com, p90_com = calcular_metricas(prob_com_lance)
        
        return {
            "sem_lance": {
                "meses": meses,
                "hazard": prob_sem_lance,
                "probabilidade_acumulada": prob_acumulada_sem,
                "probabilidade_mes": prob_sem_lance,  # Mesmo que hazard para este caso
                "esperanca_meses": esp_sem,
                "mediana_mes": med_sem,
                "p10_mes": p10_sem,
                "p90_mes": p90_sem
            },
            "com_lance": {
                "meses": meses,
                "hazard": prob_com_lance,
                "probabilidade_acumulada": prob_acumulada_com,
                "probabilidade_mes": prob_com_lance,  # Mesmo que hazard para este caso
                "esperanca_meses": esp_com,
                "mediana_mes": med_com,
                "p10_mes": p10_com,
                "p90_mes": p90_com
            },
            "parametros": {
                "num_participantes": num_participantes,
                "lance_livre_perc": lance_livre_perc,
                "contemplados_por_mes": contemplados_por_mes,
                "meses_total": meses_total
            }
        }
        
    except Exception as e:
        logger.error(f"Erro no cálculo de probabilidades: {e}")
        return None

def calcular_probabilidades_contemplacao_corrigido(num_participantes=430, lance_livre_perc=0.10):
    """
    Versão corrigida do cálculo de probabilidades de contemplação.
    
    LÓGICA CORRIGIDA BASEADA NA PLANILHA DO USUÁRIO:
    - SEM LANCE: 1/(N-1) - você só compete no sorteio (não participa do lance)
    - COM LANCE: 2/N - você pode ganhar tanto no sorteio quanto no lance
    - REDUÇÃO DE PARTICIPANTES: Sempre 2 por mês (1 sorteio + 1 lance) em ambos os cenários
    
    Args:
        num_participantes: Número total de participantes do grupo
        lance_livre_perc: Percentual do lance livre (mantido para compatibilidade)
    """
    try:
        # Calcular quantos meses até contemplar todos (sempre assumindo 2 contemplados por mês)
        meses_total = int(np.ceil(num_participantes / 2))
        
        # Listas para armazenar dados
        meses = []
        
        # Ambas as curvas usam a mesma redução de participantes (2 por mês)
        # A diferença está na fórmula de probabilidade individual
        prob_sem_lance = []
        prob_acumulada_sem = []
        prob_com_lance = []
        prob_acumulada_com = []
        
        # Inicializar
        participantes_atual = num_participantes
        prob_nao_contemplado_sem = 1.0
        prob_nao_contemplado_com = 1.0
        
        for mes in range(1, meses_total + 1):
            meses.append(mes)
            
            if participantes_atual > 0:
                # SEM LANCE: 1/(N-1) - só compete no sorteio
                # Subtrai 1 porque o lance "tira" uma oportunidade de você ganhar no sorteio
                prob_mes_sem = 1.0 / max(1, participantes_atual - 1)
                
                # COM LANCE: 2/N - pode ganhar no sorteio OU no lance
                prob_mes_com = min(2.0 / participantes_atual, 1.0)
            else:
                prob_mes_sem = 0.0
                prob_mes_com = 0.0
            
            prob_sem_lance.append(prob_mes_sem)
            prob_com_lance.append(prob_mes_com)
            
            # Cálculo das probabilidades acumuladas usando a fórmula de sobrevivência
            prob_nao_contemplado_sem *= (1.0 - prob_mes_sem)
            prob_nao_contemplado_com *= (1.0 - prob_mes_com)
            
            prob_acumulada_sem.append(1.0 - prob_nao_contemplado_sem)
            prob_acumulada_com.append(1.0 - prob_nao_contemplado_com)
            
            # Reduzir 2 participantes para próximo mês (sempre: 1 sorteio + 1 lance)
            participantes_atual = max(0, participantes_atual - 2)
        
        # Calcular métricas estatísticas corrigidas
        def calcular_metricas_corrigidas(probabilidades_mensais, probabilidades_acumuladas):
            # Usar as probabilidades mensais para calcular a esperança
            total_prob = sum(probabilidades_mensais)
            if total_prob > 0:
                # Normalizar para que some 1
                probs_norm = [p/total_prob for p in probabilidades_mensais]
                esperanca = sum((i+1) * p for i, p in enumerate(probs_norm))
                
                # Usar probabilidades acumuladas para percentis
                p50 = p10 = p90 = None
                for i, prob_acum in enumerate(probabilidades_acumuladas):
                    if p10 is None and prob_acum >= 0.10:
                        p10 = i + 1
                    if p50 is None and prob_acum >= 0.50:
                        p50 = i + 1
                    if p90 is None and prob_acum >= 0.90:
                        p90 = i + 1
                    if p90 is not None:
                        break
                
                return esperanca, p50, p10, p90
            else:
                return 0, None, None, None
        
        esp_sem, med_sem, p10_sem, p90_sem = calcular_metricas_corrigidas(prob_sem_lance, prob_acumulada_sem)
        esp_com, med_com, p10_com, p90_com = calcular_metricas_corrigidas(prob_com_lance, prob_acumulada_com)
        
        return {
            "sem_lance": {
                "meses": meses,
                "hazard": prob_sem_lance,
                "probabilidade_acumulada": prob_acumulada_sem,
                "probabilidade_mes": prob_sem_lance,  # Mesmo que hazard para este caso
                "esperanca_meses": esp_sem,
                "mediana_mes": med_sem,
                "p10_mes": p10_sem,
                "p90_mes": p90_sem
            },
            "com_lance": {
                "meses": meses,
                "hazard": prob_com_lance,
                "probabilidade_acumulada": prob_acumulada_com,
                "probabilidade_mes": prob_com_lance,  # Mesmo que hazard para este caso
                "esperanca_meses": esp_com,
                "mediana_mes": med_com,
                "p10_mes": p10_com,
                "p90_mes": p90_com
            },
            "parametros": {
                "num_participantes": num_participantes,
                "lance_livre_perc": lance_livre_perc,
                "contemplados_por_mes": 2,  # Sempre 2 na nova lógica
                "meses_total": meses_total
            }
        }
        
    except Exception as e:
        logger.error(f"Erro no cálculo de probabilidades corrigido: {e}")
        return None

def calcular_probabilidade_mes_especifico(mes_contemplacao: int, lance_livre_perc: float, num_participantes: int, contemplados_por_mes: int = 2):
    """
    Calcula as probabilidades específicas para um mês de contemplação escolhido.
    
    NOVA LÓGICA SIMPLIFICADA:
    - Sempre usa contemplados_por_mes passado como parâmetro (padrão: 2)
    - num_participantes é calculado como 2 × prazo_meses automaticamente
    - lance_livre_perc mantido para compatibilidade, mas probabilidades sempre usam contemplados_por_mes
    
    Args:
        mes_contemplacao: Mês escolhido para contemplação
        lance_livre_perc: Percentual do lance livre (mantido para compatibilidade)
        num_participantes: Número total de participantes do grupo
        contemplados_por_mes: Número de contemplados por mês (padrão: 2)
    
    Returns:
        dict com:
        - prob_no_mes: probabilidade de ser contemplado NAQUELE mês
        - prob_ate_mes: probabilidade de ter sido contemplado ATÉ aquele mês
        - participantes_restantes: quantos participantes restam no início daquele mês
    """
    try:
        if mes_contemplacao < 1:
            return {
                "prob_no_mes": 0.0,
                "prob_ate_mes": 0.0,
                "participantes_restantes": 0
            }
            
        # Calcular participantes restantes no início do mês
        participantes_restantes = max(0, num_participantes - (mes_contemplacao - 1) * contemplados_por_mes)
        
        if participantes_restantes <= 0:
            return {
                "prob_no_mes": 0.0,
                "prob_ate_mes": 1.0,
                "participantes_restantes": 0
            }
        
        # NOVA LÓGICA: sempre usa contemplados_por_mes (normalmente 2)
        prob_no_mes = min(contemplados_por_mes / participantes_restantes, 1.0)
        
        # Probabilidade acumulada até o mês (F_t)
        total_contemplados_ate_mes = min(mes_contemplacao * contemplados_por_mes, num_participantes)
        prob_ate_mes = min(total_contemplados_ate_mes / num_participantes, 1.0)
        
        return {
            "prob_no_mes": float(prob_no_mes),
            "prob_ate_mes": float(prob_ate_mes),
            "participantes_restantes": int(participantes_restantes)
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular probabilidade do mês específico: {e}")
        return {
            "prob_no_mes": 0.0,
            "prob_ate_mes": 0.0,
            "participantes_restantes": 0
        }

# Include the router in the main app
app.include_router(api_router)